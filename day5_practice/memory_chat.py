# memory_chat.py - "기억해줘"라고 한 내용은 SQLite 기억 테이블에 쌓고, 새 대화에서도 꺼내 쓰기
import datetime
import sqlite3
import uuid
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite import SqliteSaver

load_dotenv()

DB = "memory.sqlite"

def load_memories(user_name: str) -> list[str]:
    """이 사용자의 기억을 오래된 순서로 모두 꺼냅니다."""
    with sqlite3.connect(DB) as db:
        db.execute("CREATE TABLE IF NOT EXISTS memories (user TEXT, memory TEXT, created TEXT)")
        rows = db.execute("SELECT memory FROM memories WHERE user = ? ORDER BY created", (user_name,)).fetchall()
    return [r[0] for r in rows]

user_name = input("이름을 입력하세요: ").strip()

@tool
def save_memory(memory: str) -> str:
    """사용자가 '기억해줘', '메모해줘'라고 한 내용을 기억 테이블에 저장한다.
    저장을 요청했을 때만 사용한다. memory는 한 문장으로 정리한 내용이다."""
    with sqlite3.connect(DB) as db:
        db.execute("INSERT INTO memories VALUES (?, ?, ?)",
                   (user_name, memory, datetime.datetime.now().isoformat(timespec="seconds")))
    return f"기억했습니다: {memory}"

def get_text(message):
    """ChatBedrockConverse는 content를 블록 리스트로 주기도 하므로 텍스트만 모아 반환합니다."""
    content = message.content
    if isinstance(content, list):
        return "".join(block.get("text", "") for block in content if isinstance(block, dict))
    return content

# 저장된 기억을 시스템 프롬프트에 넣어 둡니다. 대화방이 바뀌어도 이 기억은 따라옵니다
memories = load_memories(user_name)
print(f"불러온 기억 {len(memories)}건")
memory_text = "\n".join(f"- {m}" for m in memories) or "- (아직 없음)"

llm = ChatBedrockConverse(
    model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    region_name="us-east-1",
)

# 실행할 때마다 새 대화방(thread_id)을 엽니다. 대화 원문은 이어지지 않습니다
config = {"configurable": {"thread_id": f"{user_name}_{uuid.uuid4().hex[:8]}"}}

with SqliteSaver.from_conn_string("chat_memory.sqlite") as checkpointer:
    agent = create_agent(
        model=llm,
        tools=[save_memory],
        system_prompt=(
            "당신은 삼성SDS 사내 어시스턴트입니다. 짧고 친절하게 답하세요. "
            "사용자가 무언가를 기억하거나 메모해 달라고 하면 save_memory 도구로 저장하세요.\n"
            f"[{user_name}님에 대해 기억하고 있는 내용]\n{memory_text}"
        ),
        checkpointer=checkpointer,
    )
    while True:
        question = input("\n나: ").strip()
        if question in ("끝", ""):
            break
        result = agent.invoke({"messages": [HumanMessage(question)]}, config=config)
        print("AI:", get_text(result["messages"][-1]))