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

    private Rigidbody _rb;
    private Vector3 _moveInput;
    private bool _isGrounded;

    private void Awake()
    {
        _rb = GetComponent<Rigidbody>();
        _rb.interpolation = RigidbodyInterpolation.Interpolate;
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
    }

    private void FixedUpdate()
    {
        Vector3 targetVelocity = _moveInput * moveSpeed;
        Vector3 velocity = _rb.velocity;
        velocity.x = targetVelocity.x;
        velocity.z = targetVelocity.z;
        _rb.velocity = velocity;
    }
}
