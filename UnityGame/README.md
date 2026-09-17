# Unity 3D 게임 예제 — "Roll & Collect"

Rigidbody 기반 물리 이동, 3인칭 추적 카메라, 회전하는 수집 아이템, 좌우로 순찰하는 장애물, 점수/승리 UI를 갖춘 최소 구성의 3D 게임 예제입니다.

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
│   │   └── GameManager.cs        # 점수/승리 조건/UI 갱신을 담당하는 싱글턴
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
   - `Canvas` 하위에 Text 2개 배치: `ScoreText`(좌상단), `MessageText`(화면 중앙, 승리 메시지용).
9. **GameManager**
   - 빈 `GameObject`를 생성, 이름을 `GameManager`로 변경.
   - `GameManager.cs` 스크립트를 추가.
   - Inspector에서 `Score Text`에 `ScoreText`를, `Message Text`에 `MessageText`를, `Player Spawn Point`에 플레이어 초기 위치(예: `0, 1, 0`)를 지정.
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

## 확장 아이디어

- `NavMeshAgent`를 이용한 적 AI 추적 로직
- `Cinemachine` 패키지로 카메라 전환을 더 매끄럽게 (충돌 회피 포함)
- `Rigidbody.AddForce` 대신 `CharacterController`로 전환해 계단/경사 처리 개선
- 타이머 기반 제한시간 모드 추가 (`GameManager`에 `Time.deltaTime` 카운트다운 추가)
