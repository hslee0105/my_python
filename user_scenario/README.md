# user_scenario — Laptop 사용자 시나리오 자동화

전력/발열/성능 측정용 표준 사용자 시나리오를 Playwright로 자동 실행합니다.

| 시나리오 | 내용 | 기본값 |
|---|---|---|
| 1. `idle` | 브라우저 미실행 상태로 대기 (baseline) | 60 s |
| 2. `web_surfing` | 네이버 메인 → 랜덤 키워드 타이핑/검색 → 휠 스크롤 → 확률적으로 결과 링크 클릭 → 반복 | 60 s |
| 3. `youtube` | YouTube 검색어/URL로 영상 3개 순차 재생 (광고 스킵, 화질 고정) | 영상당 60 s |

## 배포판 (Windows exe, Python 불필요)

[Releases](https://github.com/hslee0105/my_python/releases)에서 `UserScenario-vX.Y.Z-win64.zip`을 받아 압축을 풀고 `UserScenario.exe`(GUI) 또는 `UserScenarioCLI.exe`(명령줄)를 실행합니다. 사용법은 zip 안의 `README_KR.txt`를 참고하세요.

빌드는 `.github/workflows/build-windows.yml`이 Windows 러너에서 수행합니다 (PyInstaller → 스모크 테스트 → zip → 버전 태그가 없으면 Release 생성). 새 버전 배포는 `user_scenario/__init__.py`의 `__version__`을 올려 push하면 됩니다.

```bat
:: 로컬 빌드 (Windows)
pip install -r packaging\requirements-build.txt
pyinstaller packaging\user_scenario.spec --noconfirm --clean
:: → dist\UserScenario\
```

## 설치 (소스 실행)

```bash
pip install -r user_scenario/requirements.txt
playwright install chromium   # --browser msedge / chrome 사용 시 생략 가능
# (Windows에서는 pywinauto가 함께 설치되어 TFMonitor 연동에 사용됩니다)
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

### 시나리오 선택 · 순서 · 간격 IDLE (CLI)

```bash
# 웹서핑 → YouTube 순서로, 시나리오 사이에 30초 IDLE 삽입, 2회 반복
python -m user_scenario --scenarios web_surfing youtube --gap 30 --loops 2
```

`--gap`으로 넣은 간격 IDLE은 반복 회차 사이에도 들어가며, `phases.csv`에 `gap_idle`로 기록됩니다.
기본적으로 IDLE/간격 IDLE 구간에서는 브라우저를 닫습니다(`--keep-browser`로 유지). 브라우저 기동은 페이즈 마커 밖에서 수행되므로 측정 구간에 섞이지 않습니다.

## GUI Controller

```bash
python -m user_scenario --gui
```

- **시나리오 선택 · 순서 · 유지 시간**: 체크한 시나리오를 위에서부터 실행, ▲/▼로 순서 변경. IDLE·웹서핑은 유지 시간, YouTube는 영상 수와 영상당 재생 시간(0 = 끝까지).
- **실행 설정**: 시나리오 사이 IDLE 시간, 반복 횟수, IDLE 구간 브라우저 종료 여부.
- **브라우저 · 측정 옵션**: 브라우저(Edge/Chrome/Playwright Chromium), 화질, 음소거, 리소스 모니터링, 결과 폴더.
- **키워드 · 영상 목록**: 네이버 검색 키워드, YouTube URL/검색어를 한 줄에 하나씩 편집.
- 실행 계획 미리보기(순서와 예상 총 소요 시간), 현재 단계/전체 진행률, 실시간 로그, ■ 중지, 결과 폴더 열기.
- 설정은 `~/.user_scenario_gui.json`에 자동 저장되어 다음 실행 때 복원됩니다.

중지 버튼을 누르면 IDLE은 즉시, 브라우저 동작은 진행 중인 단일 동작(최대 Playwright timeout 15 s)이 끝나는 대로 멈추고 그때까지의 결과 파일을 정리합니다.

## TFMonitor 연동 (FAN RPM · CPU 온도 로깅, Windows)

시나리오 시작 시 TFMonitor를 실행(이미 떠 있으면 연결)하고 **[Start]**를 클릭한 뒤, 시나리오가 끝날 때까지 아래 값을 주기적으로 읽어 기록합니다. 종료 시 **[Stop]**을 클릭하고 시나리오별 그래프와 통계를 생성합니다.

| CSV 컬럼 | TFMonitor 위치 |
|---|---|
| `fan0_rpm` | FAN Status › FAN 0 RPM |
| `fan1_rpm` | FAN Status › FAN 1 RPM |
| `cpu_temp_c` | Micom Data › C0 (CPU) › **Dec** |

```bash
# GUI: "5. TFMonitor 연동"에서 사용 체크 + TFMonitor.exe 경로 지정 → [연결 테스트]로 값 매핑 확인
python -m user_scenario --gui

# CLI (--elevate: 관리자 권한이 아니면 UAC 승인 후 새 창에서 관리자 권한으로 재실행)
python -m user_scenario --elevate --tfmon --tfmon-exe "C:\Tools\TFMonitor\TFMonitor.exe" --tfmon-interval 1

# 분석만 다시 실행
python -m user_scenario.fan_analysis results/20261014_120000

# 진단: 컨트롤 목록 출력 / 값 1회 읽기
python -m user_scenario.tfmonitor --dump
python -m user_scenario.tfmonitor --read
```

- 텍스트박스에 이름이 없는 WinForms/MFC 앱이라도 동작하도록, **라벨 텍스트 + 같은 행 좌표**로 값 칸을 찾습니다(예: `C0 (CPU)` 행의 두 번째 칸 = Dec). 레이아웃이 다른 버전이면 `tfmonitor.py`의 `FIELDS`를 수정하세요.
- 버튼은 창 메시지(WM_LBUTTONDOWN/UP)로 누르므로 실제 마우스/포커스를 빼앗지 않습니다(브라우저 시나리오에 영향 없음).
- 연결에 실패하면 시나리오를 시작하지 않습니다(FAN 데이터 없는 측정 방지).
- 창 제목은 기본 `^TFMonitor v\d`(예: `TFMonitor v1.21.0.0`)로 찾습니다. 같은 이름의 탐색기 폴더 창에 잘못 붙지 않도록 버전 표기까지 매칭합니다.

### 관리자 권한 (중요)

TFMonitor는 EC/센서 드라이버에 접근하므로 관리자 권한이 필요하고, Windows **UIPI**는 일반 권한 프로세스가 관리자 권한 창에 보내는 클릭/텍스트 읽기 메시지를 **오류 없이 무시**합니다. 그래서 TFMonitor만 UAC로 올려 실행하면 "실행은 됐는데 Start가 안 눌리고 값이 비어 있는" 상태가 됩니다.

확실히 동작하는 구성은 **이 프로그램을 관리자 권한으로 실행 → TFMonitor를 직접 실행해 권한을 상속**시키는 것입니다.

| 방법 | |
|---|---|
| GUI | TFMonitor 연동이 켜진 상태에서 [시작]/[연결 테스트]를 누르면 관리자 권한 재실행을 제안합니다 (설정 유지). "관리자 권한으로 다시 실행" 버튼도 있습니다. 관리자 권한이면 창 제목에 `[관리자]`가 붙습니다. |
| CLI | `--elevate` 옵션, 또는 관리자 권한 명령 프롬프트에서 실행 |
| 권한 확인 끄기 | TFMonitor가 일반 권한에서도 동작하는 환경이면 GUI의 "관리자 권한 필요" 체크 해제 / CLI `--tfmon-no-admin` |

연결 시 다음 상황은 시나리오 시작 전에 원인을 알려 주고 중단합니다.

- 이 프로그램이 일반 권한인데 TFMonitor가 관리자 권한으로 이미 실행 중 (UIPI 차단)
- TFMonitor exe가 관리자 권한을 요구(ERROR_ELEVATION_REQUIRED, 740)하는데 이 프로그램이 일반 권한
- TFMonitor가 실행 직후 종료됨 (드라이버 로드 실패 등, exit code 표시)
- 실행했지만 창이 제한 시간 안에 나타나지 않음 (오류 대화상자, 창 제목 불일치)

Start 클릭 후 10초 동안 값이 비어 있으면 경고를 남깁니다.

### FAN 분석 결과물

- `fan.csv` — 샘플별 시각, 페이즈, FAN0/FAN1 RPM, CPU 온도
- `fan_timeline.png` — 전체 시간축 꺾은선 (위: FAN0/FAN1 RPM, 아래: CPU 온도). 시나리오 구간은 회색 음영과 이름으로 표시
- `fan_phases/NN_<시나리오>_loopK.png` — 시나리오 실행 1회별 꺾은선 (x = 시나리오 시작 후 경과 시간)
- `fan_summary.png` — 시나리오 종류별 평균(막대)과 최대(선 끝 점) RPM/온도 비교
- `fan_summary.csv` — 시나리오 실행 1회별 통계, `fan_summary_by_scenario.csv` — 시나리오 종류별 집계 (Excel에서 한글이 깨지지 않도록 UTF-8 BOM)

| 통계 컬럼 | 의미 |
|---|---|
| `*_avg / min / max / p95 / std` | 평균 / 최소 / 최대 / 95퍼센타일 / 표준편차 |
| `*_start / *_end` | 시나리오 시작·종료 시점 값 (램프업·쿨다운 확인) |
| `fanN_rpm_on_ratio_pct` | RPM > 0 인 샘플 비율 (팬 동작 비율, 0 RPM 팬 정지 정책 확인) |
| `fanN_rpm_level_changes` | RPM 값이 바뀐 횟수 (팬 hunting/소음 변동 지표) |
| `cpu_temp_c_delta` | 시나리오 동안 온도 변화 (끝 − 시작) |

RPM과 온도는 단위가 달라 이중 Y축 대신 위아래 두 패널로 나눴습니다. 샘플은 `phases.csv`의 시작/종료 epoch 기준으로 시나리오에 배정됩니다.

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
