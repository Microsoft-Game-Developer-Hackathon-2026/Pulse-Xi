# Precision Glass ? Pulse XI visual system

A web interpretation of Apple's material hierarchy, with Pulse XI's own identity. It is not an Apple implementation, endorsement or platform API. All CSS is authored for this repository; no Apple assets, proprietary fonts, external glass code or new dependencies are included.

## Scope and layout contract

Baseline: main `c2f8c622d21d3db804e57c9a02e4c09b264f9c4b`. The component tree, DOM order, routes, control labels, state, authentication, API clients, pitch coordinates and canvas are unchanged. `main.tsx` adds one stylesheet import; `index.html` sets the material attribute and browser-chrome color. No business component is edited.

`precision-glass.css` is scoped by `html[data-px-material="glass"]`. This attribute is not a user preference or new application setting. Tests temporarily remove it to measure the original CSS on the same DOM, data and captured server state, then restore it. Existing styles retain ownership of widths, heights, margins, padding, grids, flex order, responsive breakpoints and overflow. The 76px desktop rail, 110px header and existing mobile arrangement remain intact.

The geometry suite covers replay, Sandbox, Data Hub and authenticated runtime, including a real engine step and checkpoint, at1920?1080,1440?900,1280?800,1024?768,768?1024,390?844,375?812. Principal region boundaries and visible control order are compared, with2px desktop/4px mobile limits. Local initial material verification measured **0px maximum delta** across all28 combinations. This measures principal regions, not every glyph. Chromium geometry captures explicitly use no reduced-transparency/contrast preference; accessibility fallback tests exercise the alternative material.

## Tokens

| Token | Value / purpose |
|---|---|
| `--px-bg-base` | `#090d14`, graphite canvas |
| `--px-surface` | `#121923`, opaque reading layer |
| `--px-glass-regular` | charcoal translucent chrome |
| `--px-glass-strong` | nearly opaque overlay material |
| `--px-text-primary` | `#edf2fa` |
| `--px-text-secondary` | `#b3bed0` |
| `--px-text-muted` | `#96a5bd` |
| `--px-accent` | `#8be3df`, restrained teal |
| success / warning / error | mint / sand / warm coral; labels remain present |
| radius sm / md / lg / pill |8px /12px /20px /999px |
| motion fast / normal |150ms /240ms |
| easing | `cubic-bezier(.22,1,.36,1)` |

Team-owned colors, event categories, chart scales and SVG coordinates remain unchanged. Platform/Arial font stacks are reused; branding and scoreboard use the available Arial face. Numeric reading regions use tabular figures without interpolating scores. No web fonts are downloaded.

## Material hierarchy

- **Navigation and chrome:** subtle reflections, vertical edge light, quiet active accent. The long rail uses static gradients, not a fullscreen blur. Header blur is limited to12px on capable desktop browsers.
- **Reading surfaces:** nearly opaque graphite for analytics, evidence, forms, histories and tables. No backdrop filter is applied to these surfaces. Existing divider thickness and box sizing are retained.
- **Controls:** rounded surfaces, small inset highlight, restrained shadow, clear selected/disabled states. Native input/select semantics and existing hit areas remain intact.
- **Scoreboard:** fixed original grid with static atmospheric light and specular sheen. Existing team identity and authoritative numbers are preserved.
- **Pitch/observer:** framing only. No new filter, transform, renderer, texture, animation or sizing rule is applied to SVG/canvas geometry.
- **Overlays:** strong contrasting material on existing drawers/dialogs;16px blur only where supported. Existing focus/close behavior is untouched. Decorative backgrounds cannot intercept pointer events.

## Motion and accessibility

Only color, background-color, border-color and shadow transitions are used for controls. Existing overlays may reveal with opacity and5px translation on genuine mount. There is no layout animation, new requestAnimationFrame loop, scroll listener, parallax, continuously animated backdrop or value interpolation. Existing viewport preservation is not replaced.

`prefers-reduced-motion` removes decorative animation and transitions. Reduced transparency and increased contrast use opaque surfaces and stronger text/borders. Forced colors use system colors and a visible Highlight focus ring. On narrow/coarse-pointer devices, backdrop filters are disabled. Unsupported backdrop-filter has an opaque fallback. Keyboard, native controls and all actual error/disabled states remain usable. Tests check focus, real evidence opening/closing under reduced motion, and a minimum4.5:1 secondary-token contrast against the reading surface in increased-contrast mode; this is not a blanket WCAG certification.

## Cost and browser verification

No dependency, font, image, video, wrapper, extra canvas or pointer-following effect is added. Production CSS initially changed from42.59kB (10.38kB gzip) to55.32kB (13.09kB gzip); entry JavaScript remains350.26kB and the scene chunk983.87kB in the same local build. These are Vite-reported sizes, not a frame-rate guarantee. Existing graphics tests inspect real loaded scenes and fallbacks. Software-rendered tests do not certify physical-GPU performance.

Chromium, Firefox and Playwright WebKit were exercised at desktop/mobile widths through real routes and reduced motion. Playwright WebKit is not a physical Safari/iPhone certification. Full functional regressions use Chromium and real FastAPI with isolated SQLite databases.

```powershell
# frontend
npm ci
npm run build
npx playwright install chromium
npm run test:e2e
# Optional separate engine coverage; no application dependency added
npx playwright install firefox webkit
npx playwright test -c playwright.materials.config.ts
```

`glass-layout.spec.ts` writes screenshot/geometry artifacts to its test output; set `PX_VISUAL_DIR` to a local directory for retained captures. Captures use the same page, engine state and viewport before/after. No credentials are serialized in geometry reports.

## Reference evaluation and provenance

- [Apple Materials](https://developer.apple.com/design/human-interface-guidelines/materials), [Liquid Glass overview](https://developer.apple.com/documentation/technologyoverviews/liquid-glass), [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines), [WWDC25 Meet Liquid Glass](https://developer.apple.com/videos/play/wwdc2025/219/): functional chrome is distinct from content; reading surfaces retain legibility. This implementation translates that hierarchy into ordinary CSS.
- [rdev/liquid-glass-react](https://github.com/rdev/liquid-glass-react): MIT; README documents partial displacement support in Safari/Firefox. Not adopted.
- [dpawlikowski/liquid-glass](https://github.com/dpawlikowski/liquid-glass): MIT, React peer>=18, CSS/SVG scene duplication and optical effects. Not adopted.
- [aberhamm/liquid-glass-react](https://github.com/aberhamm/liquid-glass-react): MIT, React peer>=18 and browser-specific fallback tiers. Not adopted.

These projects were evaluated as references, not installed or certified against Pulse XI. Their wrappers, scene duplication and optical effects are unnecessary for the protected layout. No third-party source or assets were copied.

## Captured visual evidence

| Screen/state | Original | Precision Glass |
|---|---|---|
| Recorded replay,1440px, cutoff3500 | [Before](images/precision-glass/replay-1440-before.png) | [After](images/precision-glass/replay-1440-after.png) |
| Authenticated runtime/scenario builder,1440px, tick20 | [Before](images/precision-glass/runtime-1440-before.png) | [After](images/precision-glass/runtime-1440-after.png) |
| Data Hub,1440px, canonical built-in source filter | [Before](images/precision-glass/data-1440-before.png) | [After](images/precision-glass/data-1440-after.png) |
| Sandbox,390px, cutoff3500 | [Before](images/precision-glass/sandbox-390-before.png) | [After](images/precision-glass/sandbox-390-after.png) |

[Geometry summary](images/precision-glass/layout-report.json) records all28 route/viewport comparisons. These are real browser captures, not concept renders. Local full-resolution captures also include the checkpoint/ForkCast and pass-inspection surfaces. Screenshot PNGs are documentation only and are never loaded by the application.
