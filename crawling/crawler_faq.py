# 운영체제 환경변수 값을 읽기 위해 os 모듈을 가져온다.
import os

# CSV 파일 저장을 위해 csv 모듈을 가져온다.
import csv

# 답변 텍스트 앞의 'A' 표시를 제거하기 위해 re 모듈을 가져온다.
import re

# 프로젝트 루트를 import 경로에 추가하기 위해 sys 모듈을 가져온다.
import sys

# 현재 날짜와 시간을 저장하기 위해 datetime을 가져온다.
from datetime import datetime

# 프로젝트 루트 경로를 계산하기 위해 Path를 가져온다.
from pathlib import Path

# HTML 문서를 분석하기 위해 BeautifulSoup을 가져온다.
from bs4 import BeautifulSoup

# .env 파일에 저장된 환경변수를 읽기 위해 load_dotenv를 가져온다.
from dotenv import load_dotenv

# HTTP 요청을 보내기 위해 requests 모듈을 가져온다.
import requests

# Playwright를 동기 방식으로 사용하기 위해 sync_playwright를 가져온다.
# Playwright는 실제 브라우저를 실행해서 동적 웹페이지도 크롤링할 수 있게 해준다.
from playwright.sync_api import sync_playwright

# SQLAlchemy에서 문자열 SQL을 실행 가능한 객체로 변환할 때 사용한다.
from sqlalchemy import text

# 이 파일(crawling/)의 상위 폴더 = 프로젝트 루트 경로이다.
_ROOT = Path(__file__).resolve().parent.parent

# 프로젝트 루트가 import 경로에 없으면 추가한다.
# data.db, crawling.models 를 어디서 실행해도 불러올 수 있게 한다.
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# DB 연결 엔진 생성 함수를 가져온다.
from data.db import get_engine

# models.py에 정의된 FaqItem 데이터 클래스를 가져온다.
from crawling.models import FaqItem

# 프로젝트 루트의 .env 파일을 읽어온다.
load_dotenv(_ROOT / ".env")

# EV 무공해차 통합누리집 FAQ 목록 페이지 기본 URL이다.
EV_DEFAULT_URL = "https://ev.or.kr/nportal/partcptn/initFaqAction.do"

# 현대자동차 수소차 구매 안내 FAQ 페이지 기본 URL이다.
HYUNDAI_DEFAULT_URL = (
    "https://www.hyundai.com/kr/ko/e/customer/guide/purchase/estimate-fcev"
)

# 출처 사이트 식별자이다 (FaqItem.source_site 에 저장).
SOURCE_SITE_EV = "ev.or.kr"
SOURCE_SITE_HD = "hyundai.com"

# 브라우저 요청 시 사용할 User-Agent 문자열이다.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
)


# 답변 본문 맨 뒤에 출처 문구를 붙이는 공통 함수이다.
def append_answer_source(answer: str, page_url: str, site_name: str) -> str:
    # 출처 한 줄 형식: "출처: ev.or.kr (https://...)"
    suffix = f"\n\n출처: {site_name} ({page_url})"
    body = answer.strip()
    if not body:
        return suffix.strip()
    return body + suffix


# EV 무공해차 통합누리집(ev.or.kr) FAQ 페이지를 크롤링하는 클래스이다.
class EvFaqCrawler:
    # 객체가 생성될 때 자동으로 실행되는 생성자이다.
    def __init__(self):
        # .env 의 CRAWL_URL 값을 읽고, 없으면 EV_DEFAULT_URL 을 사용한다.
        self.url = os.getenv("CRAWL_URL", EV_DEFAULT_URL)

    # 외부에서 호출하는 대표 크롤링 메서드이다.
    # limit 을 지정하면 그 개수까지만 반환한다 (None 이면 전체).
    def crawl(self, limit: int | None = None) -> list[FaqItem]:
        # Playwright 로 모든 FAQ 페이지 HTML 을 수집한다.
        html_pages = self._fetch_all_pages()

        # 수집한 HTML 에서 질문·답변을 추출한다.
        items = self._parse_pages(html_pages)

        # limit 이 지정된 경우 앞에서부터 잘라낸다.
        if limit is not None:
            items = items[:limit]

        # FaqItem 리스트를 반환한다.
        return items

    # 크롤링 후 DB 에 저장까지 한 번에 수행하는 메서드이다.
    def crawl_and_save(self, limit: int | None = None) -> int:
        # FAQ 데이터를 수집한다.
        items = self.crawl(limit=limit)

        # 수집 결과를 DB 에 저장하고 저장 건수를 반환한다.
        return save_faqs(items)

    # Playwright 로 FAQ 목록의 모든 페이지 HTML 을 가져오는 내부 메서드이다.
    # ev.or.kr 은 pnp4web.js 봇 보안 챌린지가 적용되어 있어 실제 브라우저 실행이 필요하다.
    def _fetch_all_pages(self) -> list[str]:
        # 각 페이지의 HTML 문자열을 담을 리스트이다.
        pages: list[str] = []

        # Playwright 실행 컨텍스트를 연다.
        with sync_playwright() as p:
            # AutomationControlled 감지를 비활성화해 봇 차단을 우회한다.
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )

            # 뷰포트·locale 을 설정한 컨텍스트를 만든다.
            # 뷰포트와 locale 이 없으면 보안 챌린지가 통과되지 않는다.
            ctx = browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="ko-KR",
            )

            # 새 브라우저 페이지를 만든다.
            page = ctx.new_page()

            # FAQ 목록 URL 로 이동한다.
            # domcontentloaded 시점까지 기다려 pnp4web.js 가 즉시 실행되게 한다.
            page.goto(self.url, wait_until="domcontentloaded", timeout=60_000)

            # pnp4web.js 보안 챌린지 흐름:
            #   1) 챌린지 페이지 로드 → networkidle 발화 (여기서 첫 번째 networkidle 소비)
            #   2) 챌린지 JS 실행 후 실제 FAQ 페이지로 리다이렉트
            #   3) FAQ 페이지 로드 → networkidle 재발화
            # 고정 대기(3 s) 로 리다이렉트가 시작될 시간을 확보한 뒤
            # 두 번째 networkidle 로 FAQ 페이지가 완전히 안정될 때까지 기다린다.
            page.wait_for_load_state("networkidle", timeout=30_000)  # 챌린지 완료
            page.wait_for_timeout(3_000)                              # 리다이렉트 대기
            page.wait_for_load_state("networkidle", timeout=30_000)  # FAQ 페이지 안정화

            # ev.or.kr 사이트 개편으로 FAQ URL 이 사라진 경우 에러 페이지가 나타난다.
            # ".error_wrap .error_tit" 또는 "페이지를 표시할 수 없습니다." 텍스트로 감지한다.
            # 감지되면 빈 리스트를 반환하고 호출자에서 hyundai.com 만 처리하도록 한다.
            if page.locator(".error_wrap .error_tit").count() > 0:
                print(
                    f"[WARN] ev.or.kr FAQ 페이지를 찾을 수 없습니다 (사이트 개편). "
                    f"URL: {self.url}"
                )
                browser.close()
                return []

            # 질문 제목(.faq_title > .title)이 나타날 때까지 최대 30초 대기한다.
            # selector 가 끝내 나타나지 않으면 (사이트 구조 변경 등) 경고 후 빈 리스트 반환.
            try:
                page.wait_for_selector(".faq_title > .title", timeout=30_000)
            except Exception as e:
                print(
                    f"[WARN] ev.or.kr FAQ 항목 selector(.faq_title > .title) 를 찾지 못했습니다. "
                    f"({type(e).__name__})"
                )
                browser.close()
                return []

            # 다음 페이지가 없을 때까지 반복한다.
            while True:
                # 현재 페이지의 전체 HTML 을 리스트에 추가한다.
                pages.append(page.content())

                # '다음 페이지' 링크(a.next)를 찾는다.
                next_link = page.locator("a.next")

                # 다음 링크가 없으면 마지막 페이지이므로 반복을 종료한다.
                if next_link.count() == 0:
                    break

                # href 속성에 goPage 함수 호출이 있는지 확인한다.
                href = next_link.get_attribute("href") or ""

                # goPage 가 없으면 더 이상 페이지 이동이 불가하므로 종료한다.
                if "goPage" not in href:
                    break

                # 다음 페이지로 이동한다.
                next_link.click()

                # 새 페이지 렌더링을 위해 1.5초 대기한다.
                page.wait_for_timeout(1500)

                # 다음 페이지에서도 질문 목록이 로드될 때까지 대기한다.
                page.wait_for_selector(".faq_title > .title", timeout=30_000)

            # 브라우저를 닫는다.
            browser.close()

        # 수집한 HTML 페이지 목록을 반환한다.
        return pages

    # HTML 목록에서 FaqItem 을 추출하는 내부 메서드이다.
    def _parse_pages(self, html_pages: list[str]) -> list[FaqItem]:
        # 최종 수집 결과를 저장할 리스트이다.
        result: list[FaqItem] = []

        # 중복 질문을 제거하기 위해 set 자료구조를 사용한다.
        seen: set[str] = set()

        # 이번 크롤링 시각을 한 번만 기록한다.
        now = datetime.now()

        # 페이지별 HTML 을 순회한다.
        for html in html_pages:
            # BeautifulSoup 객체를 생성한다.
            # "lxml" 은 빠른 HTML 파서이다.
            soup = BeautifulSoup(html, "lxml")

            # FAQ 한 건씩을 감싸는 .board_faq 블록을 모두 찾는다.
            for block in soup.select(".board_faq"):
                # 질문 제목 요소: .faq_title 안의 .title
                title_el = block.select_one(".faq_title > .title")

                # 제목 요소가 없으면 건너뛴다.
                if not title_el:
                    continue

                # 질문 텍스트를 가져온다 (앞뒤 공백 제거).
                question = title_el.get_text(strip=True)

                # 질문이 비어 있거나 이미 수집한 질문이면 건너뛴다.
                if not question or question in seen:
                    continue

                # 답변 텍스트 초기값이다.
                answer = ""

                # 답변 영역(.faq_con)을 찾는다.
                answer_el = block.select_one(".faq_con")

                if answer_el:
                    # 답변 본문을 줄바꿈 단위로 추출한다.
                    answer = answer_el.get_text("\n", strip=True)

                    # 화면에 표시되는 'A' 접두 문자를 제거한다.
                    answer = re.sub(r"^A\s*", "", answer)

                # 답변 맨 뒤에 출처(사이트명·URL)를 붙인다.
                answer = append_answer_source(answer, self.url, SOURCE_SITE_EV)

                # 중복 확인용 set 에 질문을 추가한다.
                seen.add(question)

                # FaqItem 객체를 생성하여 결과 리스트에 추가한다.
                result.append(
                    FaqItem(
                        source_site=SOURCE_SITE_EV,
                        category="",
                        question=question,
                        answer=answer,
                    )
                )

        # 최종 수집 결과 리스트를 반환한다.
        return result


# 현대자동차(hyundai.com) 수소차 구매 안내 FAQ 페이지를 크롤링하는 클래스이다.
class HyundaiFaqCrawler:
    # 객체가 생성될 때 자동으로 실행되는 생성자이다.
    def __init__(self):
        # .env 의 HYUNDAI_CRAWL_URL 값을 읽고, 없으면 HYUNDAI_DEFAULT_URL 을 사용한다.
        self.url = os.getenv("HYUNDAI_CRAWL_URL", HYUNDAI_DEFAULT_URL)

    # 외부에서 호출하는 대표 크롤링 메서드이다.
    # limit 을 지정하면 그 개수까지만 반환한다 (None 이면 전체).
    def crawl(self, limit: int | None = None) -> list[FaqItem]:
        # Playwright 로 FAQ 항목을 펼쳐 질문·답변을 수집한다.
        items = self._fetch_items()

        # limit 이 지정된 경우 앞에서부터 잘라낸다.
        if limit is not None:
            items = items[:limit]

        # FaqItem 리스트를 반환한다.
        return items

    # 크롤링 후 DB 에 저장까지 한 번에 수행하는 메서드이다.
    def crawl_and_save(self, limit: int | None = None) -> int:
        # FAQ 데이터를 수집한다.
        items = self.crawl(limit=limit)

        # 수집 결과를 DB 에 저장하고 저장 건수를 반환한다.
        return save_faqs(items)

    # Playwright 로 .list-item FAQ 를 펼쳐 질문·답변을 수집하는 내부 메서드이다.
    def _fetch_items(self) -> list[FaqItem]:
        # 최종 수집 결과를 저장할 리스트이다.
        result: list[FaqItem] = []

        # 중복 질문을 제거하기 위해 set 자료구조를 사용한다.
        seen: set[str] = set()

        # 이번 크롤링 시각을 한 번만 기록한다.
        now = datetime.now()

        # Playwright 실행 컨텍스트를 연다.
        with sync_playwright() as p:
            # Chromium 브라우저를 headless 모드로 실행한다.
            browser = p.chromium.launch(headless=True)

            # 새 브라우저 탭을 연다.
            page = browser.new_page(user_agent=USER_AGENT)

            # 수소차 구매 안내 페이지로 이동한다.
            page.goto(self.url, wait_until="networkidle", timeout=60_000)

            # 동적 콘텐츠 로딩을 위해 2초 대기한다.
            page.wait_for_timeout(2000)

            # FAQ 아코디언이 페이지 하단에 있으므로 맨 아래까지 스크롤한다.
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # 스크롤 후 FAQ 목록이 렌더링될 때까지 1초 대기한다.
            page.wait_for_timeout(1000)

            # 질문 제목(.list-item .title)이 나타날 때까지 최대 30초 대기한다.
            page.wait_for_selector(".list-item .title", timeout=30_000)

            # FAQ 항목(.list-item) 전체를 가리키는 로케이터이다.
            items = page.locator(".list-item")

            # 페이지에 있는 FAQ 항목 개수이다.
            count = items.count()

            # FAQ 항목을 하나씩 순회한다.
            for i in range(count):
                # i 번째 FAQ 항목 로케이터이다.
                item = items.nth(i)

                # .list-item > .title (질문) — DOM 상 button 안에 중첩되어 있어 .title 로 조회한다.
                question = item.locator(".title").inner_text().strip()

                # 질문이 비어 있거나 이미 수집한 질문이면 건너뛴다.
                if not question or question in seen:
                    continue

                # 아코디언을 펼쳐 .conts(답변) 영역을 표시한다.
                item.locator(".title").click()

                # 답변 영역이 펼쳐질 때까지 0.3초 대기한다.
                page.wait_for_timeout(300)

                # 답변 텍스트 초기값이다.
                answer = ""

                # 답변 영역(.list-item > .conts) 로케이터이다.
                conts = item.locator(".conts")

                # 답변 요소가 있으면 텍스트를 추출한다.
                if conts.count():
                    answer = conts.inner_text().strip()

                # 답변 맨 뒤에 출처(사이트명·URL)를 붙인다.
                answer = append_answer_source(answer, self.url, SOURCE_SITE_HD)

                # 중복 확인용 set 에 질문을 추가한다.
                seen.add(question)

                # FaqItem 객체를 생성하여 결과 리스트에 추가한다.
                result.append(
                    FaqItem(
                        source_site=SOURCE_SITE_HD,
                        category="",
                        question=question,
                        answer=answer,
                    )
                )

            # 브라우저를 닫는다.
            browser.close()

        # 최종 수집 결과 리스트를 반환한다.
        return result


# FaqItem 목록을 DB faq 테이블에 저장하는 공통 함수이다.
# EvFaqCrawler, HyundaiFaqCrawler, crawl_all_and_save 에서 공통으로 사용한다.
def save_faqs(items: list[FaqItem]) -> int:
    # MySQL 연결 엔진을 가져온다.
    engine = get_engine()

    # DB 에 기록할 저장 시각이다.
    now = datetime.now()

    # 트랜잭션을 시작한다 (성공 시 commit, 실패 시 rollback).
    with engine.begin() as conn:
        # 기존 FAQ 데이터를 비우고 AUTO_INCREMENT 를 1부터 다시 시작한다.
        conn.execute(text("TRUNCATE TABLE faq"))

        # 수집한 FAQ 항목을 하나씩 INSERT 한다.
        for item in items:
            conn.execute(
                text(
                    "INSERT INTO faq (question, answer) VALUES (:question, :answer)"
                ),
                {"question": item.question, "answer": item.answer or None},
            )

        # crawl_stat 테이블에 FAQ 마지막 수집 시각을 갱신한다.
        conn.execute(
            text(
                "UPDATE crawl_stat SET last_crawled_at = :at "
                "WHERE target_type = 'faq'"
            ),
            {"at": now},
        )

    # 출처별 저장 건수를 집계한다 (로그 출력용).
    ev_count = sum(1 for i in items if i.source_site == SOURCE_SITE_EV)
    hd_count = sum(1 for i in items if i.source_site == SOURCE_SITE_HD)

    # 저장 결과를 콘솔에 출력한다.
    print(
        f"[DB] FAQ {len(items)}건 저장 "
        f"(ev.or.kr: {ev_count}, hyundai.com: {hd_count})"
    )

    # tmp_down 폴더에 CSV 파일로도 저장한다.
    tmp_down = os.path.join(os.path.dirname(__file__), "tmp_down")
    os.makedirs(tmp_down, exist_ok=True)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(tmp_down, f"faq_{timestamp}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["source_site", "category", "question", "answer"])
        writer.writeheader()
        for item in items:
            writer.writerow({
                "source_site": item.source_site,
                "category": item.category,
                "question": item.question,
                "answer": item.answer,
            })
    print(f"[CSV] FAQ 저장 완료: {csv_path}")

    # 저장된 건수를 반환한다.
    return len(items)


# ev.or.kr + hyundai.com FAQ 를 모두 수집한다.
def crawl_all_faqs(limit: int | None = None) -> list[FaqItem]:
    # ev.or.kr 은 사이트 개편/봇 차단 등으로 실패할 가능성이 있으므로
    # 예외를 흡수해서 hyundai.com 수집을 계속하도록 한다.
    ev_items: list[FaqItem] = []
    try:
        ev_items = EvFaqCrawler().crawl()
    except Exception as e:
        print(f"[WARN] EvFaqCrawler 실패: {type(e).__name__}: {e}")

    # hyundai.com 도 동일하게 예외를 흡수한다.
    hd_items: list[FaqItem] = []
    try:
        hd_items = HyundaiFaqCrawler().crawl()
    except Exception as e:
        print(f"[WARN] HyundaiFaqCrawler 실패: {type(e).__name__}: {e}")

    # 두 사이트 결과를 합친다.
    items = ev_items + hd_items

    # limit 이 지정된 경우 앞에서부터 잘라낸다.
    if limit is not None:
        items = items[:limit]

    # 합쳐진 FaqItem 리스트를 반환한다.
    return items


# ev.or.kr + hyundai.com FAQ 를 수집한 뒤 DB 에 저장한다.
def crawl_all_and_save(limit: int | None = None) -> int:
    # 전체 수집 후 save_faqs 로 DB 에 반영한다.
    return save_faqs(crawl_all_faqs(limit=limit))


# Streamlit 등에서 동기적으로 호출할 때 사용하는 래퍼 함수이다.
def run_sync() -> int:
    # ev.or.kr + hyundai.com FAQ 를 수집·저장하고 저장 건수를 반환한다.
    return crawl_all_and_save()


# 이 파일을 직접 실행하면 크롤링 후 DB 저장을 즉시 시작한다.
if __name__ == "__main__":
    # 두 사이트 FAQ 를 수집해 DB 에 저장한다.
    count = crawl_all_and_save()

    # 완료 메시지를 콘솔에 출력한다.
    print(f"[완료] FAQ {count}건 DB 저장 (ev.or.kr + hyundai.com)")
