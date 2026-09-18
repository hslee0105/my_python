using System;
using System.Collections.Generic;
using UnityEngine;

// Owns multi-stage progression: builds a randomized layout of coins and
// enemies for the current stage, and advances to the next (harder)
// stage whenever GameManager reports the current stage's coins are all
// collected. After the last stage, GameManager's normal win screen
// (with the best-time save) is shown instead of advancing further.
public class StageManager : MonoBehaviour
{
    [Serializable]
    public class StageConfig
    {
        public int coinCount = 6;
        public int enemyCount = 1;
    }

    [SerializeField] private StageConfig[] stages =
    {
        new StageConfig { coinCount = 6, enemyCount = 1 },
        new StageConfig { coinCount = 8, enemyCount = 2 },
        new StageConfig { coinCount = 10, enemyCount = 3 },
    };

    [SerializeField] private Vector2 spawnAreaMin = new Vector2(-8f, -8f);
    [SerializeField] private Vector2 spawnAreaMax = new Vector2(8f, 8f);
    [SerializeField] private float minDistanceFromPlayerStart = 2.5f;
    [SerializeField] private float enemySpeedPerStage = 0.5f;
    [SerializeField] private float enemySpawnInterval = 30f;

    private int _stageIndex;
    private readonly List<GameObject> _stageObjects = new List<GameObject>();

    private void Start()
    {
        if (GameManager.Instance == null)
        {
            Debug.LogError("StageManager: no GameManager in the scene; stage progression disabled.", this);
            return;
        }

        GameManager.Instance.EnableMultiStageMode();
        GameManager.Instance.OnStageCollected += HandleStageCollected;

        BuildStage(0);
    }

    private void OnDestroy()
    {
        if (GameManager.Instance != null)
        {
            GameManager.Instance.OnStageCollected -= HandleStageCollected;
        }
    }

    private void HandleStageCollected()
    {
        ClearStageObjects();

        _stageIndex++;
        if (_stageIndex >= stages.Length)
        {
            GameManager.Instance.ShowWinMessage();
            return;
        }

        GameManager.Instance.ShowTemporaryMessage($"Stage {_stageIndex + 1} / {stages.Length}!", 2f);
        BuildStage(_stageIndex);
    }

    private void BuildStage(int index)
    {
        StageConfig config = stages[index];
        float enemySpeed = 3.5f + enemySpeedPerStage * index;

        for (int i = 0; i < config.coinCount; i++)
        {
            Vector2 xz = RandomSpawnXZ();
            _stageObjects.Add(GameObjectFactory.CreateCoin(new Vector3(xz.x, 0.5f, xz.y)));
        }

        Vector3[] enemySpawnPoints = new Vector3[config.enemyCount];
        for (int i = 0; i < config.enemyCount; i++)
        {
            Vector2 xz = RandomSpawnXZ();
            Vector3 pos = new Vector3(xz.x, 0f, xz.y);
            enemySpawnPoints[i] = pos;
            _stageObjects.Add(GameObjectFactory.CreateEnemy(pos, enemySpeed));
        }

        GameObject spawnerObj = new GameObject("EnemySpawner");
        EnemySpawner spawner = spawnerObj.AddComponent<EnemySpawner>();
        spawner.Initialize(enemySpawnPoints, enemySpawnInterval, enemySpeed, enemySpeedPerStage, config.enemyCount, config.enemyCount + 3);
        _stageObjects.Add(spawnerObj);

        GameManager.Instance.SetStageCollectibleCount(config.coinCount);
    }

    private void ClearStageObjects()
    {
        foreach (GameObject obj in _stageObjects)
        {
            if (obj != null) Destroy(obj);
        }
        _stageObjects.Clear();
    }

    private Vector2 RandomSpawnXZ()
    {
        Vector2 point;
        int attempts = 0;
        do
        {
            point = new Vector2(
                UnityEngine.Random.Range(spawnAreaMin.x, spawnAreaMax.x),
                UnityEngine.Random.Range(spawnAreaMin.y, spawnAreaMax.y));
            attempts++;
        } while (point.magnitude < minDistanceFromPlayerStart && attempts < 20);

        return point;
    }
}
