"""Phase 2: 웹서핑 - 네이버에서 랜덤 키워드 검색 → 결과 스크롤 → (확률적으로) 결과 링크 클릭.

지정 시간(기본 60s)이 끝날 때까지 키워드를 바꿔가며 반복한다.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from urllib.parse import quote_plus

from playwright.sync_api import BrowserContext, Page
from playwright.sync_api import TimeoutError as PWTimeout

log = logging.getLogger("scenario.web")

NAVER_HOME = "https://www.naver.com"
NAVER_SEARCH = "https://search.naver.com/search.naver?query={q}"

# 검색 결과 중 클릭 후보 (네이버 마크업 변경에 대비해 여러 셀렉터 사용)
RESULT_LINK_SELECTORS = [
    "a.news_tit",
    "a.title_link",
    "a.api_txt_lines.total_tit",
    "a.link_tit",
    "#main_pack a[href^='http']:not([href*='search.naver.com']):not([href*='help.naver'])",
]


class NaverSurfingPhase:
    def __init__(self, context: BrowserContext, seconds: float, keywords: list[str],
                 dwell_range: tuple[float, float] = (8.0, 15.0),
                 click_prob: float = 0.5, rng: random.Random | None = None,
                 stop_event: threading.Event | None = None) -> None:
        self.context = context
        self.seconds = seconds
        self.keywords = keywords
        self.dwell_range = dwell_range
        self.click_prob = click_prob
        self.rng = rng or random.Random()
        self.stop = stop_event or threading.Event()
        self.searched: list[str] = []

    # ------------------------------------------------------------------ public
    def run(self) -> None:
        page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.deadline = time.monotonic() + self.seconds
        pool: list[str] = []

        while self._remaining() > 1.0:
            if not pool:  # 키워드를 소진할 때까지 중복 없이 섞어서 사용
                pool = self.keywords[:]
                self.rng.shuffle(pool)
            keyword = pool.pop()
            try:
                self._search(page, keyword)
                self.searched.append(keyword)
                self._browse_results(page)
            except PWTimeout as e:
                log.warning("Timeout (%s): %s", keyword, e.message.splitlines()[0])
                self._sleep(3.0)
            except Exception as e:  # 시나리오 중단 방지
                log.warning("웹서핑 중 예외 (%s): %s", keyword, str(e).splitlines()[0])
                page = self._recover_page(page)
                self._sleep(3.0)  # 네트워크 장애 시 tight retry loop 방지

        self._sleep(self._remaining())  # 페이즈 길이를 설정값에 맞춤 (외부 측정 로그 정렬용)
        log.info("웹서핑 완료 - 검색 %d회: %s", len(self.searched), self.searched)

    # ----------------------------------------------------------------- helpers
    def _remaining(self) -> float:
        # 중단 요청 시 0 을 반환해 모든 루프가 자연스럽게 빠져나오도록 함
        return 0.0 if self.stop.is_set() else self.deadline - time.monotonic()

    def _sleep(self, sec: float) -> None:
        self.stop.wait(max(0.0, min(sec, self._remaining())))

    def _search(self, page: Page, keyword: str) -> None:
        log.info("네이버 검색: '%s'", keyword)
        try:
            # 실제 사용자처럼 메인 페이지 검색창에 타이핑
            if "naver.com" not in page.url:
                page.goto(NAVER_HOME, wait_until="domcontentloaded", timeout=15_000)
            box = page.locator("#query, input[name='query']").first
            box.click(timeout=5_000)
            box.fill("")
            box.press_sequentially(keyword, delay=self.rng.uniform(80, 160))
            self._sleep(self.rng.uniform(0.3, 0.8))
            with page.expect_navigation(wait_until="domcontentloaded", timeout=15_000):
                box.press("Enter")
        except PWTimeout:
            # 검색창을 못 찾는 경우(마크업 변경/팝업 등) URL 직접 호출로 대체
            log.info("검색창 입력 실패 → URL 직접 검색으로 대체")
            page.goto(NAVER_SEARCH.format(q=quote_plus(keyword)),
                      wait_until="domcontentloaded", timeout=15_000)

    def _browse_results(self, page: Page) -> None:
        dwell = self.rng.uniform(*self.dwell_range)
        self._scroll_for(page, dwell * 0.6)

        if self._remaining() > 5.0 and self.rng.random() < self.click_prob:
            self._open_random_result(page, dwell * 0.4)
        else:
            self._scroll_for(page, dwell * 0.4, direction=-1)

    def _scroll_for(self, page: Page, seconds: float, direction: int = 1) -> None:
        """휠 스크롤을 일정 간격으로 발생시켜 사람의 읽기 패턴을 흉내낸다."""
        end = time.monotonic() + min(seconds, self._remaining())
        while time.monotonic() < end and not self.stop.is_set():
            page.mouse.wheel(0, direction * self.rng.randint(200, 600))
            self._sleep(self.rng.uniform(0.6, 1.5))

    def _open_random_result(self, page: Page, seconds: float) -> None:
        links = []
        for sel in RESULT_LINK_SELECTORS:
            links = [l for l in page.locator(sel).all()[:10] if l.is_visible()]
            if links:
                break
        if not links:
            log.info("클릭 가능한 검색 결과 없음")
            return

        link = self.rng.choice(links)
        href = link.get_attribute("href") or ""
        log.info("검색 결과 클릭: %s", href[:100])

        # 네이버 결과는 대부분 target=_blank → 새 탭 여부에 따라 분기
        n_pages = len(self.context.pages)
        link.click(timeout=5_000)
        self._sleep(1.0)
        if len(self.context.pages) > n_pages:
            new_page = self.context.pages[-1]
            try:
                new_page.wait_for_load_state("domcontentloaded", timeout=10_000)
                self._scroll_for(new_page, seconds)
            finally:
                new_page.close()
            page.bring_to_front()
        else:
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10_000)
                self._scroll_for(page, seconds)
            finally:
                page.go_back(wait_until="domcontentloaded", timeout=10_000)

    def _recover_page(self, page: Page) -> Page:
        # 남은 팝업 탭 정리 후 첫 탭 재사용
        for p in self.context.pages[1:]:
            p.close()
        return page if not page.is_closed() else self.context.new_page()
