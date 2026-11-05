# LangGraph로 적으면 이렇게 됩니다.
from langgraph.graph import StateGraph, START, END

# 앞 절의 route 함수가 하던 일을 셋으로 나눕니다.
#   answer     : 문서를 찾았을 때 답하는 함수
#   no_answer  : 못 찾았을 때 답하는 함수
#   has_docs   : 둘 중 어디로 갈지 정해 주는 함수 (일은 하지 않고 길만 안내합니다)

builder = StateGraph(State)                  # 1) 빈 설계도를 하나 만듭니다.

builder.add_node("retrieve", retrieve)       # 2) 할 일을 노드로 등록합니다.
builder.add_node("answer", answer)           #    여기 적은 이름으로 아래에서 화살표를 겁니다.
builder.add_node("no_answer", no_answer)

builder.add_edge(START, "retrieve")          # 3) 시작해서 retrieve로 갑니다. 직진 화살표입니다.

builder.add_conditional_edges(               # 4) 갈림길입니다.
    "retrieve",                              #    retrieve가 끝나면
    has_docs,                                #    has_docs에게 어디로 갈지 물어보고
    {True: "answer", False: "no_answer"},    #    그 대답에 따라 둘 중 하나로 보냅니다.
)

builder.add_edge("answer", END)              # 5) 두 갈래를 모두 끝으로 모읍니다.
builder.add_edge("no_answer", END)

graph = builder.compile()                    # 6) 설계도를 실행 가능한 물건으로 바꿉니다.
result = graph.invoke({"question": "집에서 일해도 되나요?"})