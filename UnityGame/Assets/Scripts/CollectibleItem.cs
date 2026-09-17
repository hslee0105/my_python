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

        GameManager.Instance.AddScore(scoreValue);
        Destroy(gameObject);
    }
}
