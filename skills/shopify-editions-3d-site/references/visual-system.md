# Visual System

## Art Direction

Aim for editorial commerce, not a generic SaaS landing page.

Observed cues from the source project:

- Black stage background and warm off-white editorial surfaces.
- Serif/script/display moments mixed with a hard grotesque UI font.
- Roman numeral or numbered section navigation.
- Precision linework inspired by technical drawings.
- Theme-aware nav/sidebar switching between dark and light sections.
- Tight, dense product-update content after an immersive opening.

## Typography

Use a three-layer type system:

- Display serif or custom display face for release identity and major chapter titles.
- Grotesque sans for navigation, buttons, cards, and product copy.
- Optional script/accent face for one or two brand moments only.

From the analyzed project:

- `NeueMontreal` equivalent for bold interface display.
- `HWCigars` equivalent for editorial serif/numbering.
- `ImperialScript` equivalent for occasional script accents.

Do not use negative letter spacing globally. If an existing brand display face requires tight tracking, apply it only to large titles and verify mobile fit.

## Color

Use a restrained but not monochrome palette:

- Stage: `#000000`
- Warm paper: `#f7f7ee`
- Ink: `#292919`
- Muted panel: `#dcdcd0` / `#e2e2d9`
- Focus blue: `#739bff`
- Product accent: one sharp color per release chapter

Avoid a page dominated by only purple, beige, dark blue, or brown/orange. Scene lighting can use saturated accent colors, but UI surfaces should remain legible.

## Navigation UI

Desktop:

- Header height about 50-60px.
- Logo/release mark left, nav/search center, CTA right.
- Buttons use compact rounded rectangles, about 4px radius unless the site design system says otherwise.
- Icon buttons should use real icons with accessible labels.

Mobile:

- Full-screen overlay.
- Large stacked section links.
- Secondary links and CTA at bottom.
- Ensure overlay text does not collide with browser safe areas.

Sidebar:

- Ordered section labels.
- Use subtle dotted/technical connecting lines on hover/active.
- Active item must be visible by color and position, not only animation.

## Hero

The hero must immediately communicate:

- release/product name
- category or launch idea
- one-sentence promise
- primary CTA or exploration path
- visible cue that more sections follow

Use a full-bleed scene or rich media background, not a split card layout. Do not hide the actual product/release behind abstract decoration.

## Section Design

Each chapter should pair:

- one strong title
- concise explainer
- update cards or feature rows
- optional media/product demo
- optional scene state

Cards should be stable and scan-friendly:

- max 8px radius
- consistent min height
- category label
- title
- summary
- tags or CTA

## Motion

Use motion to orient, not to decorate:

- nav items can enter with short staggered translate/opacity.
- section transitions can crossfade or wipe between scene render targets.
- linework can draw in once, then settle.
- hover states should be quick and reversible.

Always implement `prefers-reduced-motion`. Reduced mode should remove orbiting, large translate, scroll-scrubbed animation, and shader-heavy transitions while keeping content hierarchy.

## Accessibility

- Skip link to main content.
- Keyboard-operable search, nav menus, and cards.
- Escape closes overlays.
- Visible focus ring.
- Sufficient contrast in both dark and light nav themes.
- Do not make the WebGL canvas the only place where information exists.
