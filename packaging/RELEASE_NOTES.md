## User Scenario Controller v1.0.2 (Windows 64-bit)

Laptop 성능·전력·발열 측정용 사용자 시나리오 자동화 도구입니다. Python 설치 없이 실행됩니다.

> v1.0.0 / v1.0.1 사용자는 v1.0.2로 교체하세요. 이전 버전은 YouTube 재생이 멈춘 상태도 정상 재생으로 기록할 수 있습니다.

### v1.0.2 변경 사항
- **YouTube 재생 시간 측정 수정**: 실제 재생 위치(`currentTime`) 증가량만 `played_s`로 집계. 이전 버전은 플레이어가 멈춰 있어도 일시정지가 아니면 재생 시간으로 셌고 `status: ok`로 기록함
- **플레이어 내부 오류 감지**: 플레이어 오류 화면(봇 확인, 재생 불가 등)이 뜨면 원인·스크린샷을 남기고 해당 영상을 `error`로 기록
- **연속 재생 정지 처리**: 새로고침 후에도 재생이 진행되지 않으면 `stalled`로 기록 (타임아웃까지 대기하지 않음)

### v1.0.1 변경 사항
- **YouTube 재생 실패 진단**: 영상 플레이어(`<video>`)가 나타나지 않으면 원인(봇 확인/로그인 요구, 연령 확인, 재생 불가 영상, 쿠키 동의 화면)을 로그와 `youtube.csv`에 남기고, 결과 폴더에 스크린샷(`youtube_fail_v<번호>_try<시도>.png`)을 저장한 뒤 새로고침 후 1회 재시도
- **CLI 한글 로그 오류 수정**: 영문 Windows 콘솔/파이프 출력에서 발생하던 `UnicodeEncodeError` 수정

### 다운로드 / 실행
1. `UserScenario-v1.0.2-win64.zip`을 쓰기 가능한 폴더(예: `C:\Tools`)에 압축 해제
2. `UserScenario\UserScenario.exe` 실행 (TFMonitor 연동 시 **관리자 권한으로 실행**)
3. 자세한 사용법은 압축 안의 `README_KR.txt` 참고

### 기능
- **시나리오**: IDLE / 네이버 웹서핑(랜덤 키워드 검색·스크롤·결과 클릭) / YouTube 영상 N개 재생(광고 스킵, 화질 고정, dropped frame 통계)
- **GUI Controller**: 시나리오 선택·순서·유지 시간, 시나리오 사이 IDLE, 반복 횟수, 진행률·실시간 로그, 설정 자동 저장
- **TFMonitor 연동**: Start/Stop 자동 클릭, FAN 0/1 RPM · C0 (CPU) 온도 로깅, 관리자 권한 확인 및 재실행
- **FAN 분석**: 전체/시나리오별 꺾은선 그래프, 시나리오별 평균·최대·p95·팬 동작 비율·RPM 변동 횟수 통계
- **측정 로그**: 페이즈 시작/종료 타임스탬프(외부 측정 장비 로그 정렬용), CPU/메모리 사용률
- **CLI** (`UserScenarioCLI.exe`): 배치 자동화, `fan-analysis`(그래프 재생성), `tfmonitor --dump`(진단)

### 요구 사항
- Windows 10/11 64-bit, Microsoft Edge 또는 Google Chrome
- TFMonitor 연동 시 관리자 권한
