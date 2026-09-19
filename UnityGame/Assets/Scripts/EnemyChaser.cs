using UnityEngine;
using UnityEngine.AI;

// NavMesh-based pursuit: periodically re-paths toward the player.
// Requires a baked NavMesh in the scene (Tools > Roll & Collect >
// Build Scene bakes one automatically via the AI Navigation package).
[RequireComponent(typeof(NavMeshAgent))]
public class EnemyChaser : MonoBehaviour
{
    [SerializeField] private float repathInterval = 0.2f;

    [Tooltip("If the enemy model has an Animator with a float parameter " +
        "(e.g. \"Speed\") driving an Idle/Walk/Run blend, set its name here. " +
        "Leave empty if there's no Animator (e.g. the default red Cube).")]
    [SerializeField] private string speedParameterName = "Speed";

    private NavMeshAgent _agent;
    private Animator _animator;
    private Transform _player;
    private float _repathTimer;

    private void Awake()
    {
        _agent = GetComponent<NavMeshAgent>();
        GameObject playerObj = GameObject.FindGameObjectWithTag("Player");
        if (playerObj != null) _player = playerObj.transform;

        _animator = GetComponentInChildren<Animator>();
        if (!AnimatorUtility.HasFloatParameter(_animator, speedParameterName))
        {
            _animator = null;
        }
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

        if (_animator != null)
        {
            _animator.SetFloat(speedParameterName, _agent.velocity.magnitude);
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
