using UnityEngine;

// Generates short sound effects at runtime so the project ships with
// zero external audio assets.
public static class ProceduralAudio
{
    private static AudioClip _coinPickupClip;

    public static AudioClip CoinPickupClip => _coinPickupClip != null
        ? _coinPickupClip
        : _coinPickupClip = CreateCoinPickupClip();

    // Plays the pickup clip with pitch rising per combo step, so chaining
    // pickups quickly sounds increasingly satisfying. Uses a manually
    // created AudioSource (rather than PlayClipAtPoint) because pitch
    // needs to be set before playback starts.
    public static void PlayPickupSound(Vector3 position, int combo)
    {
        GameObject audioObj = new GameObject("PickupSound");
        audioObj.transform.position = position;

        AudioSource source = audioObj.AddComponent<AudioSource>();
        source.clip = CoinPickupClip;
        source.pitch = Mathf.Min(1f + 0.1f * (combo - 1), 2f);
        source.spatialBlend = 1f;
        source.Play();

        Object.Destroy(audioObj, CoinPickupClip.length / source.pitch);
    }

    private static AudioClip CreateCoinPickupClip()
    {
        const int sampleRate = 44100;
        const float duration = 0.15f;
        const float startFrequency = 880f;
        const float endFrequency = 1760f;

        int sampleCount = Mathf.CeilToInt(sampleRate * duration);
        float[] samples = new float[sampleCount];

        for (int i = 0; i < sampleCount; i++)
        {
            float t = i / (float)sampleRate;
            float progress = t / duration;
            float frequency = Mathf.Lerp(startFrequency, endFrequency, progress);
            float envelope = Mathf.Pow(1f - progress, 2f);
            samples[i] = Mathf.Sin(2f * Mathf.PI * frequency * t) * envelope;
        }

        AudioClip clip = AudioClip.Create("CoinPickup", sampleCount, 1, sampleRate, false);
        clip.SetData(samples, 0);
        return clip;
    }
}
