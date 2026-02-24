# Frontend Implementation Checklist

Before marking frontend as complete:

## shadcn/ui
- [ ] Checked shadcn/ui for EVERY UI component needed
- [ ] No custom duplicates of shadcn components created
- [ ] Missing shadcn components installed via `npx shadcn@latest add`

## Existing Code
- [ ] Checked existing project components via `git ls-files src/components/`
- [ ] Reused existing components where possible

## Design
- [ ] Design preferences clarified with user (if no mockups)
- [ ] Component architecture from Solution Architect followed

## Creative Mode (if Creative/Premium/Experimental)
- [ ] Style mode selected (Standard/Creative/Premium/Experimental)
- [ ] Inspiration sources checked (godly.website, awwwards.com, etc.)
- [ ] Appropriate patterns from patterns.md applied
- [ ] Dependencies installed for selected mode:
  - Creative: framer-motion, lenis
  - Premium: + three, @react-three/fiber, @react-three/drei

### Animation Checklist (Creative+)
- [ ] Scroll animations implemented where appropriate
- [ ] Hover effects enhance interactivity
- [ ] Page transitions smooth (if multi-page)
- [ ] Animation performance acceptable (60fps)

### 3D Checklist (Premium+)
- [ ] 3D scene initializes without errors
- [ ] Interactive elements respond to mouse
- [ ] Performance acceptable (monitor FPS)
- [ ] Fallback for low-performance devices

### Micro-Interactions Checklist (Creative+)
- [ ] Custom cursor (if implemented) works correctly
- [ ] Smooth scroll enabled and functional
- [ ] Magnetic effects work as expected
- [ ] All interactions are optional (don't break UX)

## Implementation
- [ ] All planned components implemented
- [ ] All components use Tailwind CSS (no inline styles, no CSS modules)
- [ ] Loading states implemented (spinner/skeleton during data fetches)
- [ ] Error states implemented (user-friendly error messages)
- [ ] Empty states implemented ("No data yet" messages)

## Quality
- [ ] Responsive: Mobile (375px), Tablet (768px), Desktop (1440px)
- [ ] Accessibility: Semantic HTML, ARIA labels, keyboard navigation
- [ ] TypeScript: No errors (`npm run build` passes)
- [ ] ESLint: No warnings (`npm run lint`)

## Verification (run before marking complete)
- [ ] `npm run build` passes without errors
- [ ] All acceptance criteria from feature spec addressed in UI
- [ ] `features/INDEX.md` status updated to "In Progress"

## Completion
- [ ] User has reviewed and approved the UI in browser
- [ ] Code committed to git
