# Pulse XI Atelier ? Precision Meets Motion

A web interpretation of Apple's design principles with Pulse XI's own football identity. This is not an Apple component library or endorsement. No Apple artwork, proprietary font, third-party glass renderer or new package is included.

## Design decisions

| Official guidance | Pulse XI decision |
|---|---|
| [Design principles](https://developer.apple.com/design/human-interface-guidelines/design-principles): purpose, simplicity and craft | Prioritize the match, then its evidence. Use a larger editorial title and score, readable secondary data and fewer competing borders. |
| [Layout](https://developer.apple.com/design/human-interface-guidelines/layout) | Retain route identities and workflow order while adapting proportions, spacing and columns to the available width. |
| [Materials](https://developer.apple.com/design/human-interface-guidelines/materials), [Liquid Glass](https://developer.apple.com/documentation/technologyoverviews/liquid-glass) | Glass belongs to navigation and elevated sheets. Statistics, forms and histories use opaque reading surfaces. |
| [Motion](https://developer.apple.com/design/human-interface-guidelines/motion) | Reveal a route or newly selected match once. Scroll reveals clarify substantial sections. Data values never interpolate; engine ticks never restart entry motion. |
| [Color](https://developer.apple.com/design/human-interface-guidelines/color) | Warm white and silver on graphite; restrained teal for interaction. Existing team colors and chart categories remain intact. |
| [Dark Mode](https://developer.apple.com/design/human-interface-guidelines/dark-mode) | An intentionally dark, immersive football workspace. Test reduced transparency and increased contrast independently; do not equate them. |

This is a substantive redesign of the earlier Precision Glass theme. The previous pixel-freeze contract is superseded by the user's explicit instruction to preserve functional structure, rather than legacy dimensions. Historical captures remain available under `docs/images/precision-glass`; they are not current layout specifications.

## Interface composition

- **Chrome:** left rail stays left; the four route destinations remain above content. The header recedes, and route navigation becomes a rounded material surface with a physically selected state and 44px targets.
- **Match room:** a display title, spacious team identities, original colored initials on neutral shield geometry, and a large central score create a distinct first-viewport hierarchy. Values remain direct source bindings.
- **Field:** an immersive frame, full-width SVG and refined metadata surround the original coordinate system. No field coordinate, event path, scene renderer, camera behavior or model changes.
- **Intelligence:** larger comparison values, calmer labels, thin comparison bars, readable source explanations and meaningful section headings. Secondary panels align beside the field on wide displays and below it on narrow ones.
- **Sandbox:** an editorial introduction and clearer seed form retain the recorded workflow. Copy accurately directs live experiments to Engine Control Room.
- **Runtime:** larger heading, calmer grouped forms, deliberate spacing, readable clock and experiment tables. Checkpoint, restoration, history, verification and recovery controls retain their functions.
- **Data Hub:** a clear page introduction, spacious import controls, readable dataset cards and consistent lifecycle dialogs.
- **Newly merged features:** Control vs Chaos, FanDNA and branch ProofTrail retain their algorithms, locales, evidence and authorization while sharing the material and typography system.
- **Broadcast:** the existing synchronized cue surface and verified proof sheet receive restrained lower-third styling, readable source text and a short entrance.

## Tokens and type

Source: `frontend/src/precision-glass.css`, scoped to `html[data-px-material="glass"]`.

| Family | Values |
|---|---|
| Canvas / reading / raised | `#0b0d0e` / `#17191b` / `#202326` |
| Primary / secondary / muted text | `#f5f4ef` / `#b7babe` / `#a0a5aa` |
| Accent / accent ink | `#b6e4d5` / `#102c27` |
| Spacing | 4, 8, 12, 16, 24, 32, 48px; responsive display margins |
| Corners | 12px controls, 20px groups, 28px stages, pill navigation |
| Typography | Platform system stack: `-apple-system`, BlinkMacSystemFont, Segoe UI, Arial, sans-serif |
| Display | Match title 30?54px, runtime title 36?68px, score 58?110px |
| Reading | 13?16px body, 11?12px supporting labels; uppercase reserved for short metadata |
| Numbers | Tabular figures on scores, clocks, comparisons and tables |

English navigation and metric headings use readable title/sentence case. Hindi and Spanish catalogs and fallback behavior remain unchanged. There are no downloaded fonts or invented team crests.

## Materials and interaction

The CSS is a replacement visual system, not another long override appended to the previous theme. Existing feature styles still provide functional layout; the scoped system defines presentation, responsive proportions and common controls. Native inputs, selects, buttons, meters and dialogs remain semantic controls. Existing focus traps, keyboard handlers, source identities and API clients are untouched.

The small navigation surface, raised evidence/dialog sheets and the transient 4px modal scrim use backdrop filtering. No filter is applied to the SVG or canvas elements; the modal scrim is active only while evidence is open. Static gradients supply environmental depth; no animated fullscreen wallpaper, new renderer, duplicate scene or pointer-tracking loop exists.

Selected controls have readable dark ink on a pale accent surface. Focus has a visible outline independent of hover. Hover and press feedback do not change stored values. Decorative layers ignore pointer events.

## Motion

`useAtelierMotion.ts` attaches one IntersectionObserver to substantial visible sections on route, selected-match or loaded-match identity changes. It owns no application state and makes no requests. The observer releases each section after its first reveal and disconnects on cleanup. Engine ticks, analytics refreshes and event selection do not restart entry motion.

- Hover: 160ms color/material response.
- Selection/press: short composited transform and material feedback.
- Route/match/scroll reveal: 560ms opacity and 14px translation with `cubic-bezier(.22,1,.36,1)`.
- Evidence sheet: 360ms opacity and horizontal reveal.
- No width/grid/height animation or score interpolation.

Without JavaScript or IntersectionObserver, content is visible. Keyboard focus reveals a section immediately. Reduced motion disables decorative transitions and reveals all content. Switching the preference mid-session also reveals queued sections.

## Responsive and accessibility contract

Seven viewports: 1920?1080, 1440?900, 1280?800, 1024?768, 768?1024, 390?844, 375?812.

`glass-layout.spec.ts` retains real scenario creation, engine stepping and checkpoint capture. It compares control identity/order across material application, not old positions. It checks navigation target sizes, logical section order, heading clipping, viewport bounds, overflow, meaningful hero dimensions and usable runtime actions. It captures both presentations for review. Exact source values remain independently tested by replay, analysis, broadcast, runtime and experiment suites.

Other checks cover keyboard sequence/focus, proof opening/closing, reduced motion, independent contrast/transparency preferences, readable selected controls, route reveals and replay stability. Existing WebGL fallback, observer and viewport-stability regressions remain enabled.

Reduced transparency makes chrome opaque without activating increased-contrast borders. Increased contrast separately strengthens text and boundaries. Forced colors use system colors. These are tested behaviors, not blanket WCAG or physical-device certification.

## Verification and evidence

```powershell
cd frontend
npm ci
npm run build
npm run test:e2e
npx playwright install firefox webkit
npx playwright test -c playwright.materials.config.ts
```

The full suite uses real FastAPI execution, isolated SQLite databases and test credentials. Cross-browser visual checks use Chromium, Firefox and Playwright WebKit. WebKit automation is not physical Safari/iPhone certification. Software-rendered observer measurements are not physical-GPU benchmarks.

Real screenshots and measured results for this revision are recorded below. Prior screenshot reports are retained as historical evidence. No production credential is serialized in captures.

## References and provenance

The official Apple pages above informed hierarchy and interaction decisions. They do not provide a native Apple web implementation. MIT-licensed [rdev/liquid-glass-react](https://github.com/rdev/liquid-glass-react) was evaluated as a reference; its optical renderer and partial browser displacement support are unnecessary for this bounded control layer. No third-party source was copied. Existing Pulse XI asset provenance and release restrictions continue to apply.

## Atelier visual evidence

Application source: `4498f571f48d33ce57d91799036aeb920f216d8a`, based on main `64ab498`. Before/after pairs use identical DOM, fixture cutoff and viewport; the before image disables the material stylesheet to expose the legacy presentation. This is a real-browser comparison, not a concept render. The previous rejected Precision Glass captures remain under `images/precision-glass` for historical comparison.

| Route | 1440?900 | 390?844 |
|---|---|---|
| Match Intelligence | [Before](images/atelier/replay-1440-before.png) / [After](images/atelier/replay-1440-after.png) | [Before](images/atelier/replay-390-before.png) / [After](images/atelier/replay-390-after.png) |
| Sandbox Lab | [Before](images/atelier/sandbox-1440-before.png) / [After](images/atelier/sandbox-1440-after.png) | [Before](images/atelier/sandbox-390-before.png) / [After](images/atelier/sandbox-390-after.png) |
| Engine Control Room | [Before](images/atelier/runtime-1440-before.png) / [After](images/atelier/runtime-1440-after.png) | [Before](images/atelier/runtime-390-before.png) / [After](images/atelier/runtime-390-after.png) |
| Data Hub | [Before](images/atelier/data-1440-before.png) / [After](images/atelier/data-1440-after.png) | [Before](images/atelier/data-390-before.png) / [After](images/atelier/data-390-after.png) |

The [responsive report](images/atelier/responsive-report.json) contains all 28 route/viewport checks. The full seven-size screenshot matrix is generated by the test suite. Additional real states: [checkpoint inspection](images/atelier/atelier-checkpoint.png), [ForkCast comparison](images/atelier/atelier-forkcast.png), [proof sheet](images/atelier/atelier-proof.png), [broadcast overlay](images/atelier/broadcast-cues-1440.png), [mobile broadcast](images/atelier/broadcast-cues-390.png), [loaded original 3D assets](images/atelier/original-asset-observer.png).

Visual review found a substantially larger title/score hierarchy, a distinct material navigation layer, a framed field stage and readable form groups. It also caught muted child text on a selected event row; selected text now inherits contrasting ink while team marker color remains unchanged. A regression checks both.

## Measured cost and verification

Baseline: clean main `64ab498`, built in a separate worktree. Environment: Windows 10.0.26300, Intel Core i7-1355U, Playwright Chromium 156.0.8078.4, 1440?900, reduced transparency enabled, reduced motion disabled. Five fresh browser contexts per version used the same recorded fixture and cutoff 3500, with warm local services.

| Metric | Main baseline | Atelier |
|---|---:|---:|
| Entry JavaScript, raw | 385,813 bytes | 386,894 bytes |
| CSS, raw | 50,412 bytes | 90,000 bytes |
| Optional scene chunk, raw | 983,869 bytes | 983,869 bytes |
| First useful screen P50 / P95 | 358 / 373 ms | 384 / 407 ms |
| Seek-to-insight P50 / P95 | 282 / 293 ms | 334 / 381 ms |
| Scroll RAF callback interval P95 | 16.8 ms | 16.8 ms |

These small-sample results are descriptive. They do not establish an improvement, production SLA, rendered FPS or physical-GPU performance. The redesign adds CSS and a small observer helper; no package, font, image or renderer is loaded into the app. [Raw timings](images/atelier/performance.json) and [raw/gzip-9 bundle measurements](images/atelier/bundles.json) are included.

```powershell
# With baseline and candidate local preview servers running:
node scripts/measure-ui.mjs http://127.0.0.1:8011 http://127.0.0.1:8000 ui-measurements.json 5
```

Verification in this session: 344 backend tests passed with an empty backend diff; 90 ordinary browser tests passed, including all 28 responsive comparisons. Six focused accessibility/motion tests and six Chromium/Firefox/WebKit material tests passed. Both committed manifest/experiment verifiers, all seven asset validators, pip check and the production npm audit passed. The maximum-history ForkCast probe exceeded its unchanged 90-second comparison-arrival budget locally, including an isolated run and a clean-main reproduction without the redesign. It is not counted as a pass. The same main source passed [Linux CI](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/39749797674); this laptop result remains a documented limitation. Fresh exact-head CI is required before reporting the entire suite green.

## Replay reading stability (audit increment)

The analysis refresh cadence is independent from the 200 ms replay renderer:
server analysis samples at 1 Hz during playback and uses the exact paused seek.
Retained public packets must belong to the current match, not exceed its cutoff,
and (for recaps) match locale/persona/favorite scope. Their actual cutoff remains
visible. Backward seeks conceal future packets immediately. Private runtime pass
analysis retains its stricter exact-key behavior.

Recap/moment lists, pass detail and rhythm detail use bounded, keyboard-focusable
reading viewports with overflow, rather than dropping whole content trees while
loading. Text remains reachable; browser zoom may increase internal scrolling.
Tactical descriptive text reserves four lines without a maximum/clipping rule.
These are reading surfaces, not new routes or data models. Playback no longer
changes the analyst's selected team merely because a new pass occurs.
