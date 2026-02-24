# Frontend Inspiration Sources

> Curated list of design inspiration sources and workflow for gathering creative ideas.

---

## Inspiration Sources

### Primary Sources

| Source | URL | Best For |
|--------|-----|----------|
| Godly | https://godly.website | High-end web design, portfolios, creative agencies |
| Awwwards | https://www.awwwards.com | Award-winning sites, cutting-edge techniques |
| Dribbble | https://dribbble.com | UI components, visual design, illustrations |
| Mobbin | https://mobbin.design | Mobile UI patterns, app screens |
| Land-book | https://land-book.com | Landing page inspiration |
| Curated Design | https://curated.design | Design systems, component libraries |

### Specialized Sources

| Source | URL | Best For |
|--------|-----|----------|
| Framer Showcase | https://www.framer.com/showcase | Framer-specific patterns |
| Readymag | https://readymag.com/showcase | Editorial, storytelling layouts |
| Cargo Collective | https://cargo.site | Artist portfolios, experimental |
| Brutalist Websites | https://brutalistwebsites.com | Brutalist aesthetic |
| Dark Mode Design | https://www.darkmodedesign.com | Dark theme patterns |
| Page Flows | https://pageflows.com | User flow patterns |

### Animation & Motion

| Source | URL | Best For |
|--------|-----|----------|
| CodePen | https://codepen.io | Interactive code snippets |
| Motion One | https://motion.dev/examples | Motion One examples |
| Framer Motion Examples | https://motion.dev/examples | Framer Motion patterns |

---

## Inspiration Workflow

### Step 1: Identify Feature Type

```
Feature Type Decision Tree:

Is this a...?
├── Landing Page → godly.website, land-book.com
├── Portfolio → godly.website, cargo.site
├── SaaS Dashboard → dribbble.com, mobbin.design
├── E-Commerce → awwwards.com, dribbble.com
├── Mobile App → mobbin.design
├── Editorial/Content → readymag.com, awwwards.com
└── Experimental/Art → brutalistwebsites.com, cargo.site
```

### Step 2: Fetch Inspiration

Use WebFetch to gather current trends:

```
Prompt for WebFetch:
"Analyze this page for:
1. Layout patterns (grid, asymmetry, split-screen)
2. Animation techniques (scroll, hover, transitions)
3. Typography choices (size hierarchy, custom fonts)
4. Color schemes (dark/light, gradients, accents)
5. Unique UI patterns that stand out
6. Any 3D or WebGL elements"
```

### Step 3: Extract Patterns

When analyzing inspiration, note:

**Visual Patterns:**
- Hero section treatment
- Navigation style (sticky, hidden, floating)
- Card designs
- Button styles
- Form treatments
- Footer design

**Interaction Patterns:**
- Hover effects
- Scroll animations
- Page transitions
- Loading states
- Micro-interactions

**Technical Patterns:**
- Animation library used (if detectable)
- 3D frameworks
- Scroll libraries
- Custom cursors

### Step 4: Combine & Adapt

```
Combination Strategy:
1. Take layout inspiration from Source A
2. Take animation style from Source B
3. Take color palette from Source C
4. Adapt all to project's tech stack (Next.js, Tailwind, shadcn/ui)
```

---

## Quick Prompts for WebFetch

### For Landing Pages
```
"What makes this landing page effective? Focus on:
- Hero section design
- Value proposition presentation
- Call-to-action placement
- Trust signals and social proof
- Visual hierarchy"
```

### For Portfolios
```
"How does this portfolio showcase work? Focus on:
- Case study presentation
- Navigation between projects
- Use of whitespace
- Typography as design element
- Unique interactive elements"
```

### For SaaS Products
```
"What design patterns does this SaaS use? Focus on:
- Dashboard layout
- Data visualization
- Navigation patterns
- Onboarding elements
- Feature highlighting"
```

### For Creative/Experimental Sites
```
"What experimental techniques does this site use? Focus on:
- Breaking conventions
- Unique interactions
- Scroll behavior
- Loading experiences
- Transitions and animations"
```

---

## Style Categories

### Modern Minimal
- Clean typography
- Lots of whitespace
- Subtle animations
- Monochromatic or limited palette
- Grid-based layouts

### Bold & Playful
- Vibrant colors
- Large typography
- Playful animations
- Irregular layouts
- Custom illustrations

### Premium/Luxury
- Dark themes
- Gold/metallic accents
- Smooth animations
- High-quality imagery
- Elegant typography

### Brutalist
- Raw, unpolished aesthetic
- High contrast
- Bold borders
- Intentionally "ugly"
- System fonts

### 3D/Immersive
- WebGL elements
- Interactive 3D objects
- Parallax scrolling
- Scroll-triggered animations
- Ambient motion

---

## Trend Checklist (2024-2025)

When fetching inspiration, check for these current trends:

**Layout Trends:**
- [ ] Asymmetric grids
- [ ] Split-screen layouts
- [ ] Overlapping elements
- [ ] Bento box grids
- [ ] Floating elements

**Animation Trends:**
- [ ] Scroll-triggered reveals
- [ ] Staggered animations
- [ ] Smooth scrolling (Lenis)
- [ ] Page transitions
- [ ] Micro-interactions on hover

**Visual Trends:**
- [ ] Grain/noise textures
- [ ] Glassmorphism
- [ ] Gradient backgrounds
- [ ] Custom cursors
- [ ] Dark mode default

**Typography Trends:**
- [ ] Variable fonts
- [ ] Large display text
- [ ] Mixed weights
- [ ] Animated text
- [ ] Split-color text

---

## Example: Inspiration to Implementation

### Inspiration Source: godly.website

**What to extract:**
1. Scroll animations with text reveal
2. Asymmetric layout with overlapping sections
3. Custom cursor that changes on hover
4. Dark theme with accent colors

### Implementation Steps:
1. Use Framer Motion for scroll animations
2. Apply Tailwind grid with CSS transforms for overlap
3. Implement custom cursor component
4. Set up dark theme with CSS variables

### Code Mapping:
```
Inspiration Element → Pattern from patterns.md
─────────────────────────────────────────────
Scroll text reveal   → Section 1.5 LineReveal
Asymmetric layout    → Section 3.1 AsymmetricGrid
Custom cursor        → Section 4.1 CustomCursor
Dark theme           → Tailwind dark: classes
```