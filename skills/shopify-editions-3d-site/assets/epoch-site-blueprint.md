# Site Blueprint — Epoch Commerce Platform

## Release

- Name: Epoch
- Tagline: The future of commerce, orchestrated
- Audience: Developers, merchants, and operations teams building the next generation of commerce
- Primary CTA: Start building
- Secondary CTA: Read the changelog

## Visual Direction

- Stage/background: `#0a0a0a` near-black
- Paper/light surface: `#f5f5ee` warm off-white
- Ink: `#1a1a14`
- Muted panel: `#dcdcd0`
- Focus accent: `#00e5c7` electric teal
- Product accents per chapter: teal, coral, amber, violet, steel
- Typefaces: Display serif for release identity, grotesque sans for UI
- Motion personality: Smooth, restrained — camera drifts, particles flow, transitions crossfade

## Sections

| ID | Nav label | Title | Theme | Scene | Updates |
|---|---|---|---|---|---|
| hero | 00 | Epoch | dark | hero | — |
| ai | 01 | AI & Automation | dark | abstract | 4 updates |
| storefront | 02 | Online Store | light | product | 4 updates |
| checkout | 03 | Checkout | dark | abstract | 3 updates |
| operations | 04 | Operations | light | product | 4 updates |
| platform | 05 | Developer Platform | dark | abstract | 3 updates |

## Scene Assets

| ID | Type | Source | Fallback | Budget |
|---|---|---|---|---|
| hero | procedural | Three.js torus knot + particles | CSS gradient | 0 KB |
| ai | procedural | Floating icosahedron lattice | CSS gradient | 0 KB |
| storefront | procedural | Rotating product showcase | CSS gradient | 0 KB |
| checkout | procedural | Shader plane flow | CSS gradient | 0 KB |
| operations | procedural | Instanced data points | CSS gradient | 0 KB |
| platform | procedural | Wireframe geometry | CSS gradient | 0 KB |

## Update Categories

- AI: Intelligent automation, personalization, forecasting
- Online: Storefront themes, merchandising, content
- Checkout: Payments, subscriptions, fraud prevention
- Operations: Analytics, inventory, fulfillment
- Platform: APIs, SDKs, infrastructure

## Fallback Strategy

- WebGL unavailable: CSS animated gradient backgrounds per section
- Reduced motion: Static gradients, no camera movement, no particle animation
- Low FPS: Disable particles and post-processing, keep geometry
- Missing model: Gradient fallback with section title

## Verification Targets

- Desktop: 1440x900, 1920x1080
- Mobile: 390x844, 430x932
- Canvas: Nonblank on all sections
- Accessibility: Keyboard nav, focus rings, reduced-motion support
