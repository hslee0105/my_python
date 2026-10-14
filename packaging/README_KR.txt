User Scenario Controller - 배포판
=================================

Laptop 성능/전력/발열 측정용 사용자 시나리오 자동화 도구입니다.
(IDLE / 네이버 웹서핑 / YouTube 재생 + TFMonitor FAN RPM·CPU 온도 로깅)

Python 설치가 필요 없습니다. 압축을 원하는 폴더(예: C:\Tools\UserScenario)에 풀고 실행하세요.
※ "C:\Program Files" 처럼 쓰기 권한이 없는 폴더는 피하세요 (결과가 exe 옆 results 폴더에 저장됨).


[실행]

  UserScenario.exe       GUI (더블클릭)
  UserScenarioCLI.exe    명령줄 / 자동화 / 진단용 (명령 프롬프트에서 실행)

  * TFMonitor 연동 시 관리자 권한이 필요합니다.
    - UserScenario.exe 를 마우스 오른쪽 → "관리자 권한으로 실행", 또는
    - GUI 의 "관리자 권한으로 다시 실행" 버튼 (창 제목에 [관리자] 표시 확인)
  * 브라우저는 PC 에 설치된 Microsoft Edge(기본) 또는 Google Chrome 을 사용합니다.
    ("Playwright Chromium" 항목은 배포판에서 사용하지 마세요)


[GUI 사용 순서]

  1. 시나리오 체크 / ▲▼ 순서 / 유지 시간(s), YouTube 영상 수·영상당 시간(0=끝까지)
  2. 시나리오 사이 IDLE(s), 반복 횟수
  3. 브라우저(Edge 권장), 화질, 결과 폴더
  4. 네이버 키워드, YouTube URL/검색어 (한 줄에 하나)
  5. TFMonitor 연동: 사용 체크 → TFMonitor.exe 경로 지정 → [연결 테스트]
  → ▶ 시작  → 완료 후 [FAN 그래프] / [결과 폴더]


[명령줄 예시]

  UserScenarioCLI.exe --help
  UserScenarioCLI.exe --browser msedge --scenarios idle web_surfing youtube --gap 30 --loops 2
  UserScenarioCLI.exe --elevate --browser msedge --tfmon --tfmon-exe "C:\Tools\TFMonitor\TFMonitor.exe"
  UserScenarioCLI.exe fan-analysis results\20261014_120000     (그래프/통계 다시 생성)
  UserScenarioCLI.exe tfmonitor --dump                         (TFMonitor 컨트롤 목록 - 문제 보고용)


[결과물]  results\<날짜_시간>\

  phases.csv              시나리오별 시작/종료 시각 (외부 측정 로그 정렬용)
  fan.csv                 FAN0/FAN1 RPM, CPU 온도 원본 로그
  fan_timeline.png        전체 시간축 꺾은선 (위 RPM / 아래 온도, 시나리오 구간 음영)
  fan_phases\*.png        시나리오 실행 1회별 꺾은선
  fan_summary.png/.csv    시나리오별 평균·최대 RPM/온도, 팬 동작 비율, RPM 변동 횟수
  resource.csv            CPU/메모리 사용률
  youtube.csv             영상별 재생 시간, 해상도, dropped frames
  run.log                 실행 로그 (문제 보고 시 첨부)


[문제 해결]

  "관리자 권한이 필요합니다"       → 관리자 권한으로 실행
  "TFMonitor 창을 찾지 못함"       → exe 경로 / 창 제목(TFMonitor v1.x) 확인
  "실행 직후 종료됨 (exit code N)" → TFMonitor 를 직접 관리자 권한으로 실행해 정상인지 확인
  Start 후 값이 비어 있다는 경고   → UserScenarioCLI.exe tfmonitor --dump 출력 공유
  Windows SmartScreen 경고         → "추가 정보" → "실행" (서명되지 않은 사내 배포 도구)
