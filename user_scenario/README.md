# user_scenario — Laptop 사용자 시나리오 자동화

전력/발열/성능 측정용 표준 사용자 시나리오를 Playwright로 자동 실행합니다.

| Phase | 내용 | 기본값 |
|---|---|---|
| 1. `idle` | 브라우저 미실행 상태로 대기 (baseline) | 60 s |
| 2. `web_surfing` | 네이버 메인 → 랜덤 키워드 타이핑/검색 → 휠 스크롤 → 확률적으로 결과 링크 클릭 → 반복 | 60 s |
| 3. `youtube` | YouTube 검색어/URL로 영상 3개 순차 재생 (광고 스킵, 화질 고정) | 영상당 60 s |

## 설치

```bash
pip install -r user_scenario/requirements.txt
playwright install chromium   # --browser msedge / chrome 사용 시 생략 가능
```

## 실행

```bash
# 기본 시나리오
python -m user_scenario

# Edge 사용, 영상 끝까지 재생, 4K 고정, 3회 반복
python -m user_scenario --browser msedge --video-seconds 0 --quality hd2160 --loops 3

# 재생할 영상을 URL로 고정 (측정 재현성 확보 시 권장)
python -m user_scenario --videos https://www.youtube.com/watch?v=AAA https://www.youtube.com/watch?v=BBB https://www.youtube.com/watch?v=CCC

# 키워드 풀 지정 + 시드 고정
python -m user_scenario --keywords "노트북" "GPU" "날씨" --seed 42
```

전체 옵션은 `python -m user_scenario --help`를 참고하세요.

## 결과물 (`results/<YYYYMMDD_HHMMSS>/`)

- `phases.csv` — 페이즈(및 영상별 서브 페이즈) 시작/종료 시각. ISO8601 + epoch를 같이 남기므로 Power meter, PresentMon, HWiNFO, GPU-Z 로그와 타임스탬프로 정렬할 수 있습니다.
- `resource.csv` — psutil로 수집한 1 s 간격 CPU 사용률(전체/최대 코어/코어별), CPU 주파수, 메모리 사용량. 각 행에 현재 phase가 태깅됩니다.
- `youtube.csv` — 영상별 URL·제목, 실제 본편 재생 시간, 광고 시간, 디코딩 해상도, `getVideoPlaybackQuality()` 기반 total/dropped frames 및 drop rate(광고 구간 제외).
- `run.log` — 실행 로그.

## 측정 시 참고

- **Headed 모드(기본)로 측정하세요.** `--headless`는 compositor/GPU 경로가 달라 실사용 부하를 대표하지 못합니다.
- Windows에서는 실행 중 `SetThreadExecutionState`로 디스플레이/시스템 슬립을 막습니다 (`--allow-sleep`으로 해제).
- IDLE 페이즈는 `time.sleep`만 사용하고 로그도 15 s 간격으로만 남겨, 스크립트 자체가 Package C-state 진입을 방해하지 않도록 했습니다. 다만 Python 프로세스와 1 s psutil 샘플러가 남아 있으므로, 엄밀한 idle 전력 측정 시에는 `--no-monitor`를 사용하세요.
- Playwright Chromium에는 독점 코덱이 없어 YouTube가 VP9/AV1을 사용합니다. 하드웨어 디코더(HW decode) 경로까지 실사용과 같게 하려면 `--browser msedge` 또는 `--browser chrome`을 권장합니다.
- 검색어 기반 재생은 결과가 날마다 달라지므로, 회차 간 비교 측정에는 `--videos`로 URL을 고정하세요.
- 네이버/YouTube 마크업이 바뀌면 셀렉터(`phases/web_surfing.py`의 `RESULT_LINK_SELECTORS`, `phases/youtube.py`의 상수)를 수정해야 할 수 있습니다. 네이버 검색창 입력에 실패하면 검색 URL을 직접 호출하는 방식으로 자동 전환됩니다.
