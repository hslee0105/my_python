using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

// Central game state: score tracking, win condition, time limit, player respawn.
// Attach to an empty "GameManager" GameObject (singleton).
public class GameManager : MonoBehaviour
{
    public static GameManager Instance { get; private set; }

    private const string BestTimeKey = "RollCollect_BestTime";

    [Header("UI References")]
    [SerializeField] private Text scoreText;
    [SerializeField] private Text messageText;
    [SerializeField] private Text timerText;
    [SerializeField] private Text bestTimeText;
    [SerializeField] private GameObject restartButton;

    [Header("Player")]
    [SerializeField] private Vector3 playerSpawnPoint = new Vector3(0f, 1f, 0f);

    [Header("Time Limit")]
    [SerializeField] private bool useTimeLimit = true;
    [SerializeField] private float timeLimitSeconds = 60f;

    private int _score;
    private int _totalCollectibles;
    private float _timeRemaining;
    private float _elapsedTime;
    private bool _isGameOver;

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
        _timeRemaining = timeLimitSeconds;
        Time.timeScale = 1f;

        UpdateScoreUI();
        UpdateTimerUI();
        UpdateBestTimeUI();
        if (messageText != null) messageText.text = string.Empty;
        if (restartButton != null) restartButton.SetActive(false);
    }

    private void Update()
    {
        if (_isGameOver) return;

        _elapsedTime += Time.deltaTime;

        if (!useTimeLimit) return;

        _timeRemaining -= Time.deltaTime;
        if (_timeRemaining <= 0f)
        {
            _timeRemaining = 0f;
            UpdateTimerUI();
            ShowTimeUpMessage();
            return;
        }

        UpdateTimerUI();
    }

    public void AddScore(int amount)
    {
        if (_isGameOver) return;

        _score += amount;
        UpdateScoreUI();

        if (_score >= _totalCollectibles)
        {
            ShowWinMessage();
        }
    }

    public void RespawnPlayer(GameObject player)
    {
        if (_isGameOver) return;

        Rigidbody rb = player.GetComponent<Rigidbody>();
        if (rb != null) rb.linearVelocity = Vector3.zero;
        player.transform.position = playerSpawnPoint;
    }

    private void UpdateScoreUI()
    {
        if (scoreText != null)
        {
            scoreText.text = $"Score: {_score} / {_totalCollectibles}";
        }
    }

    private void UpdateTimerUI()
    {
        if (timerText == null) return;

        int minutes = Mathf.FloorToInt(_timeRemaining / 60f);
        int seconds = Mathf.FloorToInt(_timeRemaining % 60f);
        timerText.text = $"Time: {minutes:00}:{seconds:00}";
    }

    private void UpdateBestTimeUI()
    {
        if (bestTimeText == null) return;

        bestTimeText.text = PlayerPrefs.HasKey(BestTimeKey)
            ? $"Best: {PlayerPrefs.GetFloat(BestTimeKey):0.0}s"
            : "Best: --";
    }

    public void RestartGame()
    {
        Time.timeScale = 1f;
        SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex);
    }

    private void ShowWinMessage()
    {
        _isGameOver = true;

        bool isNewBest = !PlayerPrefs.HasKey(BestTimeKey) || _elapsedTime < PlayerPrefs.GetFloat(BestTimeKey);
        if (isNewBest)
        {
            PlayerPrefs.SetFloat(BestTimeKey, _elapsedTime);
            PlayerPrefs.Save();
            UpdateBestTimeUI();
        }

        if (messageText != null)
        {
            messageText.text = isNewBest
                ? $"You Win! New Best Time: {_elapsedTime:0.0}s!"
                : $"You Win! Time: {_elapsedTime:0.0}s";
        }
        if (restartButton != null) restartButton.SetActive(true);
        Time.timeScale = 0f;
    }

    private void ShowTimeUpMessage()
    {
        _isGameOver = true;
        if (messageText != null)
        {
            messageText.text = $"Time's Up! Score: {_score} / {_totalCollectibles}";
        }
        if (restartButton != null) restartButton.SetActive(true);
        Time.timeScale = 0f;
    }
}
