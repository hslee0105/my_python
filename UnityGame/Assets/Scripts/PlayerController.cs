using UnityEngine;

// Physics-based player movement for a Rigidbody sphere.
// Attach to the Player GameObject along with a Rigidbody + SphereCollider.
[RequireComponent(typeof(Rigidbody))]
public class PlayerController : MonoBehaviour
{
    [Header("Movement")]
    [SerializeField] private float moveSpeed = 8f;
    [SerializeField] private float jumpForce = 6f;

    [Header("Ground Check")]
    [SerializeField] private float groundCheckDistance = 0.6f;
    [SerializeField] private LayerMask groundMask = ~0;

    [Header("Dash")]
    [SerializeField] private float dashSpeed = 20f;
    [SerializeField] private float dashDuration = 0.15f;
    [SerializeField] private float dashCooldown = 1f;

    [Header("Facing")]
    [SerializeField] private float turnSpeed = 720f;
    [Tooltip("Extra yaw (degrees) applied on top of the movement-facing rotation. " +
        "Imported character models don't always face +Z by default — if the " +
        "character appears to walk sideways or backwards, adjust this until it faces forward.")]
    [SerializeField] private float modelForwardOffset = 0f;

    [Header("Animation (optional)")]
    [Tooltip("If the character model has an Animator with a float parameter " +
        "(e.g. \"Speed\") driving an Idle/Walk/Run blend, set its name here. " +
        "Leave empty if there's no Animator (e.g. the default primitive mascot).")]
    [SerializeField] private string speedParameterName = "Speed";

    private Rigidbody _rb;
    private Animator _animator;
    private Vector3 _moveInput;
    private bool _isGrounded;

    private Vector3 _dashDirection;
    private float _dashTimeRemaining;
    private float _dashCooldownTimer;

    private void Awake()
    {
        _rb = GetComponent<Rigidbody>();
        _rb.interpolation = RigidbodyInterpolation.Interpolate;

        _animator = GetComponentInChildren<Animator>();
        if (_animator != null && !HasFloatParameter(_animator, speedParameterName))
        {
            // Avoid spamming "parameter does not exist" warnings every frame
            // when an imported character's Animator uses different names.
            _animator = null;
        }
    }

    private static bool HasFloatParameter(Animator animator, string paramName)
    {
        if (string.IsNullOrEmpty(paramName)) return false;

        foreach (AnimatorControllerParameter param in animator.parameters)
        {
            if (param.type == AnimatorControllerParameterType.Float && param.name == paramName) return true;
        }
        return false;
    }

    private void Update()
    {
        float h = Input.GetAxisRaw("Horizontal"); // A/D, Left/Right
        float v = Input.GetAxisRaw("Vertical");   // W/S, Up/Down
        _moveInput = new Vector3(h, 0f, v).normalized;

        _isGrounded = Physics.Raycast(transform.position, Vector3.down, groundCheckDistance, groundMask);

        if (_isGrounded && Input.GetKeyDown(KeyCode.Space))
        {
            _rb.AddForce(Vector3.up * jumpForce, ForceMode.Impulse);
        }

        if (_dashCooldownTimer > 0f) _dashCooldownTimer -= Time.deltaTime;

        if (Input.GetKeyDown(KeyCode.LeftShift) && _dashCooldownTimer <= 0f && _moveInput.sqrMagnitude > 0.01f)
        {
            _dashDirection = _moveInput;
            _dashTimeRemaining = dashDuration;
            _dashCooldownTimer = dashCooldown;
        }
    }

    private void FixedUpdate()
    {
        Vector3 velocity = _rb.linearVelocity;

        if (_dashTimeRemaining > 0f)
        {
            _dashTimeRemaining -= Time.fixedDeltaTime;
            Vector3 dashVelocity = _dashDirection * dashSpeed;
            velocity.x = dashVelocity.x;
            velocity.z = dashVelocity.z;
        }
        else
        {
            Vector3 targetVelocity = _moveInput * moveSpeed;
            velocity.x = targetVelocity.x;
            velocity.z = targetVelocity.z;
        }

        _rb.linearVelocity = velocity;

        Vector3 facingDirection = _dashTimeRemaining > 0f ? _dashDirection : _moveInput;
        if (facingDirection.sqrMagnitude > 0.01f)
        {
            Quaternion targetRotation = Quaternion.LookRotation(facingDirection, Vector3.up) * Quaternion.Euler(0f, modelForwardOffset, 0f);
            _rb.MoveRotation(Quaternion.RotateTowards(_rb.rotation, targetRotation, turnSpeed * Time.fixedDeltaTime));
        }

        if (_animator != null && !string.IsNullOrEmpty(speedParameterName))
        {
            float speed = new Vector2(velocity.x, velocity.z).magnitude;
            _animator.SetFloat(speedParameterName, speed);
        }
    }
}
