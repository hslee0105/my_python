# Unity 3D 게임 예제 — "Roll & Collect"

Rigidbody 기반 물리 이동(대시 포함), Cinemachine 3인칭 추적 카메라, 회전하는 수집 아이템(콤보 시스템 + 픽업 사운드·파티클 포함), NavMeshAgent로 플레이어를 추적하는 장애물(닿으면 즉시 게임오버), 코인/적 배치와 개수가 랜덤으로 달라지는 3단계 스테이지 진행, 제한시간 모드, PlayerPrefs 기반 최고 기록, 그리고 재시작 버튼을 갖춘 3D 게임 예제입니다.

## 개발 환경

- **Unity 6 (6000.0 LTS) 기준** (URL: unity.com/download)
- Scripting Backend: Mono (기본값), API Compatibility Level: .NET Standard 2.1 (기본값)
- 스크립트 언어: C# — Unity 런타임(Mono/IL2CPP)은 C#/UnityScript만 지원하며 Python 바인딩이 없어, 본 예제의 게임 로직은 C#으로 작성했습니다. Python으로 Unity 에디터를 자동화하려면 별도의 `UnityPy`/`pythonnet` 브리지가 필요하지만, 이는 표준 게임 스크립팅 경로가 아니므로 이번 예제에는 포함하지 않았습니다.
- **Unity 2021/2022 LTS를 쓰는 경우 주의**: Unity 6에서 `Rigidbody.velocity`가 `Rigidbody.linearVelocity`로 이름이 바뀌었습니다 (구 이름은 Unity 6에서 컴파일 **에러**로 처리됨). 이 저장소의 스크립트는 Unity 6 기준으로 `linearVelocity`를 사용하므로, 2021/2022 LTS에서 열면 반대로 컴파일 에러가 납니다 — 그 경우 `PlayerController.cs`와 `GameManager.cs`의 `linearVelocity`를 `velocity`로 되돌려주세요.
- **Unity 6.5(6000.5) 이상 주의**: `com.unity.ugui`(Unity UI) 패키지가 렌더 파이프라인 패키지 의존성에서 분리되었습니다. `UnityEngine.UI` 네임스페이스를 찾을 수 없다는 `CS0234` 에러가 나면, `Window > Package Manager > + > Add package by name...`에서 `com.unity.ugui`를 직접 설치해야 합니다.
- 내장 폰트 리소스 이름 `"Arial.ttf"`는 최근 Unity 버전에서 폐지되어 `"LegacyRuntime.ttf"`로 대체되었습니다 (`SceneBuilder.cs`는 이미 `LegacyRuntime.ttf`를 사용하도록 반영되어 있음) — 옛 이름을 쓰면 폰트가 null이 되어 UI 텍스트가 화면에 전혀 렌더링되지 않습니다.

### 추가로 필요한 패키지 (Cinemachine 카메라 · NavMeshAgent 추적 AI)

`SceneBuilder.cs`는 이제 아래 두 패키지의 타입을 직접 참조합니다. **Build Scene을 실행하기 전에 먼저 설치**해주세요 (`Window > Package Manager > + > Add package by name...`에 아래 이름을 정확히 입력):

| 패키지 이름 | 용도 |
|---|---|
| `com.unity.cinemachine` | 3인칭 추적 카메라 (Cinemachine 3.x, Unity 6과 함께 배포되는 버전) |
| `com.unity.ai.navigation` | `NavMeshSurface`로 바닥을 NavMesh로 굽는 데 사용 (에디터 전용) |

이 두 패키지가 없으면 `Assets/Editor/SceneBuilder.cs`가 컴파일되지 않아 `Tools > Roll & Collect > Build Scene` 메뉴 자체가 사라집니다. 다만 이 파일은 **에디터 전용 어셈블리**에만 속해 있어서, 패키지가 없어도 `Assets/Scripts` 아래의 런타임 스크립트(`PlayerController.cs` 등)나 이미 저장된 `MainScene.unity`는 영향받지 않습니다 — 즉 패키지 설치 전에 이미 빌드해둔 씬은 계속 Play해서 테스트할 수 있습니다.

`UnityEngine.AI.NavMeshAgent`(적 추적 스크립트 `EnemyChaser.cs`가 사용) 자체는 Unity 코어 모듈에 포함되어 있어 별도 패키지가 필요 없습니다 — `com.unity.ai.navigation`은 오직 NavMesh를 "굽는(bake)" `NavMeshSurface` 컴포넌트에만 필요합니다.

## 폴더 구조

```
UnityGame/
├── Assets/
│   ├── Scripts/
│   │   ├── PlayerController.cs   # WASD 이동 + Space 점프 (Rigidbody 물리)
│   │   ├── CameraFollow.cs       # (더 이상 자동 빌드에선 안 씀) 패키지 없는 SmoothDamp 추적 카메라 대안
│   │   ├── CollectibleItem.cs    # 회전하는 수집 아이템, 트리거 충돌 시 점수+사운드+파티클
│   │   ├── EnemyPatrol.cs        # (더 이상 자동 빌드에선 안 씀) 패키지 없는 좌우 왕복 장애물 대안
│   │   ├── EnemyChaser.cs        # NavMeshAgent로 플레이어를 실시간 추적, 충돌 시 즉시 게임오버
│   │   ├── EnemySpawner.cs       # 스테이지 진행 중 일정 시간마다 적을 한 마리씩 추가 스폰
│   │   ├── GameObjectFactory.cs  # 코인/적 오브젝트를 만드는 공용 헬퍼 (StageManager/EnemySpawner가 공유). Assets/Resources/EnemyCharacter.prefab이 있으면 자동으로 사용
│   │   ├── StageManager.cs       # 스테이지별로 코인/적을 랜덤 배치하고, 클리어 시 다음 스테이지로 전환
│   │   ├── ProceduralAudio.cs    # 외부 오디오 파일 없이 코드로 코인 획득 효과음 생성
│   │   ├── ProceduralEffects.cs  # 내장 ParticleSystem으로 코인 획득 파티클 생성
│   │   └── GameManager.cs        # 점수/스테이지 진행/제한시간/최고기록(PlayerPrefs)/게임오버/재시작/UI 갱신을 담당하는 싱글턴
│   ├── Editor/
│   │   └── SceneBuilder.cs       # 씬 뼈대(바닥/플레이어/카메라/UI/GameManager/StageManager)를 자동으로 조립하는 에디터 확장 (Tools 메뉴)
│   ├── Materials/                # (선택) 색상 구분용 머티리얼
│   └── Scenes/                   # 자동/수동으로 생성된 씬이 저장되는 위치
└── .gitignore                    # Unity가 자동 생성하는 Library/Temp 등 제외
```

씬(.unity) 파일 자체는 GUID 기반 바이너리/YAML 직렬화 구조라 텍스트 편집으로 직접 만들 수 없지만, Unity 에디터의 스크립팅 API(`UnityEditor` 네임스페이스)를 이용하면 씬 조립 과정을 코드로 자동화할 수 있습니다. 아래 "빠른 시작"을 따르면 별도의 수동 작업 없이 메뉴 클릭 한 번으로 전체 씬이 생성됩니다.

## 빠른 시작: 자동 씬 생성 (권장)

1. Unity Hub에서 이 `UnityGame` 폴더를 프로젝트로 열면, `Assets/Editor/SceneBuilder.cs`가 자동으로 컴파일됩니다 (컴파일 완료까지 하단 진행 바가 사라질 때까지 잠시 대기).
2. 에디터 상단 메뉴에서 **Tools > Roll & Collect > Build Scene** 클릭.
3. 다음이 자동으로 수행됩니다:
   - `Assets/Scenes/MainScene.unity` 새 씬 생성 (기존 열린 씬에 저장하지 않은 변경사항이 있으면 저장 여부를 묻는 대화상자가 뜰 수 있음)
   - `Player` 태그가 없으면 TagManager에 자동 등록
   - Floor(Plane) 생성 후 `NavMeshSurface`로 즉시 NavMesh를 굽고, Player 생성 — `Assets/Resources/PlayerCharacter.prefab`이 있으면 그 캐릭터를 사용하고, 없으면 기본 마스코트(Capsule + 구 머리 + 눈 2개)를 사용 (아래 "실제 캐릭터 임포트하기" 참고)
   - Main Camera에 `CinemachineBrain` 부착 + `CM FollowCamera`(`CinemachineCamera` + `CinemachineFollow` + `CinemachineRotationComposer`, target = Player) 생성
   - 빈 `StageManager` 오브젝트 생성 — 코인/적은 씬에 미리 배치하지 않고, Play를 눌러야 `StageManager.Start()`가 스테이지 1의 코인·적을 랜덤 위치에 실제로 생성함
   - Canvas + EventSystem, `ScoreText`/`TimerText`/`BestTimeText`/`ComboText`/`MessageText`/`RestartButton`(초기 비활성화) UI 생성
   - `GameManager` 오브젝트 생성 후 위 UI/설정 값을 `SerializedObject`로 전부 연결 (제한시간 60초, `RestartButton.OnClick → GameManager.RestartGame()` 포함)
   - 씬을 저장하고 `File > Build Settings`의 씬 목록에 자동 등록
4. 콘솔에 `Roll & Collect scene built and saved to Assets/Scenes/MainScene.unity. Press Play to test.` 로그가 뜨면 완료. 바로 상단 ▶ Play 버튼을 눌러 플레이합니다.

다시 실행하면 새 씬을 또 만들어 저장하므로, 자동 생성 결과를 손으로 수정한 뒤에는 재실행하지 않도록 주의하세요.

## 실제 리깅 캐릭터로 교체하기 (선택)

기본 마스코트(Capsule + 머리)나 빨간 큐브 적 대신 진짜 사람 모양의 리깅된 캐릭터를 쓰고 싶다면, Asset Store에서 무료 캐릭터를 받아 아래 규칙대로 배치하면 자동으로 그걸 사용합니다. **플레이어**는 `Assets/Resources/PlayerCharacter.prefab`, **적**은 `Assets/Resources/EnemyCharacter.prefab` — 이름만 다르고 절차는 동일합니다(같은 캐릭터를 색만 다르게 복제해서 둘 다에 써도 되고, 서로 다른 캐릭터를 써도 됩니다).

### 1. 캐릭터 찾기 (검색해볼 만한 후보)

Asset Store(assetstore.unity.com)에서 가격 필터를 **Free**로 두고 아래 같은 걸 검색해보세요:

- **"Unity-Chan!"** — Unity 공식 무료 마스코트 캐릭터, 애니메이션(대기/걷기/달리기) 포함, 정식 Humanoid 리그
- **"RPG Tiny Hero Duo"** (PolyPixel) — 단순한 스타일의 무료 리깅 캐릭터, 초보자가 다루기 쉬움
- 검색창에 그냥 **"free character rigged"** 로 검색해서 나오는 것 중, 미리보기에 **"Humanoid"** 리그와 애니메이션이 포함된다고 적힌 걸 고르면 무난합니다.

Asset Store 목록은 계속 바뀌기 때문에 정확히 이 이름들이 지금도 있다는 보장은 없어요 — 검색해서 나오는 무료 항목 중 하나를 고르시면 됩니다. Mixamo(mixamo.com, Adobe 계정 무료 가입)에서 캐릭터 + 애니메이션을 받아도 동일하게 사용 가능합니다.

### 2. 임포트

1. 웹 브라우저에서 원하는 에셋 페이지 → **"Add to My Assets"** (무료 항목은 바로 추가됨)
2. Unity 에디터로 돌아와서 `Window > Package Manager` → 왼쪽 위 드롭다운을 **"My Assets"**로 전환
3. 방금 추가한 에셋 선택 → **Download** → **Import** → 임포트 창에서 **Import** 버튼 클릭 (전체 선택된 채로 두면 됨)
4. Project 창에서 임포트된 폴더 안의 **캐릭터 프리팹**(보통 `Prefabs` 폴더 안에 있고, 파란색 정육면체 아이콘)을 찾습니다.

### 3. `PlayerCharacter` / `EnemyCharacter`로 등록

1. Project 창에서 `Assets` 폴더 아래에 **`Resources`** 라는 이름의 폴더가 없다면 새로 만듭니다 (우클릭 → `Create > Folder`, 이름을 정확히 `Resources`로).
2. 찾은 캐릭터 프리팹을 **복사해서** `Assets/Resources/` 안에 넣고,
   - 플레이어로 쓰려면 이름을 정확히 **`PlayerCharacter`**로,
   - 적으로 쓰려면 (같은 프리팹을 한 번 더 복사하거나 다른 캐릭터를 받아서) 이름을 정확히 **`EnemyCharacter`**로 바꿉니다.
   (원본 프리팹은 그대로 두고 복사본을 씁니다 — 이름이 겹치면 안 됩니다.)
3. 상단 메뉴 **`Tools > Roll & Collect > Build Scene`**을 다시 실행합니다. `PlayerCharacter`는 씬을 새로 빌드해야 반영되지만, **`EnemyCharacter`는 씬을 다시 빌드하지 않고 그냥 Play만 눌러도 적용됩니다** — 적은 `GameObjectFactory.CreateEnemy()`가 매번 스테이지 시작/스폰 시점에 `Resources.Load`로 즉석에서 찾아 만들기 때문입니다 (반대로 `PlayerCharacter`는 씬을 만드는 시점에 한 번만 확인하는 `SceneBuilder`가 처리하므로 재빌드가 필요합니다).

### 4. 흔히 조정이 필요한 부분

- **캐릭터가 옆으로/거꾸로 걷는 것처럼 보임**: 임포트마다 모델이 기본으로 바라보는 방향(+Z가 아닐 수 있음)이 달라서 그렇습니다. `Player` 오브젝트의 `Player Controller` 컴포넌트에서 **`Model Forward Offset`** 값을 90, 180, -90 등으로 바꿔가며 캐릭터가 이동 방향을 제대로 보는 각도를 찾으세요. (적은 `NavMeshAgent`가 자체적으로 이동 방향을 보도록 회전시키는데, 마찬가지로 모델이 +Z를 안 보고 있으면 어색하게 보일 수 있습니다 — 이 경우는 `EnemyChaser`에 별도 보정 로직을 추가해야 하니 알려주세요.)
- **애니메이션 자체가 회전 방향에 안 맞는 걸음걸이로 보임(옆으로 도는 건 정상인데 걷는 모션만 이상함)**: 이건 모델 방향 문제가 아니라 **그 캐릭터의 Animator Controller 구조**(이동 방향별로 다른 클립을 쓰는 Blend Tree 등) 문제일 수 있습니다. 게임 플레이에 지장이 없다면 넘어가도 되고, 정교하게 고치려면 Animator Controller의 `Parameters`/State 구성을 알려주시면 맞춰드릴 수 있습니다.
- **캐릭터가 바닥에 파묻히거나 떠 있음**: 대부분의 리깅 캐릭터는 발 위치가 피벗(원점)이라 `y = 0`에 놓이도록 만들어뒀는데, 특정 에셋은 다를 수 있습니다. `Player`/`Enemy` 오브젝트를 선택해 Scene 뷰에서 Y 위치를 손으로 조정해보고, 맞는 값을 찾으면(플레이어의 경우) `GameManager`의 `Player Spawn Point` Y 값도 똑같이 맞춰주세요.
- **걷는 애니메이션이 재생되지 않음(플레이어)**: 캐릭터에 `Animator`와 애니메이션은 있지만, `Player Controller`의 **`Speed Parameter Name`**(기본값 `"Speed"`)이 그 캐릭터의 Animator Controller에 있는 실제 파라미터 이름과 다르면 무시됩니다. 캐릭터를 선택해 Inspector에서 `Animator` 컴포넌트의 Controller를 더블클릭해 Animator 창을 열고, `Parameters` 탭에서 이동 속도를 나타내는 float 파라미터 이름을 확인해 `Speed Parameter Name`에 그대로 입력하세요.
- 콜라이더 크기가 안 맞아서 코인을 못 먹거나 적과 이상하게 충돌한다면, 해당 오브젝트의 `Capsule Collider` 컴포넌트에서 `Radius`/`Height`/`Center`를 캐릭터 실제 크기에 맞게 조정하세요.

## 수동 씬 구성 단계 (참고용 / 패키지 없이 단순 버전을 원할 때)

아래 절차는 **Cinemachine과 AI Navigation 패키지를 설치하지 않고도** 만들 수 있는, 조금 더 단순한 원본 버전(고정 오프셋 카메라 `CameraFollow.cs` + 좌우 왕복 장애물 `EnemyPatrol.cs`, 부딪혀도 즉시 게임오버가 아니라 리스폰만 되고, 스테이지 진행도 없는 단일 라운드 버전)을 손으로 재현하는 방법입니다. 지금의 자동 빌드 결과(Cinemachine 카메라, NavMeshAgent 추적 AI + 즉사, 3단계 스테이지)와는 다르니, 두 패키지 설치가 부담스럽다면 이 절차를 참고해 직접 조립하세요.

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
| Left Shift | 대시 (이동 중일 때만, 쿨다운 1초) |

## 동작 원리 요약

- **PlayerController**: `Input.GetAxisRaw`로 수평/수직 입력을 받아 `Rigidbody.velocity`의 X/Z 성분만 직접 갱신 (물리 엔진의 관성/충돌 반응은 유지하면서 즉각적인 반응성을 확보). `Physics.Raycast`로 접지 여부를 판정해 이중 점프를 방지.
- **캐릭터 방향 전환**: `FixedUpdate()`에서 현재 이동 방향(대시 중이면 대시 방향)을 바라보도록 `Quaternion.LookRotation` + `Quaternion.RotateTowards`로 목표 회전을 계산하고, `Rigidbody.MoveRotation()`으로 적용합니다. `Rigidbody`에 `MoveRotation`을 쓰는 이유는, 물리 엔진이 충돌 등으로 임의로 돌리는 것(예전엔 X/Z만 고정했음)과 구분해서 "게임 로직이 의도한 회전"만 매끄럽게(초당 `turnSpeed`, 기본 720도) 적용하기 위함입니다. Rigidbody의 회전 축을 X/Y/Z 모두 고정해뒀기 때문에 물리 충돌로 캐릭터가 옆으로 넘어지거나 제멋대로 도는 일 없이, 오직 이 스크립트가 원하는 방향으로만 부드럽게 돌아갑니다.
- **대시**: `Update()`에서 Shift 입력과 쿨다운을 체크해 `_dashDirection`/`_dashTimeRemaining`을 세팅하고, `FixedUpdate()`에서 `_dashTimeRemaining > 0`인 동안은 평소 이동 속도 대신 `dashSpeed`(기본 20)로 X/Z 속도를 덮어씁니다. 이동 입력이 없을 때는 대시가 발동하지 않도록 `_moveInput.sqrMagnitude > 0.01f`로 가드하며, 쿨다운(기본 1초)이 끝나기 전에는 재발동을 막습니다.
- **캐릭터/코인 모양**: 외부 3D 모델 에셋이 없을 때의 기본값은 프리미티브 조합입니다. 플레이어는 `Capsule`(몸통) + 자식 `Sphere`(머리, 콜라이더 제거해 순수 시각용) + 눈 역할의 작은 검은 `Sphere` 2개로 구성된 마스코트 캐릭터입니다 (`SceneBuilder.BuildPlayerPrimitive()`/`BuildPlayerFace()`). 코인은 `Cube` 대신 아주 얇게 스케일한(`(0.6, 0.08, 0.6)`) `Cylinder`를 써서 동전 모양 디스크로 보이게 했고, `CollectibleItem`이 이미 월드 Y축 기준으로 회전시키고 있어서 코드 변경 없이 "동전이 제자리에서 빙글빙글 도는" 느낌이 그대로 납니다 (`GameObjectFactory.CreateCoin`).
- **실제 캐릭터 임포트 지원**: `SceneBuilder.BuildPlayer()`는 매번 `Resources.Load<GameObject>("PlayerCharacter")`로 `Assets/Resources/PlayerCharacter.prefab`이 있는지 먼저 확인합니다. 있으면 `PrefabUtility.InstantiatePrefab()`으로 그 프리팹을 인스턴스화하고(`BuildPlayerFromImportedCharacter()`), `Rigidbody`/`Collider`가 없으면 자동으로 추가해줍니다 — 어떤 캐릭터를 가져오든 이 스크립트를 수정할 필요가 없도록 설계했습니다. 없으면 기존 기본 마스코트를 만듭니다. 두 경로 모두 이후 `PlayerController`를 붙이고 `groundCheckDistance`를 캡슐/휴머노이드 리그에 맞는 값(1.1)으로 설정하는 공통 로직을 거칩니다. `PlayerController`에는 이 시나리오를 위한 필드도 추가되어 있습니다: `modelForwardOffset`(모델이 +Z를 안 보고 있을 때 보정하는 추가 회전각)과 `speedParameterName`(Animator의 이동 속도 float 파라미터 이름 — `Awake()`에서 실제로 그 이름의 파라미터가 있는지 확인해서, 없으면 매 프레임 경고가 뜨지 않도록 아예 애니메이터 참조를 꺼둡니다).
- **CameraFollow** (수동 버전에서만 사용): `Vector3.SmoothDamp`로 목표 오프셋 위치를 향해 매끄럽게 추적하고, `LookAt`으로 항상 플레이어를 주시.
- **Cinemachine 카메라 (자동 빌드 기본값)**: 실제 `Camera`에는 `CinemachineBrain`만 부착해 "어떤 가상 카메라가 지금 화면을 제어할지" 결정하는 역할을 맡기고, 별도의 `CM FollowCamera` 오브젝트에 실제 추적 로직을 둡니다. `CinemachineCamera.Follow`/`LookAt`으로 대상을 지정하고, Position Control 역할의 `CinemachineFollow`(오프셋 `(0, 6, -8)` 유지)와 Rotation Control 역할의 `CinemachineRotationComposer`(화면 구도 안에 대상을 계속 붙잡아둠)를 조합합니다. 이 둘의 역할 분리(Follow=위치, RotationComposer=조준)가 Cinemachine 3.x의 표준 카메라 파이프라인 구성 방식입니다.
- **CollectibleItem**: `OnTriggerEnter`에서 태그가 `Player`인 콜라이더만 필터링해 `GameManager.AddScore()`를 호출하고, 반환된 콤보 수치로 `ProceduralAudio`/`ProceduralEffects`를 재생한 뒤 자기 자신을 파괴. `Time.deltaTime` 기반 회전으로 시각적 피드백 제공.
- **콤보 시스템**: `GameManager.AddScore()`가 호출될 때마다 직전 픽업 이후 `comboWindow`(기본 1.5초) 이내였는지 확인해 콤보를 이어가거나(`_combo + 1`) 새로 시작합니다(`_combo = 1`). 콤보 2단계부터는 `comboTimeBonusPerStep × (combo - 1)`만큼 제한시간을 되돌려주고 `ComboText`에 "Combo x3! +1.0s" 형태로 잠깐(기본 1초) 표시합니다. `AddScore`가 현재 콤보 수치를 반환하므로, `CollectibleItem`은 이 값을 그대로 `ProceduralAudio.PlayPickupSound`에 넘겨 피치를 올립니다. 콤보는 점수/승리 판정(`_score >= _totalCollectibles`)과는 완전히 분리되어 있어, 아무리 콤보가 쌓여도 코인을 실제로 다 모아야 승리합니다.
- **ProceduralAudio**: `AudioClip.Create`로 샘플 배열(사인파 + 상승하는 주파수 + 제곱 감쇠 엔벌로프)을 직접 채워 짧은 "띵" 효과음을 생성합니다. 외부 오디오 에셋이 전혀 없어도 동작하며, 한 번 생성한 클립은 static 필드에 캐싱해 재사용합니다. `PlayPickupSound`는 임시 `AudioSource`를 직접 만들어 콤보 단계에 비례해 `pitch`를 최대 2배까지 올린 뒤 재생하고, 클립 길이(피치 보정 포함)만큼 뒤에 `Destroy`를 예약해 코인이 `Destroy(gameObject)`로 즉시 사라져도 소리가 끊기지 않습니다 (피치를 재생 전에 정해야 해서 `PlayClipAtPoint` 대신 이 방식을 씁니다).
- **ProceduralEffects**: 내장 `ParticleSystem`을 코드로 구성(짧은 버스트, 구형 방출, `Sprites/Default` 셰이더)해 코인 위치에 파티클을 터뜨립니다. `ParticleSystemStopAction.Destroy`를 설정해 재생이 끝나면 별도 타이머 없이 오브젝트가 자동으로 사라집니다.
- **EnemyPatrol** (수동 버전에서만 사용): `Mathf.PingPong`으로 왕복 운동을 구현 (별도 상태 머신 없이 시간 함수만으로 좌우 이동 구현). 이 버전은 부딪혀도 `GameManager.RespawnPlayer()`로 리스폰만 시킵니다.
- **EnemyChaser (NavMeshAgent)**: `Awake()`에서 `Player` 태그로 플레이어를 찾아두고, `repathInterval`(기본 0.2초)마다 `NavMeshAgent.SetDestination(player.position)`을 호출해 목적지를 갱신합니다. 매 프레임 재계산하지 않고 일정 간격으로만 경로를 다시 잡아 CPU 비용을 줄이는, 실무에서 흔히 쓰는 최적화 패턴입니다. `NavMeshSurface.BuildNavMesh()`로 미리 구워둔 바닥 위를 자율적으로 길찾기하며 이동하고, `OnCollisionEnter`로 플레이어와 부딪히면 **`GameManager.LoseGame()`을 호출해 즉시 게임을 종료**합니다 (리스폰 없음 — 리스폰이 필요한 단순 버전은 `EnemyPatrol`을 쓰세요).
- **GameObjectFactory**: 코인/적을 만드는 코드(프리미티브 또는 임포트 캐릭터 생성, 콜라이더 설정, 색상 지정, `NavMeshAgent`/`EnemyChaser`/`CollectibleItem` 부착)를 한 곳에 모아둔 정적 헬퍼입니다. `StageManager`·`EnemySpawner`(둘 다 런타임)에서 똑같은 방식으로 오브젝트를 만들어야 해서, 중복 대신 이 헬퍼를 공유합니다. `CreateEnemy()`는 `Resources.Load<GameObject>("EnemyCharacter")`를 매번 새로 호출해서, `Assets/Resources/EnemyCharacter.prefab`이 있으면 `Object.Instantiate`로 그 캐릭터를 쓰고 없으면 빨간 큐브를 씁니다(`PrefabUtility`가 아니라 `Object.Instantiate`를 쓰는 이유는, 이 클래스가 런타임 어셈블리에 있어서 빌드에도 포함되기 때문 — 에디터 전용 API는 쓸 수 없습니다). 씬을 다시 빌드할 필요 없이 **다음 스폰/스테이지 전환 시점부터 바로 적용**되는 이유이기도 합니다.
- **StageManager (스테이지 진행)**: 씬에는 코인/적을 전혀 미리 배치하지 않고, `Start()`에서 `GameManager.Instance.EnableMultiStageMode()`로 GameManager를 "스테이지 모드"로 전환한 뒤 스테이지 1을 만듭니다. `stages` 배열(기본 3단계: 6/1마리 → 8/2마리 → 10/3마리)에 정의된 개수만큼 `GameObjectFactory`로 코인·적을 생성하는데, 위치는 `RandomSpawnXZ()`가 지정한 사각 영역(`spawnAreaMin`~`spawnAreaMax`) 안에서 매번 새로 뽑고 플레이어 시작 지점과 너무 가까우면 다시 뽑습니다(최대 20회 시도). 생성한 코인 개수는 `GameManager.SetStageCollectibleCount()`로 알려줘 그 스테이지의 승리 기준으로 삼습니다. `GameManager.OnStageCollected` 이벤트(스테이지 모드에서 `_score >= _totalCollectibles`가 될 때 발생)를 구독해두었다가, 이벤트가 오면 기존 오브젝트를 전부 `Destroy`하고 다음 스테이지를 만들며 `ShowTemporaryMessage()`로 "Stage 2 / 3!" 같은 안내를 잠깐 띄웁니다. 마지막 스테이지까지 클리어하면 다음 스테이지를 만드는 대신 `GameManager.ShowWinMessage()`를 직접 호출해 기존 승리 화면(최고 기록 저장 포함)으로 마무리합니다.
- **EnemySpawner (스테이지 내 시간 경과 난이도 상승)**: 이제 Inspector가 아니라 `Initialize(...)` 메서드로 설정을 주입받습니다 — `StageManager`가 각 스테이지를 만들 때마다 그 스테이지의 적 스폰 지점·시작 속도·이미 배치된 적 수(`wavesSpawned`)로 새로 `Initialize`해서, 스테이지가 바뀔 때마다 카운트가 올바르게 리셋됩니다. `Update()`에서 `spawnInterval`(기본 30초)마다 적을 하나씩 추가로 만들고, 새로 스폰되는 적마다 속도가 빨라지며, 그 스테이지의 `maxEnemies`(적 수 + 3)에 도달하거나 `GameManager.IsGameOver`가 `true`가 되면 더 이상 스폰하지 않습니다.
- **GameManager**: 싱글턴 패턴(`Instance`)으로 전역 접근을 제공합니다. 기본은 단일 스테이지 모드(씬에 미리 배치된 `CollectibleItem` 개수로 승리 판정)지만, `StageManager`가 있으면 `EnableMultiStageMode()`로 전환되어 코인을 다 모을 때마다 곧바로 승리 처리하는 대신 `OnStageCollected` 이벤트만 발생시키고 다음 처리는 `StageManager`에 맡깁니다. 매 프레임 `_elapsedTime`을 누적해 전체 플레이 시간(모든 스테이지 통틀어)을 추적합니다(제한시간 모드를 꺼도 계속 기록됨). `LoseGame()`은 `ShowWinMessage()`/`ShowTimeUpMessage()`와 동일한 종료 처리(재시작 버튼 노출, `Time.timeScale = 0f`)를 하되 "Game Over! An enemy caught you." 메시지를 보여주고, 최고 기록은 갱신하지 않습니다(승리한 게 아니므로).
- **최고 기록 (PlayerPrefs)**: 승리 시 `_elapsedTime`을 `PlayerPrefs`의 `RollCollect_BestTime` 키에 저장된 이전 최고 기록과 비교해, 더 빠르면 갱신하고 "New Best Time!" 메시지를 보여줍니다. `PlayerPrefs`는 macOS에서는 `~/Library/Preferences/`, Windows에서는 레지스트리에 저장되어 에디터를 재시작하거나 씬을 재시작해도 유지됩니다. 화면 상단 중앙의 `BestTimeText`가 기록이 없으면 `Best: --`, 있으면 `Best: 12.3s` 형태로 항상 표시됩니다.
- **제한시간 모드**: `Update()`에서 `Time.deltaTime`만큼 `_timeRemaining`을 감소시키고 `mm:ss` 형식으로 `TimerText`에 표시. 시간이 0이 되면 아직 승리하지 못한 경우 `Time's Up!` 메시지를 띄우고 `_isGameOver` 플래그로 이후의 `AddScore`/`RespawnPlayer` 호출을 무시합니다. 승리·시간초과 두 종료 조건 모두 `Time.timeScale = 0f`로 물리/애니메이션을 포함한 씬 전체를 정지시켜 별도의 입력 잠금 로직 없이 게임을 종료합니다. `Use Time Limit` 체크박스를 끄면 기존처럼 시간 제한 없이 플레이할 수 있습니다.
- **재시작 버튼**: 게임 종료(승리 또는 시간초과) 시 `restartButton.SetActive(true)`로 평소 숨겨져 있던 버튼을 노출합니다. Unity의 UI 이벤트 시스템은 `Time.timeScale`과 무관하게 동작하므로, `Time.timeScale = 0f`로 멈춘 상태에서도 버튼 클릭이 정상적으로 처리됩니다. 버튼의 `OnClick()`에 연결된 `GameManager.RestartGame()`은 `Time.timeScale`을 1로 복구한 뒤 `SceneManager.LoadScene()`으로 현재 씬을 다시 불러와 모든 상태(점수, 타이머, 수집 아이템, 플레이어 위치)를 초기화합니다.
- **SceneBuilder (에디터 자동화)**: `UnityEditor.EditorSceneManager`로 새 씬을 만들고, `GameObject.CreatePrimitive`/`AddComponent`로 오브젝트와 스크립트를 붙인 뒤, 각 컴포넌트의 `private [SerializeField]` 필드는 `SerializedObject.FindProperty(...).objectReferenceValue = ...` 로 (Inspector에서 드래그하는 것과 동일하게) 값을 주입합니다. 버튼 클릭 이벤트는 `UnityEditor.Events.UnityEventTools.AddPersistentListener`로 등록해 Inspector의 `OnClick()` 리스트에 실제로 나타나는 영구 리스너를 생성합니다. 마지막으로 `EditorSceneManager.SaveScene`과 `EditorBuildSettings.scenes`로 씬을 저장하고 빌드 목록에 등록합니다. `[MenuItem]` 특성이 붙어 있어 `Assets/Editor/` 폴더에 있으면(빌드에서 자동 제외) 에디터 메뉴에 즉시 노출됩니다.

## 확장 아이디어

- `Rigidbody.AddForce` 대신 `CharacterController`로 전환해 계단/경사 처리 개선
- `CinemachineDeoccluder`(구 Collider extension)로 장애물에 카메라가 가려질 때 자동 회피
- `EnemyChaser`에 순찰↔추적 상태 전환 추가 (플레이어가 일정 거리 안에 들어오기 전까지는 `EnemyPatrol`처럼 왕복하다가, 감지되면 추적 모드로 전환)
- 파워업 아이템(무적, 속도 증가, 시간 추가) 추가 — `CollectibleItem`을 상속하거나 별도 컴포넌트로 구현
- 최고 기록뿐 아니라 최고 점수(`RollCollect_BestScore`)도 별도로 `PlayerPrefs`에 저장해 시간초과/게임오버로 끝난 라운드의 기록도 남기기
- 대시에 쿨다운 게이지 UI를 추가해 언제 다시 쓸 수 있는지 시각적으로 표시
- 진짜 사람 모양/리깅된 캐릭터가 필요하다면, `Window > Package Manager > My Assets` (Asset Store 무료 캐릭터를 계정에 추가한 경우) 또는 Mixamo에서 받은 FBX를 `Assets`로 드래그해 임포트한 뒤, `SceneBuilder.BuildPlayer()`가 Capsule을 만드는 대신 그 프리팹을 `Instantiate`하도록 바꾸면 됩니다 (Animator/애니메이션 클립 연결은 별도 작업 필요)
- 적 큐브도 `GameObjectFactory.CreateEnemy`를 수정해 눈 2개를 붙이거나 다른 프리미티브 조합으로 "괴물처럼" 꾸미기
- `StageManager.stages`에 스테이지별 제한시간이나 특수 규칙(예: 마지막 스테이지는 시간 보너스 없음)을 추가해 스테이지마다 다른 긴장감 부여
- `StageManager.RandomSpawnXZ()`가 코인끼리도 최소 거리를 두도록 검사를 추가해 겹쳐서 스폰되는 경우 방지
