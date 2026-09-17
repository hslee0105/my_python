using UnityEngine;

// Simple obstacle that patrols between two points along the X axis.
// Attach to an enemy/obstacle GameObject with a (non-trigger) Collider.
public class EnemyPatrol : MonoBehaviour
{
    [SerializeField] private float patrolDistance = 4f;
    [SerializeField] private float patrolSpeed = 2f;

    private Vector3 _startPosition;

    private void Start()
    {
        _startPosition = transform.position;
    }

    private void Update()
    {
        float offset = Mathf.PingPong(Time.time * patrolSpeed, patrolDistance * 2f) - patrolDistance;
        transform.position = _startPosition + new Vector3(offset, 0f, 0f);
    }

    private void OnCollisionEnter(Collision collision)
    {
        if (collision.gameObject.CompareTag("Player"))
        {
            GameManager.Instance.RespawnPlayer(collision.gameObject);
        }
    }
}
