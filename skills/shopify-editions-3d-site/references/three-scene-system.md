# Three Scene System

## Source Pattern Observed

The analyzed project uses:

- Three.js and React Three Fiber.
- `GLTFLoader` with `DRACOLoader`.
- `KTX2Loader` / Basis transcoding.
- PMREM environment texture, e.g. `.pmrem.ktx2`.
- Per-section scene components such as `HeroScene` and `SidekickScene`.
- Shared camera, light, particle, butterfly, and effects components.
- Sticky canvas renderer with render-target crossfades between active sections.
- GPU/FPS detection and quality downgrade.
- Static fallback images when WebGL is unavailable.

## Scene Contract

Create scene components that accept data:

```ts
type SceneConfig = {
  id: string;
  component: "hero" | "product" | "abstract" | "sidekick";
  camera?: CameraPreset;
  lights?: LightPreset[];
  assets?: SceneAsset[];
  particles?: ParticlePreset;
  environment?: string;
  fallbackImage: string;
};
```

Each scene must:

- render without needing page content state except section index/config
- expose a camera
- dispose geometry, materials, and textures on unmount
- handle missing assets without throwing outside the scene boundary
- be visually meaningful within 1-2 seconds

## Asset Loading

Use loaders, not ad hoc fetch parsing:

- `GLTFLoader` for `.glb` and `.gltf`
- `DRACOLoader` for compressed geometry
- `KTX2Loader.detectSupport(renderer)` for compressed textures
- `RGBELoader` or KTX2 PMREM for environment maps

Decoder paths:

- Draco: point to a known local/public decoder path or CDN only when network use is allowed.
- Basis/KTX2: bundle transcoder assets or use a stable CDN path.

Cache loaders and textures. Do not create a new loader for every render frame.

## Modeling Guidance

For product-launch scenes:

- Use a single hero model or a small set of grouped assets.
- Keep real product surfaces inspectable; avoid over-dark, blurred, or purely atmospheric presentation.
- Use origin-centered models with real-world scale.
- Name important nodes in the model for camera targets and animation hooks.
- Bake static details into textures; keep geometry for silhouette and interaction.

Recommended budgets:

- Hero GLB: 1-5 MB compressed when possible.
- Supporting GLB: under 2 MB each.
- Texture max: 1024-2048px for most assets.
- KTX2/Basis for GPU textures.
- Draco for dense static meshes.
- Avoid hundreds of separate draw calls.

## Camera

Use named presets:

- hero front three-quarter
- product closeup
- orbit debug
- section transition target

Implement pointer gaze subtly:

- interpolate mouse/pointer influence
- clamp pan and tilt
- disable or reduce on touch and reduced motion
- never make text hard to read because of camera drift

## Lighting

Use environment lighting as the base. Add point/area lights only for emphasis.

Common setup:

- PMREM environment
- key light
- rim/accent light
- optional low-intensity fill

Avoid high-intensity colored lights that hide material detail. If using red/blue accent lights, keep them controllable per scene.

## Particles And Procedural Elements

Use procedural elements to support the launch identity:

- particles for energy fields, dust, sparks, data points
- instanced meshes for repeated small objects
- shader planes for texture/linework effects

Keep uniforms explicit and easy to tune:

- time
- opacity
- color
- size
- speed
- turbulence
- count

Stop or simplify particles in reduced-motion and low-quality modes.

## Post Processing

A robust renderer can use:

- render targets for current/next scene
- crossfade shader
- overlay shader
- optional bloom
- optional inverted/edge/sobel effect

But post processing must never be required for legibility. Disable bloom or heavy effects on low quality.

## Quality Management

Detect:

- WebGL support
- device pixel ratio
- viewport size
- reduced motion
- measured FPS after initial load

Quality rules:

- high: 60fps target, DPR capped at 2, full post-processing
- medium: DPR capped by viewport budget, moderate particles
- low: 30fps target, no bloom, fewer particles, fallback media acceptable

If FPS stays below target, downgrade once and keep the page stable.

## Verification

Before completion:

- Verify canvas has nonblack/nontransparent pixels after load.
- Verify the model or fallback is visible in desktop and mobile screenshots.
- Resize the viewport and ensure camera framing still works.
- Test missing asset behavior.
- Test reduced-motion behavior.
- Confirm all geometries/materials/textures are disposed on scene unmount if scenes are mounted dynamically.
