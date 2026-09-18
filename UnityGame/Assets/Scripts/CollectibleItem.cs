using UnityEngine;

// Attach to each collectible coin. Requires a trigger Collider.
// Tag the Player GameObject as "Player" for OnTriggerEnter to fire.
[RequireComponent(typeof(Collider))]
public class CollectibleItem : MonoBehaviour
{
    [SerializeField] private float rotationSpeed = 90f;
    [SerializeField] private int scoreValue = 1;

    private void Reset()
    {
        GetComponent<Collider>().isTrigger = true;
    }

    private void Update()
    {
        transform.Rotate(Vector3.up, rotationSpeed * Time.deltaTime, Space.World);
    }

    private void OnTriggerEnter(Collider other)
    {
        if (!other.CompareTag("Player")) return;

        if (GameManager.Instance == null)
        {
            Debug.LogError("CollectibleItem: no GameManager in the scene (score will not be tracked). " +
                "Run Tools > Roll & Collect > Build Scene, or add a GameManager object manually.", this);
        }
        else
        {
            GameManager.Instance.AddScore(scoreValue);
        }

        AudioSource.PlayClipAtPoint(ProceduralAudio.CoinPickupClip, transform.position);
        ProceduralEffects.SpawnPickupBurst(transform.position, Color.yellow);

        Destroy(gameObject);
    }
}
