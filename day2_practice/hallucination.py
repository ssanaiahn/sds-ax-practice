# hallucination.py - RAG 없이 사내 규정 질문
from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse

load_dotenv()
llm = ChatBedrockConverse(
    model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name="us-east-1",
    temperature=0,
)

def get_text(message):
    """ChatBedrockConverse는 content를 블록 리스트로 주기도 하므로 텍스트만 모아 반환합니다."""
    content = message.content
    if isinstance(content, list):
        return "".join(block.get("text", "") for block in content if isinstance(block, dict))
    return content


print(get_text(llm.invoke("삼성SDS 국내 출장 식비 한도는 하루 얼마인가요? 정확한 금액만 답해주세요.")))
print(get_text(llm.invoke("삼성SDS 재택근무는 주 며칠까지 가능한가요? 규정 조항 번호와 함께 알려주세요.")))