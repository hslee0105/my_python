using UnityEngine;

// Escalates difficulty within a stage: spawns one additional
// NavMeshAgent chaser enemy every `spawnInterval` seconds, cycling
// through the given spawn points. Configured via Initialize() rather
// than the Inspector, since instances are created procedurally by
// SceneBuilder (edit time) or StageManager (runtime, once per stage).
public class EnemySpawner : MonoBehaviour
{
    private Vector3[] _spawnPoints = { new Vector3(5f, 0f, 5f) };
    private float _spawnInterval = 30f;
    private float _baseSpeed = 3.5f;
    private float _speedIncreasePerWave = 0.5f;
    private int _wavesSpawned = 1;
    private int _maxEnemies = 6;

    private float _timer;

    public void Initialize(Vector3[] spawnPoints, float spawnInterval, float baseSpeed, float speedIncreasePerWave, int wavesAlreadySpawned, int maxEnemies)
    {
        if (spawnPoints != null && spawnPoints.Length > 0) _spawnPoints = spawnPoints;
        _spawnInterval = spawnInterval;
        _baseSpeed = baseSpeed;
        _speedIncreasePerWave = speedIncreasePerWave;
        _wavesSpawned = wavesAlreadySpawned;
        _maxEnemies = maxEnemies;
        _timer = 0f;
    }

    private void Update()
    {
        if (GameManager.Instance != null && GameManager.Instance.IsGameOver) return;
        if (_wavesSpawned >= _maxEnemies) return;

        _timer += Time.deltaTime;
        if (_timer < _spawnInterval) return;

        _timer = 0f;
        Vector3 position = _spawnPoints[_wavesSpawned % _spawnPoints.Length];
        GameObjectFactory.CreateEnemy(position, _baseSpeed + _speedIncreasePerWave * _wavesSpawned);
        _wavesSpawned++;
    }
}
