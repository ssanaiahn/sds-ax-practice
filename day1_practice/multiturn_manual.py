# multiturn_manual.py - chat_history 리스트 직접 관리로 원리 확인
from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage

load_dotenv()
llm = ChatBedrockConverse(
    model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name="us-east-1",
)

chat_history = []  # 대화 기록을 우리가 직접 들고 있습니다

for user_input in ["안녕, 내 이름은 김하늘이야.", "내 이름이 뭐였지?"]:
    chat_history.append(HumanMessage(content=user_input))
    response = llm.invoke(chat_history)   # 기록 전체를 매번 보냅니다
    chat_history.append(response)         # AI 응답도 기록에 추가합니다
    print(f"사용자: {user_input}")
    print(f"AI: {response.content}")
    print(f"(현재 기록 {len(chat_history)}개, 입력 토큰 {response.usage_metadata['input_tokens']})\n")
    print("--------------")
    print(chat_history)