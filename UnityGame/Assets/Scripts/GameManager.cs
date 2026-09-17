using UnityEngine;
using UnityEngine.UI;

// Central game state: score tracking, win condition, player respawn.
// Attach to an empty "GameManager" GameObject (singleton).
public class GameManager : MonoBehaviour
{
    public static GameManager Instance { get; private set; }

    [Header("UI References")]
    [SerializeField] private Text scoreText;
    [SerializeField] private Text messageText;

    [Header("Player")]
    [SerializeField] private Vector3 playerSpawnPoint = new Vector3(0f, 1f, 0f);

    private int _score;
    private int _totalCollectibles;

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
    }

    private void Start()
    {
        _totalCollectibles = FindObjectsOfType<CollectibleItem>().Length;
        UpdateScoreUI();
        if (messageText != null) messageText.text = string.Empty;
    }

    public void AddScore(int amount)
    {
        _score += amount;
        UpdateScoreUI();

        if (_score >= _totalCollectibles)
        {
            ShowWinMessage();
        }
    }

    public void RespawnPlayer(GameObject player)
    {
        Rigidbody rb = player.GetComponent<Rigidbody>();
        if (rb != null) rb.velocity = Vector3.zero;
        player.transform.position = playerSpawnPoint;
    }

    private void UpdateScoreUI()
    {
        if (scoreText != null)
        {
            scoreText.text = $"Score: {_score} / {_totalCollectibles}";
        }
    }

    private void ShowWinMessage()
    {
        if (messageText != null)
        {
            messageText.text = "You Win! All items collected.";
        }
    }
}
