---
name: shopify-editions-3d-site
description: Use when asked to build a Shopify Editions-style product launch site, immersive 3D commerce microsite, scroll-driven WebGL announcement page, or premium release page with 3D hero scenes, section navigation, product update cards, responsive fallbacks, and high-performance asset loading.
---

# Shopify Editions 3D Site

## Overview

Use this skill to create a polished product-launch microsite in the same class as Shopify Editions Winter '26: full-viewport editorial storytelling, sticky WebGL scenes, dense update content, precise navigation, and robust fallbacks.

Do not clone Shopify branding or copy protected content. Recreate the system: scene architecture, editorial hierarchy, asset pipeline, motion discipline, and performance constraints.

## Start Here

1. Define the release concept, sections, and product/update taxonomy.
2. Read `references/architecture.md` for page structure and data flow.
3. Read `references/visual-system.md` for typography, navigation, layout, and motion language.
4. Read `references/three-scene-system.md` before implementing any 3D, WebGL, shader, GLB/GLTF, KTX2, DRACO, camera, lighting, particle, or post-processing work.
5. Read `references/asset-pipeline.md` when preparing models, textures, video, images, fonts, or fallbacks.
6. Use `assets/site-blueprint.template.md` to draft the concrete site plan before coding.
7. Use `references/implementation-checklist.md` for build and verification.

## Required Deliverables

- A working website, not a static mockup or landing-page description.
- A first viewport with the product/release identity, immersive 3D or rich media, and a visible path into the next section.
- Sticky global navigation, mobile navigation, section navigation, and CTA treatment.
- Product/update sections that can be scanned, searched, filtered, or grouped.
- Low-performance and reduced-motion fallbacks.
- Verified desktop and mobile rendering, including canvas nonblank checks when WebGL is used.

## Preferred Stack

Use the existing project stack when one exists. For a new build, prefer:

- React + Vite or Remix-style routing.
- Tailwind or a tokenized CSS layer.
- Three.js with React Three Fiber for interactive scenes.
- GLTFLoader + DRACOLoader + KTX2Loader for production 3D assets.
- A lightweight scene configuration object per section.

Avoid hand-rolling core 3D asset loading or compression behavior when Three.js loaders already solve it.

## Build Pattern

Treat the site as two coordinated systems:

- **Content system:** release metadata, section taxonomy, navigation, search, update cards, CTAs, SEO.
- **Scene system:** sticky canvas, per-section scene components, compressed assets, camera/light presets, render quality, transitions, fallbacks.

The content must remain usable if the scene system fails.

## Quality Bar

- No blank WebGL canvases.
- No text overlap on mobile or desktop.
- No motion-only navigation.
- No one-note palette; combine dark stage surfaces, warm editorial neutrals, sharp accent colors, and product-specific colors.
- No decorative cards inside cards.
- No marketing-only hero. The first screen must be the actual product-launch experience.

## References

- `references/architecture.md`: page architecture and interaction model.
- `references/visual-system.md`: art direction and responsive UI rules.
- `references/three-scene-system.md`: 3D modeling, asset loading, scene, shader, and performance rules.
- `references/asset-pipeline.md`: asset preparation and budgets.
- `references/implementation-checklist.md`: build and verification checklist.
