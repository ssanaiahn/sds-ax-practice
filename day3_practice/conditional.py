# conditional.py - 조건부 엣지로 분기하기
from typing import TypedDict, Literal
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_aws import ChatBedrockConverse

load_dotenv()
llm = ChatBedrockConverse(
    model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name="us-east-1",
)


def get_text(message):
    """ChatBedrockConverse는 content를 블록 리스트로 주기도 하므로 텍스트만 모아 반환합니다."""
    content = message.content
    if isinstance(content, list):
        return "".join(block.get("text", "") for block in content if isinstance(block, dict))
    return content


class ClassifyState(TypedDict):
    user_input: str
    intent: str
    response: str


def classify(state: ClassifyState) -> dict:
    """LLM에게 입력이 질문인지 감탄인지 판단하게 합니다."""
    response = llm.invoke(
        "다음 문장이 무언가를 묻는 질문이면 question, 감탄이나 감정 표현이면 exclaim 이라고 "
        f"단어 하나만 답하세요.\n문장: {state['user_input']}"
    )
    text = get_text(response).strip().lower()
    # LLM이 "question입니다"처럼 덧붙여 답해도 되도록 포함 여부로 봅니다.
    # 둘 다 아니면 질문으로 보고 답하는 쪽으로 보냅니다.
    intent = "exclaim" if "exclaim" in text and "question" not in text else "question"
    return {"intent": intent}


def answer_question(state: ClassifyState) -> dict:
    """질문에 LLM으로 답합니다."""
    response = llm.invoke(f"다음 질문에 한 줄로 답하세요: {state['user_input']}")
    return {"response": get_text(response)}


def react_exclaim(state: ClassifyState) -> dict:
    """감탄에는 LLM 없이 정해진 반응을 합니다."""
    return {"response": f"'{state['user_input']}' 라니 멋진 일이네요."}


def route_by_intent(state: ClassifyState) -> Literal["answer_question", "react_exclaim"]:
    """라우팅 함수: State를 보고 다음 노드의 이름을 반환합니다."""
    if state["intent"] == "question":
        return "answer_question"
    return "react_exclaim"


builder = StateGraph(ClassifyState)
builder.add_node("classify", classify)
builder.add_node("answer_question", answer_question)
builder.add_node("react_exclaim", react_exclaim)

builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", route_by_intent)   # 분기 등록
builder.add_edge("answer_question", END)
builder.add_edge("react_exclaim", END)
graph = builder.compile()

# 네 번째 입력은 물음표가 없는 질문입니다. 예전 규칙('?' 유무)이라면 exclaim으로 잘못 분류됩니다.
for text in ["오늘 사내 식당 메뉴 뭐야?", "와 배포가 한 번에 성공했다", "LangGraph가 뭐야?", "회의실 예약 방법 알려줘", "오늘 날씨는"]:
    result = graph.invoke({"user_input": text, "intent": "", "response": ""})
    print(f"입력: {text}")
    print(f"분류: {result['intent']} / 응답: {result['response']}\n")