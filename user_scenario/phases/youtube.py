"""Phase 3: YouTube 영상 N개 순차 재생.

- target 이 URL 이면 바로 재생, 아니면 YouTube 검색 후 첫 번째 일반 영상(Shorts/광고 제외) 재생
- 광고 자동 스킵, 화질 고정(best-effort), 재생 상태 감시(stall 시 재시도)
- 영상별 재생 통계(getVideoPlaybackQuality: total/dropped frames, 해상도) 수집
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict, dataclass
from urllib.parse import quote_plus

from pathlib import Path

from playwright.sync_api import BrowserContext, Page
from playwright.sync_api import TimeoutError as PWTimeout

log = logging.getLogger("scenario.youtube")

SEARCH_URL = "https://www.youtube.com/results?search_query={q}"
SKIP_AD_SELECTORS = ".ytp-skip-ad-button, .ytp-ad-skip-button, .ytp-ad-skip-button-modern"
# <video> 가 안 뜰 때 원인 추정용 문구 (페이지 본문 기준, 소문자 비교)
BLOCK_PATTERNS = {
    "봇 확인/로그인 요구 (데이터센터·VPN IP 차단 가능)": ["confirm you're not a bot", "confirm you’re not a bot",
                                                 "봇이 아님을 확인", "sign in to confirm"],
    "연령 확인 필요": ["confirm your age", "연령 확인", "age-restricted"],
    "재생 불가 영상": ["video unavailable", "동영상을 재생할 수 없습니다", "this video isn't available",
                  "이 동영상은 사용할 수 없습니다"],
    "쿠키/약관 동의 화면": ["before you continue", "계속하기 전에"],
}
CONSENT_SELECTORS = [  # EU 등 일부 지역 쿠키 동의창
    "button[aria-label^='Accept all']",
    "button[aria-label^='모두 수락']",
    "form[action*='consent'] button",
]

# 재생 상태 조회용 JS (movie_player 비공식 API + HTMLVideoElement 사용)
JS_STATUS = """() => {
  const v = document.querySelector('video.html5-main-video') || document.querySelector('video');
  const p = document.getElementById('movie_player');
  if (!v) return null;
  const q = v.getVideoPlaybackQuality ? v.getVideoPlaybackQuality() : {};
  return {
    currentTime: v.currentTime, duration: v.duration, paused: v.paused, ended: v.ended,
    ad: !!(p && p.classList.contains('ad-showing')),
    width: v.videoWidth, height: v.videoHeight,
    totalFrames: q.totalVideoFrames || 0, droppedFrames: q.droppedVideoFrames || 0,
    quality: p && p.getPlaybackQuality ? p.getPlaybackQuality() : '',
    title: document.title.replace(/ - YouTube$/, ''),
  };
}"""

JS_PLAY = """(mute) => {
  const v = document.querySelector('video.html5-main-video') || document.querySelector('video');
  if (!v) return false;
  v.muted = mute;
  if (v.paused) v.play().catch(() => {});
  return true;
}"""

JS_SET_QUALITY = """(q) => {
  const p = document.getElementById('movie_player');
  if (!p || !p.setPlaybackQualityRange) return false;
  p.setPlaybackQualityRange(q, q);
  if (p.setPlaybackQuality) p.setPlaybackQuality(q);
  return true;
}"""


@dataclass
class VideoStat:
    index: int
    target: str
    url: str = ""
    title: str = ""
    played_s: float = 0.0
    ad_s: float = 0.0
    resolution: str = ""
    quality: str = ""
    total_frames: int = 0
    dropped_frames: int = 0
    drop_rate_pct: float = 0.0
    status: str = "pending"


class YouTubePhase:
    def __init__(self, context: BrowserContext, targets: list[str], count: int = 3,
                 play_seconds: float = 60.0, quality: str = "hd1080", mute: bool = False,
                 on_video=None, stop_event: threading.Event | None = None,
                 diag_dir: Path | None = None) -> None:
        self.context = context
        self.targets = targets
        self.count = count
        self.play_seconds = play_seconds
        self.quality = quality
        self.mute = mute
        self.on_video = on_video  # 영상별 페이즈 마커 기록용 콜백(context manager factory)
        self.stats: list[VideoStat] = []
        self.stop = stop_event or threading.Event()
        self.diag_dir = diag_dir  # 재생 실패 시 스크린샷 저장 위치

    def run(self) -> list[VideoStat]:
        page = self.context.pages[0] if self.context.pages else self.context.new_page()
        played_urls: set[str] = set()
        for i in range(self.count):
            if self.stop.is_set():
                break
            target = self.targets[i % len(self.targets)]
            stat = VideoStat(index=i + 1, target=target)
            self.stats.append(stat)
            cm = self.on_video(f"youtube_video_{i + 1}", target) if self.on_video else _null_cm()
            with cm:
                try:
                    url = self._resolve(page, target, exclude=played_urls)
                    played_urls.add(url)
                    stat.url = url
                    self._play(page, url, stat)
                except Exception as e:
                    stat.status = f"error: {e!r}"[:200]
                    log.warning("영상 %d 재생 실패: %r", i + 1, e)
            log.info("영상 %d 결과: %s", i + 1, asdict(stat))
        return self.stats

    # ------------------------------------------------------------------ steps
    def _resolve(self, page: Page, target: str, exclude: set[str]) -> str:
        if target.startswith("http"):
            return target
        log.info("YouTube 검색: '%s'", target)
        page.goto(SEARCH_URL.format(q=quote_plus(target)), wait_until="domcontentloaded", timeout=20_000)
        self._dismiss_consent(page)
        page.wait_for_selector("ytd-video-renderer a#video-title", timeout=20_000)
        for href in page.eval_on_selector_all(
            "ytd-video-renderer a#video-title",
            "els => els.map(e => e.href).filter(h => h && h.includes('/watch?v='))",
        ):
            url = href.split("&")[0]
            if url not in exclude:
                return url
        raise RuntimeError("검색 결과에서 재생 가능한 영상을 찾지 못함")

    def _play(self, page: Page, url: str, stat: VideoStat) -> None:
        log.info("재생 시작: %s", url)
        page.goto(url, wait_until="domcontentloaded", timeout=20_000)
        self._dismiss_consent(page)
        self._wait_video(page, stat)

        quality_set = False
        last_t, last_progress = -1.0, time.monotonic()
        started = time.monotonic()
        content_s = 0.0
        prev_tick = time.monotonic()
        base_frames = None  # 광고 구간 프레임은 제외하기 위해 본편 시작 시점 기준값 저장
        s = None

        while True:
            now = time.monotonic()
            dt, prev_tick = now - prev_tick, now
            s = page.evaluate(JS_STATUS)
            if s is None:
                if self.stop.wait(0.5):
                    stat.status = "stopped"
                    return
                continue

            if s["ad"]:
                stat.ad_s += dt
                self._skip_ad(page)
            else:
                if base_frames is None:
                    base_frames = (s["totalFrames"], s["droppedFrames"])
                if not quality_set and self.quality != "auto":
                    quality_set = bool(page.evaluate(JS_SET_QUALITY, self.quality))
                if not s["paused"]:
                    content_s += dt

            page.evaluate(JS_PLAY, self.mute)  # autoplay 차단/일시정지 대비

            # 진행 감시: 15초간 currentTime 변화 없으면 reload
            if abs(s["currentTime"] - last_t) > 0.05:
                last_t, last_progress = s["currentTime"], now
            elif now - last_progress > 15:
                log.warning("재생 정지(stall) 감지 → 새로고침")
                page.reload(wait_until="domcontentloaded")
                last_progress = now

            if not s["ad"]:
                if s["ended"]:
                    stat.status = "ended"
                    break
                if self.play_seconds > 0 and content_s >= self.play_seconds:
                    stat.status = "ok"
                    break
            # 안전장치: 광고/버퍼링 포함 최대 대기 시간
            limit = (self.play_seconds if self.play_seconds > 0 else (s["duration"] or 3600)) + 120
            if now - started > limit:
                stat.status = "timeout"
                break
            if self.stop.wait(1.0):
                stat.status = "stopped"
                break

        stat.played_s = round(content_s, 1)
        stat.ad_s = round(stat.ad_s, 1)
        stat.title = s["title"]
        stat.resolution = f'{s["width"]}x{s["height"]}'
        stat.quality = s["quality"]
        b_total, b_drop = base_frames or (0, 0)
        stat.total_frames = max(0, s["totalFrames"] - b_total)
        stat.dropped_frames = max(0, s["droppedFrames"] - b_drop)
        if stat.total_frames:
            stat.drop_rate_pct = round(100 * stat.dropped_frames / stat.total_frames, 3)
        page.evaluate("() => { const v = document.querySelector('video'); if (v) v.pause(); }")

    def _wait_video(self, page: Page, stat: VideoStat) -> None:
        """<video> 대기. 실패하면 원인 진단(스크린샷/차단 문구) 후 1회 새로고침 재시도."""
        for attempt in (1, 2):
            try:
                page.wait_for_selector("video", state="attached", timeout=20_000)
                return
            except PWTimeout:
                reason = self._diagnose(page, stat.index, attempt)
                if attempt == 1:
                    log.warning("영상 %d: <video> 없음 (%s) → 새로고침 후 재시도", stat.index, reason)
                    page.reload(wait_until="domcontentloaded", timeout=20_000)
                    self._dismiss_consent(page)
        raise RuntimeError(f"<video> 요소 없음 - {reason}")

    def _diagnose(self, page: Page, index: int, attempt: int) -> str:
        try:
            title = page.title()
            body = (page.inner_text("body", timeout=3_000) or "").lower()
        except Exception as e:
            return f"페이지 확인 실패: {e!r}"[:200]
        reason = next((name for name, pats in BLOCK_PATTERNS.items() if any(p in body for p in pats)),
                      "원인 미상")
        shot = ""
        if self.diag_dir is not None:
            path = self.diag_dir / f"youtube_fail_v{index}_try{attempt}.png"
            try:
                page.screenshot(path=str(path))
                shot = f", 스크린샷 {path.name}"
            except Exception:
                pass
        log.warning("영상 %d 진단: %s | 제목 '%s' | URL %s%s", index, reason, title, page.url, shot)
        return reason

    @staticmethod
    def _skip_ad(page: Page) -> None:
        btn = page.locator(SKIP_AD_SELECTORS).first
        try:
            if btn.is_visible():
                btn.click(timeout=2_000)
                log.info("광고 스킵")
        except Exception:
            pass

    @staticmethod
    def _dismiss_consent(page: Page) -> None:
        for sel in CONSENT_SELECTORS:
            btn = page.locator(sel).first
            try:
                if btn.is_visible():
                    btn.click(timeout=3_000)
                    page.wait_for_load_state("domcontentloaded")
                    return
            except Exception:
                pass


class _null_cm:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
