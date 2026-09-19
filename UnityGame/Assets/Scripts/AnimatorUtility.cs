using UnityEngine;

// Shared helper for scripts that optionally drive an imported character's
// Animator: lets them check once (e.g. in Awake) whether a given float
// parameter actually exists, instead of calling SetFloat blindly and
// spamming "parameter does not exist" warnings every frame when an
// asset's Animator Controller uses different names.
public static class AnimatorUtility
{
    public static bool HasFloatParameter(Animator animator, string paramName)
    {
        if (animator == null || string.IsNullOrEmpty(paramName)) return false;

        foreach (AnimatorControllerParameter param in animator.parameters)
        {
            if (param.type == AnimatorControllerParameterType.Float && param.name == paramName) return true;
        }
        return false;
    }
}
