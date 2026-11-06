# memory_graph.py - (완성형 예제) 쌓인 기억을 관계 그래프 그림으로 보기
import sqlite3
import webbrowser
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_aws import ChatBedrockConverse

load_dotenv()

llm = ChatBedrockConverse(
    model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    region_name="us-east-1",
    temperature=0,
)

class Edge(BaseModel):
    source: str = Field(description="주체. 예: 김하늘")
    relation: str = Field(description="관계를 짧은 말로. 예: 소속, 담당, 좋아함")
    target: str = Field(description="대상. 예: 클라우드운영팀")

class MemoryGraph(BaseModel):
    edges: list[Edge]

# 1) SQLite에서 기억 꺼내기
user_name = input("그래프로 만들 이름을 입력하세요: ").strip()
with sqlite3.connect("memory.sqlite") as db:
    memories = [row[0] for row in db.execute("SELECT memory FROM memories WHERE user = ?", (user_name,))]
if not memories:
    raise SystemExit("저장된 기억이 없습니다. auto_memory.py로 먼저 대화해 주세요.")

# 2) 기억 문장을 (주체, 관계, 대상)으로 나누기
graph = llm.with_structured_output(MemoryGraph).invoke(
    f"다음 기억을 (주체, 관계, 대상)으로 나눠 주세요. 주체는 '{user_name}'으로 통일하고 "
    "기억에 없는 내용은 만들지 않습니다.\n" + "\n".join(memories)
)

# 3) Mermaid 문법으로 바꾸기 (글자로 그림을 그리는 문법)
ids = {}
def node(name):
    ids.setdefault(name, f"n{len(ids)}")
    return f'{ids[name]}["{name}"]'

lines = ["graph LR"] + [f"    {node(e.source)} -->|{e.relation}| {node(e.target)}" for e in graph.edges]
mermaid = "\n".join(lines)
print(f"기억 {len(memories)}건 -> 관계 {len(graph.edges)}건\n{mermaid}")

# 4) HTML로 저장하고 브라우저로 열기
html = f"""<!doctype html><meta charset="utf-8"><title>{user_name}님의 기억</title>
<h2>{user_name}님의 기억 그래프</h2>
<pre class="mermaid">
{mermaid}
</pre>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs";
  mermaid.initialize({{ startOnLoad: true }});
</script>"""
path = Path("memory_graph.html").resolve()
path.write_text(html, encoding="utf-8")
webbrowser.open(path.as_uri())