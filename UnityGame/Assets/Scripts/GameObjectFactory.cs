using UnityEngine;
using UnityEngine.AI;

// Shared runtime construction for coins and NavMeshAgent-chasing
// enemies, so SceneBuilder (editor time), StageManager, and
// EnemySpawner (both at runtime) all build identical objects instead
// of duplicating the same primitive/component setup three times.
public static class GameObjectFactory
{
    public static GameObject CreateCoin(Vector3 position)
    {
        // A flattened Cylinder reads as a coin/disc; CollectibleItem already
        // spins it around the world Y axis, which — combined with this
        // shape — looks like a coin lying flat and spinning in place.
        GameObject coin = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        coin.name = "Coin";
        coin.transform.position = position;
        coin.transform.localScale = new Vector3(0.6f, 0.08f, 0.6f);

        Collider collider = coin.GetComponent<Collider>();
        collider.isTrigger = true;
        coin.AddComponent<CollectibleItem>();

        SetColor(coin, new Color(1f, 0.84f, 0.2f)); // warm gold, richer than flat yellow
        return coin;
    }

    // If a rigged character prefab has been placed at
    // Assets/Resources/EnemyCharacter.prefab (same convention as the
    // player's PlayerCharacter.prefab), use it as the enemy's visual
    // instead of the plain red Cube.
    private const string EnemyCharacterResourceName = "EnemyCharacter";

    public static GameObject CreateEnemy(Vector3 position, float speed)
    {
        GameObject enemyCharacterPrefab = Resources.Load<GameObject>(EnemyCharacterResourceName);
        GameObject enemy = enemyCharacterPrefab != null
            ? Object.Instantiate(enemyCharacterPrefab, position, Quaternion.identity)
            : CreateEnemyPrimitive(position);
        enemy.name = "Enemy";

        if (enemy.GetComponent<Collider>() == null)
        {
            CapsuleCollider capsule = enemy.AddComponent<CapsuleCollider>();
            capsule.center = new Vector3(0f, 1f, 0f);
            capsule.height = 2f;
            capsule.radius = 0.4f;
        }

        NavMeshAgent agent = enemy.GetComponent<NavMeshAgent>();
        if (agent == null) agent = enemy.AddComponent<NavMeshAgent>();
        // Imported characters are usually feet-pivoted (no lift needed);
        // the primitive Cube's pivot is centered, so it needs baseOffset
        // to sit on the floor instead of clipping halfway into it.
        agent.baseOffset = enemyCharacterPrefab != null ? 0f : 0.5f;
        agent.speed = speed;
        agent.radius = 0.4f;

        if (enemy.GetComponent<EnemyChaser>() == null)
        {
            enemy.AddComponent<EnemyChaser>();
        }

        return enemy;
    }

    private static GameObject CreateEnemyPrimitive(Vector3 position)
    {
        GameObject enemy = GameObject.CreatePrimitive(PrimitiveType.Cube);
        enemy.transform.position = position;
        SetColor(enemy, Color.red);
        return enemy;
    }

    public static void SetColor(GameObject go, Color color)
    {
        Renderer renderer = go.GetComponent<Renderer>();
        renderer.sharedMaterial = new Material(renderer.sharedMaterial) { color = color };
    }
}
