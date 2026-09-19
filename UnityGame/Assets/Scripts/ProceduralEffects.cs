using UnityEngine;

// Spawns simple built-in ParticleSystem bursts without external assets.
public static class ProceduralEffects
{
    private static Material _particleMaterial;

    public static void SpawnPickupBurst(Vector3 position, Color color)
    {
        GameObject burstObj = new GameObject("PickupBurst");
        burstObj.transform.position = position;

        ParticleSystem system = burstObj.AddComponent<ParticleSystem>();

        ParticleSystem.MainModule main = system.main;
        main.duration = 0.3f;
        main.loop = false;
        main.startLifetime = 0.4f;
        main.startSpeed = 3f;
        main.startSize = 0.15f;
        main.startColor = color;
        main.simulationSpace = ParticleSystemSimulationSpace.World;
        main.stopAction = ParticleSystemStopAction.Destroy;

        ParticleSystem.EmissionModule emission = system.emission;
        emission.rateOverTime = 0f;
        emission.SetBursts(new[] { new ParticleSystem.Burst(0f, 12) });

        ParticleSystem.ShapeModule shape = system.shape;
        shape.shapeType = ParticleSystemShapeType.Sphere;
        shape.radius = 0.1f;

        system.GetComponent<ParticleSystemRenderer>().material = GetParticleMaterial();

        system.Play();
    }

    private static Material GetParticleMaterial()
    {
        if (_particleMaterial == null)
        {
            _particleMaterial = new Material(Shader.Find("Sprites/Default"));
        }
        return _particleMaterial;
    }
}
