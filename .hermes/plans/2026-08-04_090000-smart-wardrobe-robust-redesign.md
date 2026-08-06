# Smart Wardrobe - Robust Redesign & Modular Architecture Plan

**Date:** 2026-08-04  
**Goal:** Transform the current partial frontend into a complete, robust, modular full-stack application with premium design system, proper backend, and maintainable architecture.

---

## Design Read

> Reading this as: **Consumer wardrobe management app** for personal use on mobile/kiosk (Raspberry Pi), with a **premium consumer / Apple-y language**, leaning toward **native CSS + Vanilla JS ES Modules + CSS Custom Properties design system + Motion-like micro-interactions**.

---

## Current State Audit

| Area | Status | Issues |
|------|--------|--------|
| **Backend** | ❌ Missing (only documented in KB) | No Python code, no FastAPI, no DB, no ML pipeline |
| **Frontend Templates** | ✅ Exists | `kiosk.html`, `settings.html` - need design system integration |
| **Frontend JS** | ✅ Exists | `kiosk.js`, `settings.js`, `utils.js`, `api.js` - need modular cleanup |
| **CSS Design System** | ❌ Missing | No `style.css` in `frontend/static/css/` |
| **Docker/Deploy** | ❌ Missing | No Dockerfile, docker-compose, nginx config |
| **Modularity** | ❌ Low | JS has duplicate utilities, tight coupling, no clear boundaries |

---

## Three Dials (from design-taste-frontend)

| Dial | Value | Rationale |
|------|-------|-----------|
| **DESIGN_VARIANCE** | 7 | Premium consumer - asymmetric but controlled |
| **MOTION_INTENSITY** | 5 | Spring physics on interactions, scroll-reveal, reduced motion support |
| **VISUAL_DENSITY** | 4 | Bento grid on settings, clean kiosk - not data-dense |

---

## Architecture Principles (Ponytail Mode + Modularity)

1. **Single Source of Truth** - CSS tokens in one file, shared by all views
2. **File Ownership** - Each module owns its files; no cross-contamination
3. **No Over-Abstraction** - One implementation per interface; add abstraction only when 2+ exist
4. **Root-Cause Fixes** - Fix shared utilities, not duplicated code
5. **Shortest Working Diff** - Minimal changes that actually work

---

## Phase 1: Design System Foundation (CSS Tokens + Base)

**File Ownership:** `frontend/static/css/style.css` (NEW)

### 1.1 CSS Custom Properties (Design Tokens)
```css
:root {
  /* Color - Single Accent: Deep Rose (LILA RULE compliant) */
  --accent: #e11d48;
  --accent-hover: #be123c;
  --accent-subtle: rgba(225, 29, 72, 0.12);
  --accent-glow: rgba(225, 29, 72, 0.35);

  /* Surface Elevation */
  --surface: #1e1e1e;
  --surface-elevated: #242424;
  --surface-overlay: #2a2a2a;

  /* Text */
  --text-primary: #fafafa;
  --text-secondary: #a3a3a3;
  --text-muted: #737373;

  /* Borders */
  --border: #333333;
  --border-soft: #404040;

  /* Shadows - Tinted to accent */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.4);
  --shadow-lg: 0 12px 32px rgba(0,0,0,0.5);
  --shadow-glow: 0 0 24px var(--accent-glow);

  /* Shape Consistency Lock - ONE radius system */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-full: 9999px;

  /* Motion Tokens */
  --ease-spring: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out: cubic-bezier(0.2, 0, 0.1, 1);
  --dur-fast: 150ms;
  --dur-base: 250ms;
  --dur-slow: 350ms;

  /* Typography */
  --font-sans: 'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'Geist Mono', ui-monospace, monospace;

  /* Layout */
  --maxw: 1400px;
  --nav-h: 56px;

  /* Noise overlay */
  --noise-opacity: 0.03;
}

/* Dark/Light mode - page theme lock */
@media (prefers-color-scheme: light) {
  :root {
    --surface: #fafafa;
    --surface-elevated: #ffffff;
    --surface-overlay: #f5f5f5;
    --text-primary: #18181b;
    --text-secondary: #52525b;
    --text-muted: #a1a1aa;
    --border: #e4e4e7;
    --border-soft: #d4d4d8;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
    --shadow-lg: 0 12px 32px rgba(0,0,0,0.12);
  }
}
```

### 1.2 Base Styles
- Reset, box-sizing, font-smoothing
- Noise overlay on `body::after` (fixed, pointer-events-none)
- Focus-visible rings for accessibility
- Reduced motion support
- Scrollbar styling

### 1.3 Utility Classes (minimal, no framework)
- `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-ghost`
- `.card`, `.card-elevated`
- `.input`, `.select`, `.label`
- `.toast`, `.toast-success`, `.toast-error`, `.toast-warning`, `.toast-info`
- `.modal`, `.modal-overlay`, `.modal-content`
- `.skeleton`, `.skeleton-image`, `.skeleton-text`
- `.grid-bento` (with `grid-auto-flow: dense`)

---

## Phase 2: Settings View Redesign (Modal + Grid + Upload)

**File Ownership:**
- `frontend/templates/settings.html` (MODIFY)
- `frontend/static/js/settings.js` (MODIFY)

### 2.1 HTML Changes (settings.html)
- Modern drag & drop image upload zone with preview
- Better form layout: grouped fieldsets, inline validation
- Proper modal markup with backdrop blur, slide-up animation
- Toast container (ARIA live region)
- Bento grid for garments (`grid-auto-flow: dense`)
- Empty state with actionable CTA
- Skeleton loading states matching final layout

### 2.2 JS Changes (settings.js)
- Remove duplicate utilities (use `utils.js` imports)
- Drag & drop upload with file input sync
- Form validation with inline error messages
- Image preview with remove button
- Modal focus trap + escape key + overlay click
- Toast system (shared via utils.js)
- IntersectionObserver for scroll-reveal on sections
- Bulk actions with selection state
- Edit/Delete garment with optimistic UI

---

## Phase 3: Wardrobe Grid Cards Redesign (Bento Grid)

**File Ownership:**
- `frontend/static/css/style.css` (ADD grid section)
- `frontend/static/js/settings.js` (MODIFY `renderGarmentGrid`)

### 3.1 Card Design
- Asymmetric bento-style grid (varied `col-span`/`row-span`)
- Image aspect-ratio preserved (4:5), `object-fit: cover`
- Hover physics: `scale(1.015)` + shadow glow + border highlight
- Tags: modern pill design with color swatch (`--tag-color`)
- Actions: floating on hover with backdrop blur
- Skeleton cards matching final layout exactly

### 3.2 Grid Layout
```css
.wardrobe-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  grid-auto-flow: dense;
  gap: 20px;
}
.wardrobe-item.featured { grid-column: span 2; }
.wardrobe-item.tall { grid-row: span 2; }
```

---

## Phase 4: Kiosk View Polish (Adaptive Layout)

**File Ownership:**
- `frontend/static/css/style.css` (ADD kiosk section)
- `frontend/templates/kiosk.html` (MINOR tweaks)
- `frontend/static/js/kiosk.js` (MINOR cleanup)

### 4.1 Layout Fixes
- `min-h-[100dvh]` not `100vh` (mobile viewport stability)
- Dual-panel desktop (60/40), single-panel mobile (slide-up)
- Smooth transitions between layout modes
- Touch targets ≥ 48px

### 4.2 Visual Hierarchy
- Visualization panel: larger outfit images, better score display
- Touch panel: tactile occasion/season grids, better selected state
- Stats: tabular-nums, larger display numbers
- Packing modal: improved layout, clearer results

### 4.3 Touch Gestures
- Swipe navigation between outfits
- Haptic feedback (`navigator.vibrate`)
- Pull-to-refresh hint

---

## Phase 5: Global Polish & Motion

**File Ownership:**
- `frontend/static/css/style.css` (global motion, focus, reduced motion)
- `frontend/static/js/utils.js` (shared utilities only)

### 5.1 Motion System
- Spring physics on ALL interactive elements (`var(--ease-spring)`)
- Staggered entry on grid load (`animation-delay: calc(var(--i) * 50ms)`)
- Scroll-reveal via IntersectionObserver (`.reveal-on-scroll`)
- Reduced motion: disable all animations, instant transitions

### 5.2 Accessibility
- Focus-visible rings on ALL interactive elements
- ARIA labels, roles, live regions
- Keyboard navigation (tab order, escape to close)
- Color contrast WCAG AA

### 5.3 Page Theme Lock
- No section flips dark↔light mid-page
- Grain overlay fixed `pointer-events-none` at `z-index: 9999`

---

## Phase 6: Backend Implementation (FastAPI + SQLModel + ML)

**File Ownership:** NEW `backend/` directory structure

### 6.1 Project Structure
```
backend/
├── api/
│   ├── main.py              # FastAPI app, lifespan, SPA fallback, static mounts
│   └── routers/
│       └── wardrobe.py      # CRUD endpoints
├── core/
│   └── config.py            # Pydantic Settings
├── models/
│   ├── garment.py           # SQLModel with dual image paths
│   ├── outfit.py            # Outfit + OutfitItem
│   └── schemas.py           # Pydantic schemas
├── repositories/
│   └── garment_repo.py      # Data access layer
├── services/
│   └── outfit_service.py    # Business logic
├── vision/
│   ├── segmenter.py         # SAM vit_b (CPU)
│   ├── classifier.py        # CLIP ViT-B-32
│   ├── color_extractor.py   # ColorThief
│   └── ingestion_pipeline.py # Dual storage write
└── ai_providers/
    ├── local.py             # Rules-based provider
    └── nim.py               # NVIDIA NIM (optional)
```

### 6.2 Key Fixes (from KB)
- PNG for masked images (not JPEG)
- `segment()` not `segment_auto()`
- RGBA handling in PIL
- CPU-only torch
- Dual image storage: `raw_image_path` + `processed_image_path`
- SPA fallback in FastAPI (`app.get("/{path:path}")`)

---

## Phase 7: Docker & Deployment

**File Ownership:** NEW files at root
- `Dockerfile` (multi-stage, CPU torch, non-root)
- `docker-compose.yml` (dev/prod profiles, volumes, nginx)
- `nginx.conf` (reverse proxy, static caching, gzip)
- `.env.example`

---

## Phase 8: Modularity & Code Quality

### 8.1 Shared Utilities (utils.js) - SINGLE SOURCE
Move ALL duplicated functions here:
- `formatType`, `formatPattern`, `formatFormality`
- `escapeHtml`, `getToastIcon`
- `showToast`, `openModal`, `closeModal`
- `prefersReducedMotion`, `debounce`, `triggerHaptic`

### 8.2 API Client (api.js) - SINGLETON
- `ApiClient` class with `request`, `getGarments`, `createGarment`, etc.
- Export singleton `api`

### 8.3 SPA Router (index.html) - NEW
```javascript
// Loads template → injects → dynamic import → calls init*()
const routes = {
  '/kiosk': { template: '/templates/kiosk.html', load: () => import('/static/js/kiosk.js') },
  '/settings': { template: '/templates/settings.html', load: () => import('/static/js/settings.js') }
};
```

---

## Verification Checklist (Pre-Flight)

- [ ] Zero em-dashes anywhere
- [ ] One accent color (Deep Rose `#e11d48`) used identically
- [ ] One corner-radius system (6/10/16/24/9999px)
- [ ] Every CTA text readable (WCAG AA 4.5:1)
- [ ] No CTA label wraps at desktop
- [ ] Form inputs, placeholders, focus rings, labels pass WCAG AA
- [ ] Hero fits viewport: headline ≤ 2 lines, CTA visible
- [ ] Max 1 eyebrow per 3 sections
- [ ] No split-header pattern
- [ ] No 3+ consecutive image+text-split sections
- [ ] No duplicate CTA intent
- [ ] Bento background diversity: 2-3 cells have visual variation
- [ ] Real images used (Picsum seeds for placeholders)
- [ ] No pills/labels overlaid on images
- [ ] No version footers
- [ ] Navigation on ONE line, height ≤ 80px
- [ ] Section-Layout-Repetition: ≥ 4 different layout families
- [ ] Bento has rhythm AND exact cell count
- [ ] Long lists use right UI component
- [ ] Motion motivated (every animation justified)
- [ ] GSAP ScrollTrigger skeletons use `start: "top top"`, `pin: true`
- [ ] No `window.addEventListener('scroll')` - use IntersectionObserver
- [ ] Reduced motion wrapped for `MOTION_INTENSITY > 3`
- [ ] Dark mode tokens defined and tested in both modes
- [ ] Mobile collapse explicit for high-variance layouts
- [ ] `min-h-[100dvh]`, never `h-screen`
- [ ] Empty/loading/error states provided
- [ ] Cards omitted in favor of spacing where possible
- [ ] Icons from Phosphor Icons (inline SVG)
- [ ] Core Web Vitals plausible (LCP < 2.5s, INP < 200ms, CLS < 0.1)

---

## Risks & Tradeoffs

| Risk | Mitigation |
|------|------------|
| JS/CSS coupling - Modal logic depends on specific IDs | Document ownership; coordinate changes |
| Image upload - Browser variance (iOS `capture="environment"`) | Test on Chrome + Safari; fallback to file input |
| Dark/Light mode - All new tokens must work in both | Define light mode tokens explicitly; test both |
| Performance - Animations on Pi | Use transform/opacity only; grain overlay fixed |
| Backend complexity - ML pipeline on CPU | CPU torch wheels; lazy-load models; cache SAM checkpoint |

---

## Git Strategy

```bash
# Phase 1-5: Frontend redesign
git add -A
git commit -m "feat: premium redesign - design system, settings modal, wardrobe grid, kiosk polish, global motion"

# Phase 6: Backend implementation
git add backend/
git commit -m "feat: backend - FastAPI, SQLModel, SAM/CLIP pipeline, dual image storage"

# Phase 7: Docker & deploy
git add Dockerfile docker-compose.yml nginx.conf .env.example
git commit -m "feat: docker - multi-stage build, compose profiles, nginx reverse proxy"

git push origin feat/server-kiosk-architecture
```

---

## Subagent Task Breakdown (for parallel execution)

| Task | Files Owned | Dependencies |
|------|-------------|--------------|
| 1. Design System CSS | `frontend/static/css/style.css` | None |
| 2. Settings Modal Redesign | `templates/settings.html`, `static/js/settings.js` | Task 1 (CSS tokens) |
| 3. Wardrobe Grid Cards | `static/css/style.css` (grid section), `static/js/settings.js` (render) | Task 1 |
| 4. Kiosk View Polish | `static/css/style.css` (kiosk section), `templates/kiosk.html` | Task 1 |
| 5. Global Polish & Motion | `static/css/style.css` (global), `static/js/utils.js` | Task 1 |
| 6. Backend Implementation | `backend/` (new) | None |
| 7. Docker & Deploy | Root config files | Task 6 |
| 8. Modularity Cleanup | `static/js/utils.js`, `static/js/api.js`, `index.html` | Tasks 2-5 |