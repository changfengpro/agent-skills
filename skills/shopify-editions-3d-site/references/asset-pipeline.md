# Asset Pipeline

## Inventory

Create an asset manifest before coding:

```ts
type AssetManifestItem = {
  id: string;
  type: "model" | "texture" | "image" | "video" | "font" | "icon" | "json";
  src: string;
  fallback?: string;
  budgetKb?: number;
  owner?: string;
};
```

Keep remote URLs replaceable. For production, prefer local/public assets controlled by the project unless the user explicitly wants CDN-hosted assets.

## 3D Models

Preferred format:

- `.glb` for complete model packages.
- Draco compression for dense geometry.
- KTX2 textures where feasible.
- Named animation clips when motion is needed.

Model export checklist:

- Units and scale are correct.
- Pivot/origin supports intended camera motion.
- Meshes and important empties are named.
- Materials are PBR-friendly.
- Hidden helper geometry is removed.
- Animations are trimmed to useful ranges.

## Textures

Use:

- KTX2/Basis for GPU texture delivery.
- JPG/WebP/AVIF for fallback raster images.
- PNG only for alpha or pixel-accurate UI assets.
- SVG for simple icons and linework.

Avoid huge uncompressed textures. A beautiful scene with late-loading 8K textures is a failed site.

## Environment Maps

Use PMREM-ready environment textures for consistent lighting.

Rules:

- Prefer 1K environment maps for web.
- Keep intensity adjustable per scene.
- Use a neutral studio environment unless the scene needs a specific place.
- Do not use the environment as the only background if fallback imagery matters.

## Images And Video

Hero media:

- Provide desktop and mobile crops.
- Keep subject inspectable.
- Use poster images for videos.
- Lazy-load below-the-fold media.

Social/meta:

- Provide Open Graph image.
- Provide favicon and touch icon.

## Fonts

Bundle only required weights/styles.

Recommended pattern:

- display serif/custom: 1 weight
- sans UI: 1-2 weights
- optional script/accent: 1 weight

Use `font-display: swap`. Confirm text remains acceptable before custom fonts load.

## Fallbacks

Each scene should have:

- static fallback image
- optional lightweight video fallback
- textual content outside the canvas

Fallbacks must be visually aligned with the full scene, not generic placeholders.
