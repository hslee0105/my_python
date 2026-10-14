"""시나리오 설정 값 (CLI 인자로 덮어쓰기 가능)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# 네이버 검색에 사용할 랜덤 키워드 풀
NAVER_KEYWORDS: list[str] = [
    "오늘 날씨", "노트북 추천", "GPU 벤치마크", "인공지능 뉴스", "맛집 추천",
    "주식 시세", "환율", "프로야구 결과", "영화 순위", "여행지 추천",
    "캠핑 용품", "전기차", "스마트폰 신제품", "반도체 뉴스", "레시피",
    "부동산 뉴스", "축구 하이라이트", "게임 신작", "책 추천", "건강 정보",
]

# YouTube 재생 대상: 검색 키워드(검색 결과 첫 영상 재생) 또는 watch URL 직접 지정
YOUTUBE_QUERIES: list[str] = [
    "4K nature relaxing",
    "lofi hip hop",
    "tech review laptop",
]


# 선택 가능한 시나리오 (key → 표시 이름)
SCENARIOS: dict[str, str] = {
    "idle": "IDLE",
    "web_surfing": "웹서핑 (네이버 검색)",
    "youtube": "YouTube 영상 재생",
}
BROWSER_SCENARIOS = {"web_surfing", "youtube"}
QUALITIES = ["auto", "tiny", "small", "medium", "large", "hd720", "hd1080", "hd1440", "hd2160"]


@dataclass
class ScenarioConfig:
    # 실행할 시나리오와 순서 (SCENARIOS 의 key)
    scenarios: list[str] = field(default_factory=lambda: ["idle", "web_surfing", "youtube"])
    # 시나리오 사이에 삽입할 IDLE 시간 [s] (0 이면 삽입 안 함)
    gap_idle_seconds: float = 0.0
    # 시나리오 전체 반복 횟수
    loops: int = 1
    # IDLE/간격 IDLE 구간에서 브라우저를 종료해 순수 시스템 idle 상태로 측정
    close_browser_on_idle: bool = True

    # Phase 1: IDLE
    idle_seconds: float = 60.0

    # Phase 2: 웹서핑
    surfing_seconds: float = 60.0
    naver_keywords: list[str] = field(default_factory=lambda: list(NAVER_KEYWORDS))
    # 검색 1회당 결과 페이지 체류(스크롤) 시간 범위 [s]
    dwell_range: tuple[float, float] = (8.0, 15.0)
    # 검색 결과 링크 클릭 확률
    click_result_prob: float = 0.5

    # Phase 3: YouTube
    youtube_targets: list[str] = field(default_factory=lambda: list(YOUTUBE_QUERIES))
    video_count: int = 3
    # 영상당 재생 시간 [s]. 0 이하이면 영상 끝까지 재생
    video_seconds: float = 60.0
    # 선호 화질 (tiny/small/medium/large/hd720/hd1080/hd1440/hd2160/auto)
    video_quality: str = "hd1080"
    mute: bool = False

    # Browser
    browser_channel: str | None = None  # "msedge", "chrome", None(=Playwright Chromium)
    browser_path: str | None = None  # Chromium 계열 실행 파일 경로 직접 지정
    headless: bool = False
    window_size: tuple[int, int] = (1920, 1080)

    # 로그 / 모니터링
    output_dir: Path = Path("results")
    sample_interval: float = 1.0
    enable_monitor: bool = True
    keep_awake: bool = True
    seed: int | None = None

    def planned_seconds(self, scenario: str) -> float | None:
        """시나리오 1회 예상 소요 시간 [s]. 영상 끝까지 재생 모드면 None(미정)."""
        if scenario == "idle":
            return self.idle_seconds
        if scenario == "web_surfing":
            return self.surfing_seconds
        if scenario == "youtube":
            return self.video_count * self.video_seconds if self.video_seconds > 0 else None
        raise ValueError(f"알 수 없는 시나리오: {scenario}")
