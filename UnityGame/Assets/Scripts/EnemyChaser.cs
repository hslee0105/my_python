using UnityEngine;
using UnityEngine.AI;

// NavMesh-based pursuit: periodically re-paths toward the player.
// Requires a baked NavMesh in the scene (Tools > Roll & Collect >
// Build Scene bakes one automatically via the AI Navigation package).
[RequireComponent(typeof(NavMeshAgent))]
public class EnemyChaser : MonoBehaviour
{
    [SerializeField] private float repathInterval = 0.2f;

    private NavMeshAgent _agent;
    private Transform _player;
    private float _repathTimer;

    private void Awake()
    {
        _agent = GetComponent<NavMeshAgent>();
        GameObject playerObj = GameObject.FindGameObjectWithTag("Player");
        if (playerObj != null) _player = playerObj.transform;
    }

    private void Update()
    {
        if (_player == null) return;

        _repathTimer -= Time.deltaTime;
        if (_repathTimer <= 0f)
        {
            _agent.SetDestination(_player.position);
            _repathTimer = repathInterval;
        }
    }

    private void OnCollisionEnter(Collision collision)
    {
        if (collision.gameObject.CompareTag("Player") && GameManager.Instance != null)
        {
            GameManager.Instance.LoseGame();
        }
    }
}
