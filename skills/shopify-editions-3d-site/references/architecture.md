# Architecture

## Source Pattern Observed

The analyzed project is a static mirror of a Shopify Editions page:

- `index.html` is a full-screen iframe shell.
- `editions/winter2026/index.html` contains server-rendered Remix/Oxygen HTML plus hydrated JS bundles.
- Main CSS is Tailwind v4 output with custom tokens and component classes.
- The app uses global navigation, mobile overlay nav, predictive search, section sidebar navigation, dense content sections, and a sticky background renderer.
- 3D sections are loaded from scene components such as `HeroScene` and `SidekickScene`.

Use this pattern as architectural reference, not as code to copy.

## Page Shell

Build a normal app shell unless the user specifically needs iframe embedding:

- `<header>` fixed or sticky with release identity, edition picker, search, and primary CTA.
- `<aside>` section navigation on desktop; collapsible or hidden on mobile.
- `<main>` containing a hero and release sections.
- Sticky full-viewport scene layer behind or beside content.
- Static fallback media layer beneath the canvas.

Keep content readable without JavaScript. The hydrated experience can enhance search, transitions, and WebGL.

## Content Model

Use data-first content. A practical schema:

```ts
type ReleaseSection = {
  id: string;
  navLabel: string;
  eyebrow?: string;
  title: string;
  summary: string;
  theme: "dark" | "light";
  scene?: SceneConfig;
  updates: ProductUpdate[];
};

type ProductUpdate = {
  id: string;
  title: string;
  category: string;
  summary: string;
  tags: string[];
  media?: MediaAsset[];
  cta?: { label: string; href: string };
};
```

Recommended section taxonomy for a commerce release:

- AI assistant / automation
- Online store
- Retail / POS
- Marketing
- Checkout
- Operations / analytics
- Developer platform

## Navigation

Required navigation behavior:

- Brand/release mark links back to top.
- Desktop nav exposes edition/release switcher, search, external product link, and primary CTA.
- Mobile nav uses a full-height overlay with large section labels.
- Section sidebar uses ordered labels, active-state highlighting, and theme-aware contrast.
- Search should support keyboard navigation, escape to close, clear/reset, and empty states.

If search backends are unavailable, implement local search over the update schema.

## Layout

Use full-width bands and constrained inner content. Avoid nested card structures.

Recommended layout rhythm:

- Hero: full viewport minus hint of next section.
- Scene canvas: sticky top, full viewport, pointer events only where needed.
- Sections: min-height 100svh for major chapters; denser sections can be 60-80svh.
- Update grid: responsive 1/2/3 columns with stable card dimensions.
- Editorial interludes: large display text, simple body copy, few controls.

## State

Keep state explicit:

- active section index
- navigation theme
- sidebar theme
- search open state and query
- render quality: `high | medium | low`
- reduced motion
- WebGL availability
- scene loading state

Do not let visual state live only inside animation callbacks.

## Failure Model

The page must degrade in layers:

1. Full WebGL scene.
2. Static fallback image/video per section.
3. Plain content layout with text and cards.

Any asset-loading error should affect only its scene, not the whole page.
