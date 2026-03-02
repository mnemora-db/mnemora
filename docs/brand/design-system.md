# Mnemora — Brand & Design System

## Design Philosophy

Mnemora's visual identity draws from two parallel traditions: the precision of Swiss/International typographic design (clean grids, geometric forms, high contrast) and the organic mystique of Greek classical aesthetics (memory as something ancient, powerful, almost sacred). The result is a brand that feels technically rigorous yet intellectually rich — a database product that treats memory as something worth designing beautifully.

**Core Principles:**
- **Precision over decoration.** Every element serves a purpose. No ornamental noise.
- **Dark-first.** Developers work in dark environments. Our brand lives in the dark.
- **Monochrome dominance, surgical accent.** 95% grayscale. Color only where it earns attention.
- **Typography as interface.** Text is our primary material. Make it count.

---

## Color System

### Primary Palette

Our palette is deliberately constrained. Like Vercel, we use a gray scale as the foundation with a single accent color family for emphasis. Unlike Vercel's pure black/white, Mnemora uses a slightly warm dark tone (hint of blue) to evoke depth — like looking into deep water where memories are stored.

```
BACKGROUNDS
--mn-bg-primary:      #09090B     Deep void (near-black with blue undertone)
--mn-bg-secondary:    #111114     Elevated surface
--mn-bg-tertiary:     #18181B     Card/panel background
--mn-bg-inverse:      #FAFAFA     Light mode background

BORDERS & LINES
--mn-border-subtle:   #27272A     Subtle dividers
--mn-border-default:  #3F3F46     Default borders
--mn-border-strong:   #52525B     Emphasized borders

TEXT
--mn-text-primary:    #FAFAFA     Primary text (high contrast)
--mn-text-secondary:  #A1A1AA     Secondary text, labels
--mn-text-tertiary:   #71717A     Tertiary text, placeholders
--mn-text-inverse:    #09090B     Text on light backgrounds

ACCENT — Teal/Cyan (Memory = water = depth)
--mn-accent:          #2DD4BF     Primary accent (teal-400)
--mn-accent-hover:    #5EEAD4     Hover state (teal-300)
--mn-accent-muted:    #0D9488     Muted accent for backgrounds (teal-600)
--mn-accent-subtle:   #134E4A     Very subtle accent tint (teal-900)

SEMANTIC STATUS
--mn-success:         #22C55E     Green-500
--mn-warning:         #EAB308     Yellow-500
--mn-error:           #EF4444     Red-500
--mn-info:            #3B82F6     Blue-500
```

**Why Teal?** It's uncommon in the developer tools space (Vercel = black/white, Supabase = green, PlanetScale = yellow, Neon = neon green). Teal sits between blue (trust, technology) and green (growth, data) — perfect for a memory database. It also evokes the Greek sea, connecting to our Mnemosyne etymology.

### Color Usage Rules

1. Backgrounds are ALWAYS from the gray scale. Never use accent as a background on large surfaces.
2. Accent color is reserved for: interactive elements (buttons, links), status indicators, code highlights, and the logo mark.
3. Text NEVER uses accent color for body copy. Only for links and highlighted inline code.
4. Borders default to `--mn-border-subtle`. Use `--mn-border-default` only on interactive components.
5. Cards and panels use `--mn-bg-tertiary` with `--mn-border-subtle` border.

---

## Typography

### Font Stack

```
PRIMARY (Sans):       "Geist Sans", "Inter", -apple-system, BlinkMacSystemFont, sans-serif
MONOSPACE:            "Geist Mono", "JetBrains Mono", "Fira Code", monospace
DISPLAY (Headings):   "Geist Sans", same fallbacks — but at weight 600-700
```

**Why Geist?** It's open-source (SIL OFL), designed specifically for developer interfaces, and has the Swiss-inspired geometric precision that matches our brand. It is NOT owned by Vercel — it's an open-source typeface anyone can use. If a more distinctive choice is needed for marketing (not product UI), consider pairing with "Satoshi" or "General Sans" for display headings.

### Type Scale

```
DISPLAY-XL:   48px / 1.1 line-height / -0.02em tracking / Weight 700
DISPLAY:      36px / 1.15 / -0.02em / Weight 700
HEADING-1:    30px / 1.2 / -0.015em / Weight 600
HEADING-2:    24px / 1.3 / -0.01em / Weight 600
HEADING-3:    20px / 1.4 / -0.005em / Weight 600
BODY-LG:      18px / 1.6 / 0em / Weight 400
BODY:         16px / 1.6 / 0em / Weight 400
BODY-SM:      14px / 1.5 / 0em / Weight 400
CAPTION:      12px / 1.5 / 0.02em / Weight 500
CODE:         14px / 1.6 / 0em / Weight 400 (Monospace)
```

### Typography Rules

1. **Headings** use negative letter-spacing (tighter). Body text uses neutral spacing.
2. **Code** always in monospace with a subtle background tint (`--mn-accent-subtle` at 10% opacity).
3. **Links** use `--mn-accent` with underline-offset of 3px. No underline on hover (remove, don't add).
4. **Numbers in data** use `font-variant-numeric: tabular-nums` for alignment.
5. **Marketing headlines** can go up to DISPLAY-XL. Product UI never exceeds HEADING-1.

---

## Logo

### Concept

The Mnemora logo mark is an abstract "M" that also evokes a neural pathway or wave pattern — representing the flow of memory. It uses clean geometric strokes, not filled shapes.

### Logo Specifications

```
WORDMARK:     "mnemora" in lowercase, Geist Sans weight 600, tracking -0.03em
MARK:         Abstract geometric M — two connected arcs forming memory pathways
ARRANGEMENT:  Mark + wordmark (horizontal) or mark-only for small contexts
```

### Logo Color Usage

```
On dark backgrounds:   White mark (#FAFAFA) + white wordmark
On light backgrounds:  Black mark (#09090B) + black wordmark  
Accent variant:        Teal mark (#2DD4BF) + white/black wordmark (special contexts only)
Monochrome:            Always acceptable. Never use gradients on the logo.
```

### Clear Space

Minimum clear space around the logo = height of the "m" character in the wordmark, on all four sides.

### Minimum Size

Wordmark + mark: minimum 100px wide. Mark only: minimum 24px.

---

## Spacing & Layout

### Spacing Scale (8px base)

```
--mn-space-1:    4px     Tight padding (within badges, pills)
--mn-space-2:    8px     Default inner padding
--mn-space-3:    12px    Component padding
--mn-space-4:    16px    Standard gap
--mn-space-5:    24px    Section gap
--mn-space-6:    32px    Large gap
--mn-space-8:    48px    Section separation
--mn-space-10:   64px    Page section separation
--mn-space-12:   96px    Hero/major section separation
```

### Border Radius

```
--mn-radius-sm:    6px    Buttons, badges, inputs
--mn-radius-md:    8px    Cards, panels
--mn-radius-lg:    12px   Modals, large containers
--mn-radius-full:  9999px Pills, avatars
```

### Grid

- Landing page: max-width 1200px, centered, 24px horizontal padding
- Dashboard: full-width with 280px sidebar, 16px gaps
- Documentation: max-width 768px content area, right sidebar for TOC
- 12-column grid with 16px gutters for complex layouts

---

## Component Patterns

### Buttons

```css
/* Primary */
background: var(--mn-accent);
color: #09090B;
font-weight: 500;
padding: 8px 16px;
border-radius: 6px;
transition: background 150ms ease;

/* Primary Hover */
background: var(--mn-accent-hover);

/* Secondary */
background: transparent;
border: 1px solid var(--mn-border-default);
color: var(--mn-text-primary);

/* Secondary Hover */
background: var(--mn-bg-tertiary);
border-color: var(--mn-border-strong);
```

### Cards

```css
background: var(--mn-bg-tertiary);
border: 1px solid var(--mn-border-subtle);
border-radius: 8px;
padding: 24px;
transition: border-color 200ms ease;

/* Hover */
border-color: var(--mn-border-default);
```

### Code Blocks

```css
background: var(--mn-bg-secondary);
border: 1px solid var(--mn-border-subtle);
border-radius: 8px;
padding: 16px;
font-family: var(--font-mono);
font-size: 14px;
line-height: 1.6;

/* Inline code */
background: rgba(45, 212, 191, 0.08);  /* accent at 8% opacity */
padding: 2px 6px;
border-radius: 4px;
font-size: 0.9em;
```

### Navigation

Top bar: `--mn-bg-primary` with bottom border `--mn-border-subtle`. 
Height: 64px. Logo left, nav center, CTA right.
Blur backdrop on scroll: `backdrop-filter: blur(12px); background: rgba(9,9,11,0.8);`

---

## Motion & Animation

### Principles

1. **Subtle and purposeful.** No decorative animation. Every motion communicates state change.
2. **Fast.** 150ms for micro-interactions, 300ms for layout transitions, 500ms for page transitions.
3. **Ease curves:** `cubic-bezier(0.22, 1, 0.36, 1)` for entrances, `ease-out` for exits.

### Standard Animations

```css
/* Fade in up (page load, card entrance) */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Stagger children on page load */
.stagger > * {
  animation: fadeInUp 400ms cubic-bezier(0.22, 1, 0.36, 1) both;
}
.stagger > *:nth-child(1) { animation-delay: 0ms; }
.stagger > *:nth-child(2) { animation-delay: 80ms; }
.stagger > *:nth-child(3) { animation-delay: 160ms; }
.stagger > *:nth-child(4) { animation-delay: 240ms; }

/* Skeleton loading pulse */
@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}
```

---

## Copywriting Voice

### Tone

- **Direct.** Active voice. Short sentences. No filler words.
- **Technical but accessible.** Assume the reader is a developer but don't gatekeep with jargon.
- **Confident, not arrogant.** State what we do. Don't oversell.
- **Second person.** "Your agents remember" not "Our system enables memory persistence."

### Patterns

```
GOOD: "Store. Search. Remember."
BAD:  "Enabling AI agents to persistently store and retrieve contextual memory data."

GOOD: "Your agent remembers."
BAD:  "Leverage our cutting-edge memory infrastructure."

GOOD: "One API. Four memory types. Sub-10ms."
BAD:  "Mnemora provides a comprehensive unified API supporting multiple memory modalities."
```

### Headlines Template

Marketing: `[Short punchy statement]. [Supporting detail].`
Example: "Memory infrastructure for AI agents. One API. Four memory types."

Documentation: `[Action verb] [what]`
Example: "Store semantic memories" / "Search across memory types" / "Configure TTL policies"

Error messages: `[What happened]. [What to do].`
Example: "Vector dimension mismatch. Expected 1024, got 512. Check your embedding model configuration."

---

## Document Formatting (for Word, PDFs, Decks)

### Cover Pages

- Background: `--mn-bg-primary` (#09090B)
- Title: DISPLAY-XL, white, centered vertically at ~40% from top
- Subtitle: BODY-LG, `--mn-text-secondary`, 16px below title
- Logo mark bottom-left, small
- Date/version bottom-right, CAPTION size, `--mn-text-tertiary`
- Thin teal accent line (1px) at ~30% from top, full width

### Internal Pages

- White/light background for readability in print
- Headers: Geist Sans weight 600, `--mn-bg-primary` color
- Body: 16px, 1.6 line height, `--mn-text-inverse` 
- Code snippets: light gray background (#F4F4F5), monospace, 14px
- Accent sparingly: teal for links and highlighted key terms only
- Page numbers: bottom-right, CAPTION, gray

### Tables

- Header row: `--mn-bg-tertiary` on dark, light gray (#F4F4F5) on light
- No vertical borders. Horizontal lines only.
- Cell padding: 12px horizontal, 8px vertical
- Alternating row backgrounds at 2% opacity difference (barely visible)

---

## Comparison: Vercel vs Mnemora

| Aspect | Vercel | Mnemora (Ours) |
|--------|--------|---------|
| Base palette | Pure B&W (#000/#FFF) | Warm dark (#09090B/#FAFAFA) |
| Accent | No single accent (uses blue, red, amber contextually) | Teal (#2DD4BF) as brand accent |
| Typography | Geist Sans + Mono | Same (it's open source OFL), differentiated by weight usage |
| Logo | Triangle (▲) geometric | Abstract M / neural pathway — geometric strokes |
| Motion | Minimal, status-driven | Same philosophy, slightly more entrance animation on marketing |
| Voice | Corporate-technical | Direct-developer ("Your agent remembers") |
| Theme | System/light/dark | Dark-first, light supported |
| Layout | Dense, dashboard-centric | Content-first, documentation-heavy |
| Brand feel | "The Frontend Cloud" — infrastructure | "Where agents remember" — cognitive, evocative |

**Key differentiation:** We share the Swiss precision DNA but diverge on personality. Vercel is corporate infrastructure. Mnemora is developer-intimate — it's YOUR agent's memory, something personal and powerful. The teal accent adds a distinct, ownable color that no major dev tool competitor uses.

---

## Asset Checklist

Before launch, create:

- [ ] Logo mark (SVG, PNG @1x/2x/4x)
- [ ] Wordmark (SVG, PNG)
- [ ] Logo + wordmark lockup (horizontal, stacked)
- [ ] Favicon (32x32, 16x16) — simplified mark in teal on dark
- [ ] OG image template (1200x630) — dark bg, logo, tagline
- [ ] Twitter/X banner (1500x500)
- [ ] GitHub social preview (1280x640)
- [ ] README header image
- [ ] Slide deck template (16:9, dark + light variants)
- [ ] Documentation site theme (dark-first)
- [ ] Dashboard UI kit (Figma or code components)
- [ ] Email template (transactional: welcome, API key, alerts)
