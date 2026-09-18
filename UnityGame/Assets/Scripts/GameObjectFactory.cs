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

    public static GameObject CreateEnemy(Vector3 position, float speed)
    {
        GameObject enemy = GameObject.CreatePrimitive(PrimitiveType.Cube);
        enemy.name = "Enemy";
        enemy.transform.position = position;
        SetColor(enemy, Color.red);

        NavMeshAgent agent = enemy.AddComponent<NavMeshAgent>();
        agent.baseOffset = 0.5f;
        agent.speed = speed;
        agent.radius = 0.4f;

        enemy.AddComponent<EnemyChaser>();
        return enemy;
    }

    public static void SetColor(GameObject go, Color color)
    {
        Renderer renderer = go.GetComponent<Renderer>();
        renderer.sharedMaterial = new Material(renderer.sharedMaterial) { color = color };
    }
}
