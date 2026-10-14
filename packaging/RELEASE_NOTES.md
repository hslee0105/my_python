## User Scenario Controller v1.0.0 (Windows 64-bit)

Laptop 성능·전력·발열 측정용 사용자 시나리오 자동화 도구 첫 배포판입니다. Python 설치 없이 실행됩니다.

### 다운로드 / 실행
1. `UserScenario-v1.0.0-win64.zip`을 쓰기 가능한 폴더(예: `C:\Tools`)에 압축 해제
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
