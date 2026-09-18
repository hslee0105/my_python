using UnityEngine;
using UnityEngine.AI;

// Escalates difficulty over time: spawns one additional NavMeshAgent
// chaser enemy every `spawnInterval` seconds, cycling through
// `spawnPoints`. The enemy already placed in the scene by SceneBuilder
// counts as the first wave, so `wavesSpawned` starts at 1.
public class EnemySpawner : MonoBehaviour
{
    [SerializeField] private Vector3[] spawnPoints = { new Vector3(5f, 0f, 5f) };
    [SerializeField] private float spawnInterval = 30f;
    [SerializeField] private float baseSpeed = 3.5f;
    [SerializeField] private float speedIncreasePerWave = 0.5f;
    [SerializeField] private int maxEnemies = 6;
    [SerializeField] private int wavesSpawned = 1;

    private float _timer;

    private void Update()
    {
        if (GameManager.Instance != null && GameManager.Instance.IsGameOver) return;
        if (wavesSpawned >= maxEnemies) return;

        _timer += Time.deltaTime;
        if (_timer < spawnInterval) return;

        _timer = 0f;
        SpawnEnemy();
    }

    private void SpawnEnemy()
    {
        Vector3 position = spawnPoints[wavesSpawned % spawnPoints.Length];

        GameObject enemy = GameObject.CreatePrimitive(PrimitiveType.Cube);
        enemy.name = "Enemy";
        enemy.transform.position = position;

        Renderer renderer = enemy.GetComponent<Renderer>();
        renderer.sharedMaterial = new Material(renderer.sharedMaterial) { color = Color.red };

        NavMeshAgent agent = enemy.AddComponent<NavMeshAgent>();
        agent.baseOffset = 0.5f;
        agent.speed = baseSpeed + speedIncreasePerWave * wavesSpawned;
        agent.radius = 0.4f;

        enemy.AddComponent<EnemyChaser>();

        wavesSpawned++;
    }
}
