# Trace Design Overhaul — "Warm Slate" Roadmap

## Design Direction
A refined, modern sports analytics aesthetic inspired by Strava and Linear. Warm slate tones, subtle depth, dark mode, and cohesive theming across all components.

---

## Phase 1: Design Foundation (app.css + variables)
**Goal:** Establish the new design system that everything else builds on.

- [ ] Rewrite `app.css` with new color tokens (light + dark mode)
- [ ] Add shadow, spacing, radius, and transition variables
- [ ] Define typography scale (14px base, tabular nums for metrics)
- [ ] Add `.page`, `.card`, `.btn` base styles with new design
- [ ] Add dark mode CSS variables (`[data-theme="dark"]`)
- [ ] Create `ThemeToggle.svelte` component (sun/moon icon)
- [ ] Integrate theme toggle into sidebar or topbar

---

## Phase 2: Core Components Refresh
**Goal:** Update shared components to use new design tokens.

- [ ] `StatCard.svelte` — new shadow, accent border, hover lift
- [ ] `Icon.svelte` — ensure consistent sizing/colors
- [ ] `Modal.svelte` — backdrop blur, slide-in animation
- [ ] `Toast.svelte` — slide-in from top-right, new colors
- [ ] `LoadingSpinner.svelte` — new color, subtle pulse
- [ ] `ErrorBanner.svelte` — refined variant colors
- [ ] `EmptyState.svelte` — new icon styling, better spacing
- [ ] `PeriodNav.svelte` — new pill/tab style
- [ ] `ActivityTable.svelte` — sport-color left border, hover states
- [ ] `HRZones.svelte` / `PowerZones.svelte` — consistent with new palette

---

## Phase 3: Layout & Navigation
**Goal:** Modernize the app shell (sidebar + topbar + content area).

- [ ] `App.svelte` sidebar: glassmorphism bg (backdrop-blur), active left accent bar
- [ ] `App.svelte` topbar: clean border-bottom, better brand treatment
- [ ] `App.svelte` content: smooth page transition (fade or slide)
- [ ] Mobile: improve sidebar slide-in, backdrop blur
- [ ] Sidebar collapse: smoother animation, tooltip labels when collapsed

---

## Phase 4: Dashboard
**Goal:** The most-seen page gets the biggest visual upgrade.

- [ ] Greeting header: subtle gradient bg or decorative accent
- [ ] Metric cards: left color border accent, shadow, hover lift
- [ ] Sparkline area: subtle fill gradient under the line
- [ ] Period tabs: new pill style with active indicator
- [ ] Recent activities table: sport-color left border, better row hover
- [ ] "By sport" card: refine SportBreakdown colors
- [ ] Heatmap card: new color scale for dark mode

---

## Phase 5: Key Pages
**Goal:** Bring the new design to the most-used secondary pages.

### Profile
- [ ] Hero section: gradient header, refined stats layout
- [ ] Benchmark cards: new shadow, accent icons, better grid
- [ ] Zone editor: refined zone bar colors, input styling
- [ ] Admin section: subtle card treatment

### Activities
- [ ] Filter panel: refined pill/toggle style
- [ ] Activity list: card-style rows with sport accent
- [ ] Pagination: new button style

### Activity Detail
- [ ] Map container: better border-radius, shadow
- [ ] Stats grid: new metric card style
- [ ] Lap table: refined row styling
- [ ] Chart section: better card treatment

### Training Calendar
- [ ] Calendar grid: refined day cells, today highlight
- [ ] Session details: better card/modal treatment

---

## Phase 6: Remaining Pages
**Goal:** Consistency across all pages.

- [ ] Statistics — new chart card treatment
- [ ] Heatmap — new color scale, dark mode support
- [ ] Monthly Stats — metric card style
- [ ] Milestones — card grid style
- [ ] Eddington — chart card treatment
- [ ] Gear — card grid, stat display
- [ ] Segments — table, map card
- [ ] Training Plans — timeline, card treatment
- [ ] Training Insights — chart, card treatment
- [ ] Fitness Tests — zone visualization
- [ ] Route Planner — map, form styling
- [ ] Upload — dropzone styling

---

## Phase 7: Dark Mode Polish
**Goal:** Full dark mode support across all components.

- [ ] Audit all hardcoded colors in components → replace with variables
- [ ] Test every page in dark mode
- [ ] Map/chart color adjustments for dark bg
- [ ] Sidebar glassmorphism in dark mode
- [ ] Persist theme choice (localStorage)

---

## Phase 8: Micro-interactions & Polish
**Goal:** Add life to the UI without overdoing it.

- [ ] Button hover/press transitions (scale + shadow)
- [ ] Card hover lift on interactive cards
- [ ] Page transition (fade or slide)
- [ ] Toast slide-in animation
- [ ] Modal backdrop blur + fade-in
- [ ] Sidebar collapse/expand transition refinement
- [ ] Zone bar smooth width transitions
- [ ] Loading skeleton shimmer (optional)

---

## Technical Notes

- **All styling via CSS variables** — no hardcoded hex values in components
- **Theme toggle** — `<html data-theme="dark">` swap, localStorage persistence
- **No new dependencies** — pure CSS, no Tailwind/etc.
- **Incremental** — each phase is independently shippable
- **Dark mode first** — design tokens support both from the start

---

## Out of Scope (for now)
- Framework migration (staying on Svelte 5 SPA)
- New pages or features
- Backend changes
- Mobile app (responsive web only)
