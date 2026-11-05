# mcp_test.py - 공공데이터포털 아파트 매매 실거래가(상세) MCP 서버 (fastmcp)
"""노출하는 도구 2개:
  - search_apt_trade(apt_name, region, deal_ym)   아파트 이름으로 실거래가 조회
  - list_regions()                                 지원하는 지역(시군구) 이름 목록

API: 국토교통부 아파트 매매 실거래가 상세 자료 /getRTMSDataSvcAptTradeDev
인증키: 프로젝트 루트 .env 의 DATA_GO_KR_API_KEY

실행: python mcp_test.py
(stdio 모드로 대기합니다.)
"""
import os
import xml.etree.ElementTree as ET
from datetime import date
from urllib.parse import unquote

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("apt-trade")

API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
# 포털에서 받은 키는 URL 인코딩(%2F, %3D)된 값이라 한 번 디코딩합니다.
# requests가 전송할 때 다시 인코딩하므로, 그대로 넘기면 이중 인코딩되어 인증 실패합니다.
API_KEY = unquote(os.getenv("DATA_GO_KR_API_KEY", ""))

# API는 아파트 이름이 아니라 시군구 코드(LAWD_CD, 법정동 코드 앞 5자리)로 조회합니다.
# 이름으로 쓸 수 있게 서울 25개 구와 일부 경기 지역만 등록하고, 그 외 지역은 5자리 코드를 직접 넣습니다.
REGION_CODES = {
    "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200",
    "광진구": "11215", "동대문구": "11230", "중랑구": "11260", "성북구": "11290",
    "강북구": "11305", "도봉구": "11320", "노원구": "11350", "은평구": "11380",
    "서대문구": "11410", "마포구": "11440", "양천구": "11470", "강서구": "11500",
    "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
    "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710",
    "강동구": "11740",
    # 경기도
    "과천시": "41290",
}

MAX_RESULTS = 20


def format_amount(amount: int) -> str:
    """만원 단위 금액을 읽기 쉽게 바꾼다. 485000 -> '48억 5,000만 원'"""
    eok, man = divmod(amount, 10000)
    if eok and man:
        return f"{eok}억 {man:,}만 원"
    if eok:
        return f"{eok}억 원"
    return f"{man:,}만 원"


def recent_months(n: int) -> list[str]:
    """이번 달부터 거슬러 올라가며 n개월의 'YYYYMM' 목록을 만든다."""
    today = date.today()
    y, m = today.year, today.month
    months = []
    for _ in range(n):
        months.append(f"{y}{m:02d}")
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return months


def fetch_trades(lawd_cd: str, deal_ym: str) -> list[dict]:
    """한 지역, 한 달치 거래 전체를 가져온다. 에러면 RuntimeError."""
    items, page = [], 1
    while True:
        resp = requests.get(API_URL, params={
            "serviceKey": API_KEY,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": deal_ym,
            "pageNo": page,
            "numOfRows": 1000,
        }, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        # 정상: resultCode 000 / 인증키 오류 등은 returnAuthMsg 형태로 옵니다
        code = root.findtext(".//resultCode") or root.findtext(".//returnReasonCode")
        if code not in ("000", "00"):
            msg = root.findtext(".//resultMsg") or root.findtext(".//returnAuthMsg")
            raise RuntimeError(f"API 에러 {code}: {msg}")

        for it in root.iter("item"):
            items.append({child.tag: (child.text or "").strip() for child in it})

        total = int(root.findtext(".//totalCount") or 0)
        if page * 1000 >= total:
            return items
        page += 1


@mcp.tool()
def search_apt_trade(apt_name: str, region: str, deal_ym: str = "") -> str:
    """아파트 이름으로 매매 실거래가를 조회한다 (국토교통부 공공데이터).

    거래금액, 전용면적, 층, 계약일, 법정동을 최신 계약일 순으로 돌려준다.
    API가 지역 단위로만 조회되므로 아파트가 있는 시군구를 반드시 함께 넣는다.

    Args:
        apt_name: 아파트 이름 일부 (예: '래미안', '헬리오시티'). 띄어쓰기 무시
        region: 시군구 이름 (예: '강남구', '과천시'. 서울 25개 구와 과천시 지원) 또는 법정동 코드 앞 5자리 (예: '41135')
        deal_ym: 계약년월 'YYYYMM' (예: '202510'). 빈 문자열이면 최근 3개월 조회
    """
    if not API_KEY:
        return "에러: .env 에 DATA_GO_KR_API_KEY 가 없습니다."

    lawd_cd = region if region.isdigit() and len(region) == 5 else REGION_CODES.get(region)
    if not lawd_cd:
        return f"'{region}' 지역을 찾을 수 없습니다. 등록된 시군구 이름이나 5자리 시군구 코드를 넣으세요. list_regions로 목록 확인 가능."

    months = [deal_ym] if deal_ym else recent_months(3)
    keyword = apt_name.replace(" ", "")
    rows = []
    try:
        for ym in months:
            rows += [t for t in fetch_trades(lawd_cd, ym)
                     if keyword in t.get("aptNm", "").replace(" ", "")]
    except (requests.RequestException, ET.ParseError, RuntimeError) as e:
        return f"에러: 실거래가 조회에 실패했습니다 ({e})"

    if not rows:
        return f"{region} {', '.join(months)} 기간에 '{apt_name}' 거래가 없습니다. 이름이나 기간을 바꿔 다시 시도하세요."

    rows.sort(key=lambda t: (int(t["dealYear"]), int(t["dealMonth"]), int(t["dealDay"])), reverse=True)

    lines = [f"'{apt_name}' 거래 {len(rows)}건 (최신순 최대 {MAX_RESULTS}건 표시)"]
    for i, t in enumerate(rows[:MAX_RESULTS], 1):
        amount = int(t["dealAmount"].replace(",", ""))
        lines.append(
            f"\n[{i}]\n"
            f"aptNm: {t['aptNm']}\n"
            f"dealAmount: {t['dealAmount']}만원 ({format_amount(amount)})\n"
            f"excluUseAr: {t['excluUseAr']}㎡\n"
            f"floor: {t['floor']}층\n"
            f"계약일: {t['dealYear']}-{int(t['dealMonth']):02d}-{int(t['dealDay']):02d}\n"
            f"umdNm: {t['umdNm']}"
        )
    return "\n".join(lines)


@mcp.tool()
def list_regions() -> str:
    """search_apt_trade의 region에 이름으로 넣을 수 있는 시군구 목록을 돌려준다."""
    return ", ".join(f"{name}({code})" for name, code in REGION_CODES.items())


if __name__ == "__main__":
    mcp.run()   # stdio 모드로 실행
