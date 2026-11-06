# auto_memory.py - 말하지 않아도 Agent가 스스로 기억을 만드는 미들웨어
import datetime
import sqlite3
import uuid
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

load_dotenv()

DB = "memory.sqlite"

llm = ChatBedrockConverse(
    model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    region_name="us-east-1",
)

def get_text(message):
    """ChatBedrockConverse는 content를 블록 리스트로 주기도 하므로 텍스트만 모아 반환합니다."""
    content = message.content
    if isinstance(content, list):
        return "".join(block.get("text", "") for block in content if isinstance(block, dict))
    return content

def load_memories(user_name: str) -> list[str]:
    with sqlite3.connect(DB) as db:
        db.execute("CREATE TABLE IF NOT EXISTS memories (user TEXT, memory TEXT, created TEXT)")
        return [r[0] for r in db.execute("SELECT memory FROM memories WHERE user = ? ORDER BY created", (user_name,))]

def save_memory(user_name: str, memory: str) -> None:
    with sqlite3.connect(DB) as db:
        db.execute("INSERT INTO memories VALUES (?, ?, ?)",
                   (user_name, memory, datetime.datetime.now().isoformat(timespec="seconds")))

class MemoryCandidates(BaseModel):
    memories: list[str] = Field(description="오래 기억할 만한 사실을 한 문장씩. 없으면 빈 리스트")

class MemoryMiddleware(AgentMiddleware):
    """사용자가 말할 때마다 기억할 만한 사실을 골라 SQLite에 저장하는 미들웨어"""

    def __init__(self, user_name: str):
        super().__init__()
        self.user_name = user_name

    def before_model(self, state, runtime):
        last = state["messages"][-1]
        if not isinstance(last, HumanMessage):  # 도구 결과를 들고 다시 부를 때는 건너뜁니다
            return None
        checker = llm.with_structured_output(MemoryCandidates)
        found = checker.invoke(
            f"다음 사용자 말에서 앞으로 업무를 도울 때 쓸모 있는 사실만 '{self.user_name}'을 주어로 한 문장씩 뽑으세요. "
            "인사, 질문, 한 번뿐인 요청은 빼고, 사번, 전화번호, 이메일 같은 개인정보는 절대 넣지 마세요.\n\n"
            f"사용자: {get_text(last)}"
        )
        for memory in found.memories:
            save_memory(self.user_name, memory)
            print(f"   🧠 기억함: {memory}")
        return None  # State는 건드리지 않습니다

if __name__ == "__main__":
    user_name = input("이름을 입력하세요: ").strip()
    memories = load_memories(user_name)
    memory_text = "\n".join(f"- {m}" for m in memories) or "- (아직 없음)"

    # 기억이 있으면 Agent가 먼저 말을 겁니다
    if memories:
        hello = llm.invoke(f"다음 기억을 바탕으로 {user_name}님에게 제목 없이 한두 문장으로 반갑게 인사하고 "
                           f"관련된 안부를 하나 물어보세요.\n{memory_text}")
        print("AI:", get_text(hello))

    config = {"configurable": {"thread_id": f"{user_name}_{uuid.uuid4().hex[:8]}"}}  # 실행마다 새 대화방
    with SqliteSaver.from_conn_string("chat_memory.sqlite") as checkpointer:
        agent = create_agent(
            model=llm,
            tools=[],
            middleware=[MemoryMiddleware(user_name)],
            system_prompt=("당신은 삼성SDS 사내 어시스턴트입니다. 짧고 친절하게 답하세요. "
                           "사번, 전화번호, 이메일 같은 개인정보는 기억하지 않으니, 받으면 기억하지 않는다고 짧게 안내하세요.\n"
                           f"[{user_name}님에 대해 기억하고 있는 내용]\n{memory_text}"),
            checkpointer=checkpointer,
        )
        while True:
            question = input("\n나: ").strip()
            if question in ("끝", ""):
                break
            result = agent.invoke({"messages": [HumanMessage(question)]}, config=config)
            print("AI:", get_text(result["messages"][-1]))