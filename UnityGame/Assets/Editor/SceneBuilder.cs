using System.Collections.Generic;
using Unity.AI.Navigation;
using Unity.Cinemachine;
using UnityEditor;
using UnityEditor.Events;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.EventSystems;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

// Editor-only automation: assembles the full "Roll & Collect" scene
// (floor, player, camera, collectibles, enemy, UI, GameManager) and
// wires every reference, so the manual steps in README.md can be
// skipped. Run via Tools > Roll & Collect > Build Scene.
public static class SceneBuilder
{
    private const string ScenePath = "Assets/Scenes/MainScene.unity";
    private static readonly Vector3[] CoinPositions =
    {
        new Vector3(3f, 0.5f, 3f),
        new Vector3(-3f, 0.5f, 3f),
        new Vector3(3f, 0.5f, -3f),
        new Vector3(-3f, 0.5f, -3f),
        new Vector3(0f, 0.5f, 5f),
        new Vector3(0f, 0.5f, -5f),
    };

    [MenuItem("Tools/Roll & Collect/Build Scene")]
    public static void BuildScene()
    {
        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

        EnsureTag("Player");

        BuildFloor();
        GameObject player = BuildPlayer();
        BuildCinemachineCamera(player.transform);
        BuildCollectibles();
        BuildEnemies();

        Text scoreText, timerText, bestTimeText, comboText, messageText;
        GameObject restartButtonObj;
        BuildUI(out scoreText, out timerText, out bestTimeText, out comboText, out messageText, out restartButtonObj);

        BuildGameManager(scoreText, timerText, bestTimeText, comboText, messageText, restartButtonObj);

        SaveSceneAndRegister(scene);

        Debug.Log($"Roll & Collect scene built and saved to {ScenePath}. Press Play to test.");
    }

    private static GameObject BuildFloor()
    {
        GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
        floor.name = "Floor";
        floor.transform.localScale = new Vector3(3f, 1f, 3f);

        NavMeshSurface surface = floor.AddComponent<NavMeshSurface>();
        surface.BuildNavMesh();

        return floor;
    }

    private static GameObject BuildPlayer()
    {
        GameObject player = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        player.name = "Player";
        player.transform.position = new Vector3(0f, 1f, 0f);
        player.tag = "Player";

        Rigidbody rb = player.AddComponent<Rigidbody>();
        rb.constraints = RigidbodyConstraints.FreezeRotationX | RigidbodyConstraints.FreezeRotationZ;

        player.AddComponent<PlayerController>();
        return player;
    }

    private static void BuildCinemachineCamera(Transform target)
    {
        Camera mainCamera = Camera.main;
        if (mainCamera == null)
        {
            GameObject camObj = new GameObject("Main Camera");
            camObj.tag = "MainCamera";
            mainCamera = camObj.AddComponent<Camera>();
            camObj.AddComponent<AudioListener>();
        }
        mainCamera.gameObject.AddComponent<CinemachineBrain>();

        GameObject vcamObj = new GameObject("CM FollowCamera");
        CinemachineCamera vcam = vcamObj.AddComponent<CinemachineCamera>();
        vcam.Follow = target;
        vcam.LookAt = target;

        CinemachineFollow follow = vcamObj.AddComponent<CinemachineFollow>();
        follow.FollowOffset = new Vector3(0f, 6f, -8f);

        vcamObj.AddComponent<CinemachineRotationComposer>();
    }

    private static void BuildCollectibles()
    {
        GameObject parent = new GameObject("Collectibles");

        foreach (Vector3 pos in CoinPositions)
        {
            GameObject coin = GameObject.CreatePrimitive(PrimitiveType.Cube);
            coin.name = "Coin";
            coin.transform.SetParent(parent.transform);
            coin.transform.position = pos;
            coin.transform.localScale = Vector3.one * 0.4f;

            Collider coinCollider = coin.GetComponent<Collider>();
            coinCollider.isTrigger = true;
            coin.AddComponent<CollectibleItem>();

            SetInstanceColor(coin, Color.yellow);
        }
    }

    private static readonly Vector3[] EnemySpawnPoints =
    {
        new Vector3(5f, 0f, 5f),
        new Vector3(-5f, 0f, -5f),
        new Vector3(5f, 0f, -5f),
        new Vector3(-5f, 0f, 5f),
    };
    private const float EnemyBaseSpeed = 3.5f;
    private const float EnemySpawnInterval = 30f;

    // Places one enemy immediately, then adds an EnemySpawner that spawns
    // another every EnemySpawnInterval seconds (ramping difficulty up over
    // a long round instead of starting with every enemy already active).
    private static void BuildEnemies()
    {
        BuildEnemy(EnemySpawnPoints[0], EnemyBaseSpeed);

        GameObject spawnerObj = new GameObject("EnemySpawner");
        EnemySpawner spawner = spawnerObj.AddComponent<EnemySpawner>();

        SerializedObject spawnerSO = new SerializedObject(spawner);
        SerializedProperty spawnPointsProp = spawnerSO.FindProperty("spawnPoints");
        spawnPointsProp.arraySize = EnemySpawnPoints.Length;
        for (int i = 0; i < EnemySpawnPoints.Length; i++)
        {
            spawnPointsProp.GetArrayElementAtIndex(i).vector3Value = EnemySpawnPoints[i];
        }
        spawnerSO.FindProperty("spawnInterval").floatValue = EnemySpawnInterval;
        spawnerSO.FindProperty("baseSpeed").floatValue = EnemyBaseSpeed;
        spawnerSO.FindProperty("wavesSpawned").intValue = 1;
        spawnerSO.ApplyModifiedProperties();
    }

    private static void BuildEnemy(Vector3 position, float speed)
    {
        GameObject enemy = GameObject.CreatePrimitive(PrimitiveType.Cube);
        enemy.name = "Enemy";
        enemy.transform.position = position;
        SetInstanceColor(enemy, Color.red);

        NavMeshAgent agent = enemy.AddComponent<NavMeshAgent>();
        agent.baseOffset = 0.5f;
        agent.speed = speed;
        agent.radius = 0.4f;

        enemy.AddComponent<EnemyChaser>();
    }

    private static void SetInstanceColor(GameObject go, Color color)
    {
        Renderer renderer = go.GetComponent<Renderer>();
        Material instanceMaterial = new Material(renderer.sharedMaterial) { color = color };
        renderer.sharedMaterial = instanceMaterial;
    }

    private static void BuildUI(out Text scoreText, out Text timerText, out Text bestTimeText, out Text comboText, out Text messageText, out GameObject restartButtonObj)
    {
        GameObject canvasObj = new GameObject("Canvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
        Canvas canvas = canvasObj.GetComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;

        CanvasScaler scaler = canvasObj.GetComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920f, 1080f);

        if (Object.FindObjectOfType<EventSystem>() == null)
        {
            new GameObject("EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));
        }

        scoreText = CreateUIText(canvasObj.transform, "ScoreText",
            new Vector2(0f, 1f), new Vector2(150f, -40f), new Vector2(280f, 50f),
            "Score: 0 / 0", TextAnchor.MiddleLeft);

        timerText = CreateUIText(canvasObj.transform, "TimerText",
            new Vector2(1f, 1f), new Vector2(-150f, -40f), new Vector2(280f, 50f),
            "Time: 01:00", TextAnchor.MiddleRight);

        bestTimeText = CreateUIText(canvasObj.transform, "BestTimeText",
            new Vector2(0.5f, 1f), new Vector2(0f, -40f), new Vector2(280f, 50f),
            "Best: --", TextAnchor.MiddleCenter);

        comboText = CreateUIText(canvasObj.transform, "ComboText",
            new Vector2(0f, 1f), new Vector2(150f, -90f), new Vector2(320f, 50f),
            string.Empty, TextAnchor.MiddleLeft);
        comboText.color = Color.yellow;

        messageText = CreateUIText(canvasObj.transform, "MessageText",
            new Vector2(0.5f, 0.5f), new Vector2(0f, 60f), new Vector2(700f, 80f),
            string.Empty, TextAnchor.MiddleCenter);
        messageText.fontSize = 40;

        restartButtonObj = BuildRestartButton(canvasObj.transform);
    }

    private static Text CreateUIText(Transform parent, string name, Vector2 anchor, Vector2 anchoredPosition, Vector2 sizeDelta, string content, TextAnchor alignment)
    {
        GameObject go = new GameObject(name, typeof(RectTransform), typeof(Text));
        go.transform.SetParent(parent, false);

        RectTransform rect = go.GetComponent<RectTransform>();
        rect.anchorMin = anchor;
        rect.anchorMax = anchor;
        rect.pivot = new Vector2(0.5f, 0.5f);
        rect.anchoredPosition = anchoredPosition;
        rect.sizeDelta = sizeDelta;

        Text text = go.GetComponent<Text>();
        text.text = content;
        text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        text.fontSize = 32;
        text.alignment = alignment;
        text.color = Color.white;
        return text;
    }

    private static GameObject BuildRestartButton(Transform parent)
    {
        GameObject buttonObj = new GameObject("RestartButton", typeof(RectTransform), typeof(Image), typeof(Button));
        buttonObj.transform.SetParent(parent, false);

        RectTransform rect = buttonObj.GetComponent<RectTransform>();
        rect.anchorMin = new Vector2(0.5f, 0.5f);
        rect.anchorMax = new Vector2(0.5f, 0.5f);
        rect.pivot = new Vector2(0.5f, 0.5f);
        rect.anchoredPosition = new Vector2(0f, -60f);
        rect.sizeDelta = new Vector2(200f, 60f);

        Image image = buttonObj.GetComponent<Image>();
        image.color = new Color(0.15f, 0.15f, 0.15f, 0.9f);

        GameObject labelObj = new GameObject("Text", typeof(RectTransform), typeof(Text));
        labelObj.transform.SetParent(buttonObj.transform, false);
        RectTransform labelRect = labelObj.GetComponent<RectTransform>();
        labelRect.anchorMin = Vector2.zero;
        labelRect.anchorMax = Vector2.one;
        labelRect.offsetMin = Vector2.zero;
        labelRect.offsetMax = Vector2.zero;

        Text label = labelObj.GetComponent<Text>();
        label.text = "Restart";
        label.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        label.fontSize = 28;
        label.alignment = TextAnchor.MiddleCenter;
        label.color = Color.white;

        buttonObj.SetActive(false);
        return buttonObj;
    }

    private static void BuildGameManager(Text scoreText, Text timerText, Text bestTimeText, Text comboText, Text messageText, GameObject restartButtonObj)
    {
        GameObject gmObj = new GameObject("GameManager");
        GameManager gameManager = gmObj.AddComponent<GameManager>();

        SerializedObject gmSO = new SerializedObject(gameManager);
        gmSO.FindProperty("scoreText").objectReferenceValue = scoreText;
        gmSO.FindProperty("timerText").objectReferenceValue = timerText;
        gmSO.FindProperty("bestTimeText").objectReferenceValue = bestTimeText;
        gmSO.FindProperty("comboText").objectReferenceValue = comboText;
        gmSO.FindProperty("messageText").objectReferenceValue = messageText;
        gmSO.FindProperty("restartButton").objectReferenceValue = restartButtonObj;
        gmSO.FindProperty("playerSpawnPoint").vector3Value = new Vector3(0f, 1f, 0f);
        gmSO.FindProperty("useTimeLimit").boolValue = true;
        gmSO.FindProperty("timeLimitSeconds").floatValue = 60f;
        gmSO.ApplyModifiedProperties();

        Button restartButton = restartButtonObj.GetComponent<Button>();
        UnityEventTools.AddPersistentListener(restartButton.onClick, gameManager.RestartGame);
    }

    private static void SaveSceneAndRegister(Scene scene)
    {
        if (!AssetDatabase.IsValidFolder("Assets/Scenes"))
        {
            AssetDatabase.CreateFolder("Assets", "Scenes");
        }

        EditorSceneManager.MarkSceneDirty(scene);
        EditorSceneManager.SaveScene(scene, ScenePath);

        List<EditorBuildSettingsScene> scenes = new List<EditorBuildSettingsScene>(EditorBuildSettings.scenes);
        if (scenes.FindIndex(s => s.path == ScenePath) < 0)
        {
            scenes.Add(new EditorBuildSettingsScene(ScenePath, true));
            EditorBuildSettings.scenes = scenes.ToArray();
        }
    }

    private static void EnsureTag(string tagName)
    {
        SerializedObject tagManager = new SerializedObject(
            AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
        SerializedProperty tagsProp = tagManager.FindProperty("tags");

        for (int i = 0; i < tagsProp.arraySize; i++)
        {
            if (tagsProp.GetArrayElementAtIndex(i).stringValue == tagName) return;
        }

        tagsProp.InsertArrayElementAtIndex(tagsProp.arraySize);
        tagsProp.GetArrayElementAtIndex(tagsProp.arraySize - 1).stringValue = tagName;
        tagManager.ApplyModifiedProperties();
    }
}
