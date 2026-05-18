# 운영체제 환경변수 값을 읽기 위해 os 모듈을 가져온다.
import os

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

# Playwright를 동기 방식으로 사용하기 위해 sync_playwright를 가져온다.
# Playwright는 실제 브라우저를 실행해서 동적 웹페이지도 크롤링할 수 있게 해준다.
from playwright.sync_api import sync_playwright

# SQLAlchemy에서 문자열 SQL을 실행 가능한 객체로 변환할 때 사용한다.
from sqlalchemy import text

# 이 파일(crawling/)의 상위 폴더 = 프로젝트 루트 경로이다.
_ROOT = Path(__file__).resolve().parent.parent

# 프로젝트 루트가 import 경로에 없으면 추가한다.
# crawling.db, crawling.models 를 어디서 실행해도 불러올 수 있게 한다.
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# DB 연결 엔진 생성 함수를 가져온다.
from crawling.db import get_engine

# models.py에 정의된 FaqItem 데이터 클래스를 가져온다.
from crawling.models import FaqItem

# 프로젝트 루트의 .env 파일을 읽어온다.
load_dotenv(_ROOT / ".env")

# FAQ 목록 페이지 기본 URL이다.
DEFAULT_URL = "https://ev.or.kr/nportal/partcptn/initFaqAction.do"

# 출처 사이트 식별자이다 (FaqItem.source_site 에 저장).
SOURCE_SITE = "ev.or.kr"

# 브라우저 요청 시 사용할 User-Agent 문자열이다.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
)


# EV 무공해차 통합누리집(ev.or.kr) FAQ 페이지를 크롤링하는 클래스이다.
class EvFaqCrawler:
    # 객체가 생성될 때 자동으로 실행되는 생성자이다.
    def __init__(self):
        # .env 의 CRAWL_URL 값을 읽고, 없으면 DEFAULT_URL 을 사용한다.
        self.url = os.getenv("CRAWL_URL", DEFAULT_URL)

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
        return self._save(items)

    # Playwright 로 FAQ 목록의 모든 페이지 HTML 을 가져오는 내부 메서드이다.
    def _fetch_all_pages(self) -> list[str]:
        # 각 페이지의 HTML 문자열을 담을 리스트이다.
        pages: list[str] = []

        # Playwright 실행 컨텍스트를 연다.
        # with 구문을 사용하면 작업이 끝난 뒤 자원이 자동 정리된다.
        with sync_playwright() as p:
            # Chromium 브라우저를 실행한다.
            # headless=True 는 브라우저 창을 화면에 보이지 않게 실행한다는 뜻이다.
            browser = p.chromium.launch(headless=True)

            # 새 브라우저 페이지를 만든다.
            page = browser.new_page(user_agent=USER_AGENT)

            # FAQ 목록 URL 로 이동한다.
            # wait_until="networkidle" 은 네트워크 요청이 어느 정도 끝날 때까지 기다린다.
            page.goto(self.url, wait_until="networkidle", timeout=60_000)

            # 질문 제목(.faq_title > .title)이 나타날 때까지 최대 30초 대기한다.
            page.wait_for_selector(".faq_title > .title", timeout=30_000)

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

                # 중복 확인용 set 에 질문을 추가한다.
                seen.add(question)

                # FaqItem 객체를 생성하여 결과 리스트에 추가한다.
                result.append(
                    FaqItem(
                        source_site=SOURCE_SITE,
                        category="",
                        question=question,
                        answer=answer,
                        crawled_at=now,
                    )
                )

        # 최종 수집 결과 리스트를 반환한다.
        return result

    # FaqItem 목록을 DB faq 테이블에 저장하는 내부 메서드이다.
    def _save(self, items: list[FaqItem]) -> int:
        # MySQL 연결 엔진을 가져온다.
        engine = get_engine()

        # DB 에 기록할 저장 시각이다.
        now = datetime.now()

        # 트랜잭션을 시작한다 (성공 시 commit, 실패 시 rollback).
        with engine.begin() as conn:
            # 기존 FAQ 데이터를 모두 삭제한 뒤 새 데이터로 교체한다.
            conn.execute(text("DELETE FROM faq"))

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

        # 저장 결과를 콘솔에 출력한다.
        print(f"[DB] FAQ {len(items)}건 저장 (출처: {SOURCE_SITE})")

        # 저장된 건수를 반환한다.
        return len(items)


# Streamlit 등에서 동기적으로 호출할 때 사용하는 래퍼 함수이다.
def run_sync() -> int:
    return EvFaqCrawler().crawl_and_save()


# 이 파일을 직접 실행하면 크롤링 후 DB 저장을 즉시 시작한다.
if __name__ == "__main__":
    count = EvFaqCrawler().crawl_and_save()
    print(f"[완료] EV FAQ {count}건 DB 저장")
