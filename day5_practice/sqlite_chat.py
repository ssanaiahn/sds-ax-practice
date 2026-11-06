# sqlite_chat.py - 터미널에서 대화하고, 대화 기록은 SQLite(chat_memory.sqlite)에 쌓기
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

load_dotenv()

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

user_name = input("이름을 입력하세요: ").strip()
config = {"configurable": {"thread_id": f"chat_{user_name}"}}  # 사람마다 대화방을 따로 둡니다

with SqliteSaver.from_conn_string("chat_memory.sqlite") as checkpointer:
    agent = create_agent(
        model=llm,
        tools=[],
        system_prompt="당신은 삼성SDS 사내 어시스턴트입니다. 짧고 친절하게 답하세요.",
        checkpointer=checkpointer,
    )

    while True:
        question = input("\n나: ").strip()
        if question in ("끝", ""):
            break
        result = agent.invoke({"messages": [HumanMessage(question)]}, config=config)
        print("AI:", get_text(result["messages"][-1]))
        print(f"   (이 대화방에 쌓인 메시지 {len(result['messages'])}개)")