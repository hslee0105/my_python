# Unity 3D 게임 예제 — "Roll & Collect"

Rigidbody 기반 물리 이동, 3인칭 추적 카메라, 회전하는 수집 아이템, 좌우로 순찰하는 장애물, 점수/승리 UI, 제한시간 모드, 그리고 재시작 버튼을 갖춘 최소 구성의 3D 게임 예제입니다.

## 개발 환경

- Unity 2021 LTS 또는 2022 LTS (URL: unity.com/download)
- Scripting Backend: Mono (기본값), API Compatibility Level: .NET Standard 2.1 (기본값)
- 스크립트 언어: C# — Unity 런타임(Mono/IL2CPP)은 C#/UnityScript만 지원하며 Python 바인딩이 없어, 본 예제의 게임 로직은 C#으로 작성했습니다. Python으로 Unity 에디터를 자동화하려면 별도의 `UnityPy`/`pythonnet` 브리지가 필요하지만, 이는 표준 게임 스크립팅 경로가 아니므로 이번 예제에는 포함하지 않았습니다.

## 폴더 구조

```
UnityGame/
├── Assets/
│   ├── Scripts/
│   │   ├── PlayerController.cs   # WASD 이동 + Space 점프 (Rigidbody 물리)
│   │   ├── CameraFollow.cs       # 부드러운 3인칭 추적 카메라
│   │   ├── CollectibleItem.cs    # 회전하는 수집 아이템, 트리거 충돌 시 점수 획득
│   │   ├── EnemyPatrol.cs        # 좌우로 왕복 이동하는 장애물, 충돌 시 리스폰
│   │   └── GameManager.cs        # 점수/승리 조건/제한시간/재시작/UI 갱신을 담당하는 싱글턴
│   ├── Materials/                # (선택) 색상 구분용 머티리얼
│   └── Scenes/                   # 신규 씬을 저장할 위치
└── .gitignore                    # Unity가 자동 생성하는 Library/Temp 등 제외
```

씬(.unity) 파일은 GUID 기반 바이너리/YAML 직렬화 구조라 에디터 밖에서 안전하게 생성할 수 없으므로, 아래 단계에 따라 Unity 에디터에서 직접 구성합니다. 5~10분이면 충분합니다.

## 씬 구성 단계

1. **새 프로젝트 생성**: Unity Hub에서 3D (URP or Built-in) 템플릿으로 새 프로젝트를 만들고, 이 저장소의 `UnityGame/Assets` 폴더 내용을 프로젝트의 `Assets` 폴더로 복사(또는 이 폴더를 그대로 Unity 프로젝트 루트로 열기)합니다.
2. **씬 생성**: `Assets/Scenes` 에 새 씬(`MainScene`)을 만들고 엽니다.
3. **바닥(Floor)**
   - `GameObject > 3D Object > Plane` 생성, 이름을 `Floor`로 변경.
   - Scale을 `(3, 1, 3)` 정도로 키워 넓은 바닥을 만듭니다.
4. **플레이어(Player)**
   - `GameObject > 3D Object > Sphere` 생성, 이름을 `Player`로 변경.
   - Position을 `(0, 1, 0)`으로 설정.
   - `Add Component > Rigidbody` 추가 (Freeze Rotation X/Z 체크 권장 — 굴러가는 시각 효과가 싫다면).
   - Tag를 `Player`로 지정 (Inspector 상단 Tag 드롭다운에서 `Add Tag...`로 새로 만들 수 있음).
   - `PlayerController.cs` 스크립트를 추가.
5. **카메라(Main Camera)**
   - 씬의 `Main Camera`를 선택.
   - `CameraFollow.cs` 스크립트를 추가하고, Inspector의 `Target` 필드에 `Player`를 드래그하여 연결.
6. **수집 아이템(Collectibles)**
   - `GameObject > 3D Object > Cube` (또는 Sphere) 생성, 이름을 `Coin`으로 변경.
   - Scale을 `(0.4, 0.4, 0.4)` 정도로 축소.
   - Box/Sphere Collider의 `Is Trigger` 체크박스를 켬.
   - `CollectibleItem.cs` 스크립트를 추가.
   - 이 `Coin`을 프리팹화(`Assets` 폴더로 드래그)한 뒤, 바닥 위 여러 위치에 5~10개 복제 배치.
7. **장애물(Enemy/Obstacle)** — 선택 사항
   - `GameObject > 3D Object > Cube` 생성, 이름을 `Enemy`로 변경, 붉은색 머티리얼 적용.
   - `Rigidbody`는 추가하지 않고 (Kinematic 이동), 일반 `Box Collider` 유지 (Is Trigger 체크 해제).
   - `EnemyPatrol.cs` 스크립트를 추가.
8. **UI 캔버스**
   - `GameObject > UI > Text` 생성 (자동으로 `Canvas`와 `EventSystem`이 함께 생성됨).
   - `Canvas` 하위에 Text 3개 배치: `ScoreText`(좌상단), `TimerText`(우상단), `MessageText`(화면 중앙, 승리/게임오버 메시지용).
   - `GameObject > UI > Button` 으로 `RestartButton` 생성, 화면 중앙 하단에 배치. 자식 `Text`의 문구를 "Restart"로 변경. 평소에는 보이지 않아야 하므로 **Inspector 우상단 체크박스를 해제하여 비활성화**해 둡니다 (게임오버 시 스크립트가 다시 활성화함).
9. **GameManager**
   - 빈 `GameObject`를 생성, 이름을 `GameManager`로 변경.
   - `GameManager.cs` 스크립트를 추가.
   - Inspector에서 `Score Text`에 `ScoreText`를, `Message Text`에 `MessageText`를, `Timer Text`에 `TimerText`를, `Restart Button`에 `RestartButton`을, `Player Spawn Point`에 플레이어 초기 위치(예: `0, 1, 0`)를 지정.
   - `Use Time Limit` 체크박스로 제한시간 모드 On/Off, `Time Limit Seconds`로 제한 시간(초, 기본 60초)을 조절.
   - `RestartButton`의 `Button` 컴포넌트에서 `On Click()` 리스트에 `+`를 눌러 `GameManager` 오브젝트를 드래그하고, 함수 드롭다운에서 `GameManager > RestartGame()`을 선택해 연결합니다.
   - `File > Build Settings...` 에서 `Add Open Scenes`로 현재 씬을 빌드 목록에 추가해 둡니다 (재시작 시 `SceneManager.LoadScene`이 현재 씬의 build index를 참조하므로, 목록에 없으면 재시작이 동작하지 않습니다).
10. **재생(Play)**: 상단 Play 버튼을 눌러 테스트합니다.

## 조작법

| 입력 | 동작 |
|---|---|
| W / A / S / D (또는 방향키) | 이동 |
| Space | 점프 (지면에 닿아 있을 때만) |

## 동작 원리 요약

- **PlayerController**: `Input.GetAxisRaw`로 수평/수직 입력을 받아 `Rigidbody.velocity`의 X/Z 성분만 직접 갱신 (물리 엔진의 관성/충돌 반응은 유지하면서 즉각적인 반응성을 확보). `Physics.Raycast`로 접지 여부를 판정해 이중 점프를 방지.
- **CameraFollow**: `Vector3.SmoothDamp`로 목표 오프셋 위치를 향해 매끄럽게 추적하고, `LookAt`으로 항상 플레이어를 주시.
- **CollectibleItem**: `OnTriggerEnter`에서 태그가 `Player`인 콜라이더만 필터링해 점수를 올리고 자기 자신을 파괴. `Time.deltaTime` 기반 회전으로 시각적 피드백 제공.
- **EnemyPatrol**: `Mathf.PingPong`으로 왕복 운동을 구현 (별도 상태 머신 없이 시간 함수만으로 좌우 이동 구현).
- **GameManager**: 싱글턴 패턴(`Instance`)으로 전역 접근을 제공하며, 씬 시작 시 `FindObjectsOfType<CollectibleItem>()`으로 전체 아이템 수를 캐싱해 승리 조건(`score >= total`)을 판정.
- **제한시간 모드**: `Update()`에서 `Time.deltaTime`만큼 `_timeRemaining`을 감소시키고 `mm:ss` 형식으로 `TimerText`에 표시. 시간이 0이 되면 아직 승리하지 못한 경우 `Time's Up!` 메시지를 띄우고 `_isGameOver` 플래그로 이후의 `AddScore`/`RespawnPlayer` 호출을 무시합니다. 승리·시간초과 두 종료 조건 모두 `Time.timeScale = 0f`로 물리/애니메이션을 포함한 씬 전체를 정지시켜 별도의 입력 잠금 로직 없이 게임을 종료합니다. `Use Time Limit` 체크박스를 끄면 기존처럼 시간 제한 없이 플레이할 수 있습니다.
- **재시작 버튼**: 게임 종료(승리 또는 시간초과) 시 `restartButton.SetActive(true)`로 평소 숨겨져 있던 버튼을 노출합니다. Unity의 UI 이벤트 시스템은 `Time.timeScale`과 무관하게 동작하므로, `Time.timeScale = 0f`로 멈춘 상태에서도 버튼 클릭이 정상적으로 처리됩니다. 버튼의 `OnClick()`에 연결된 `GameManager.RestartGame()`은 `Time.timeScale`을 1로 복구한 뒤 `SceneManager.LoadScene()`으로 현재 씬을 다시 불러와 모든 상태(점수, 타이머, 수집 아이템, 플레이어 위치)를 초기화합니다.

## 확장 아이디어

- `NavMeshAgent`를 이용한 적 AI 추적 로직
- `Cinemachine` 패키지로 카메라 전환을 더 매끄럽게 (충돌 회피 포함)
- `Rigidbody.AddForce` 대신 `CharacterController`로 전환해 계단/경사 처리 개선
- 라운드마다 최고 점수를 `PlayerPrefs`에 저장하는 하이스코어 기능 추가
