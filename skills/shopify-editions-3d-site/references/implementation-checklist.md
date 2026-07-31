# Implementation Checklist

## Planning

- Define release name, theme, audience, and primary CTA.
- Draft sections and product/update taxonomy.
- Draft the scene list and fallback media list.
- Fill `assets/site-blueprint.template.md`.

## Build

- Create app shell: header, mobile nav, aside nav, main sections.
- Create content data schema.
- Render hero and sections from data.
- Add local search/filter over update data.
- Build sticky scene layer with fallbacks.
- Add per-section scene config.
- Add GLTF/DRACO/KTX2 loading if 3D assets exist.
- Add reduced-motion and low-quality modes.
- Add SEO/meta/social image tags.

## UI Verification

- Desktop: 1440x900 and 1920x1080.
- Mobile: 390x844 and 430x932.
- Check hero first viewport includes release identity and next-section hint.
- Check header, mobile menu, search, CTA, and sidebar.
- Check no text overlaps or clipped button labels.
- Check light and dark nav themes.
- Check keyboard navigation and focus rings.

## 3D Verification

- Canvas renders nonblank.
- Model/fallback is visible and framed.
- DPR cap works.
- Reduced motion disables heavy movement.
- Low quality disables or reduces particles/postprocessing.
- Asset-loading errors do not crash the page.

## Performance

- Use lazy loading below the fold.
- Cap DPR by viewport/quality.
- Avoid unnecessary rerenders of scene objects.
- Dispose Three.js resources on unmount.
- Verify no large uncompressed textures ship accidentally.

## Completion

- Run lint/build/tests available in the project.
- Start a local dev server if the app requires it.
- Capture screenshots or otherwise verify desktop/mobile.
- Report exact files changed and verification performed.
