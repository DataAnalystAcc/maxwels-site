# 9elements Hero Animation — Reverse Engineering Notes

## Source: https://9elements.com/de/

### Composition
Multi-layered hero filling the viewport:
1. **Background**: Dark gradient (#0a0a0e base) with noise/grain texture overlay
2. **Floating 3D objects**: PNG keyboard keys with varying blur (depth of field), positioned with `transform: translate3d()` and driven by mouse position via CSS custom properties
3. **Neon gradient frame**: Cyan-to-blue rounded rectangle, acts as a framing device for the central hand image
4. **Central visual**: Monochrome hand photograph (rock gesture), partially overlapping the frame
5. **Typography mask**: "TECHNOLOGY & DESIGN" in brush script, large, overlapping multiple layers
6. **Horizontal glitch lines**: Animated across the hero for tech noise effect
7. **Rotating badge**: "OPEN FOR BUSINESS" in a circular text badge, rotates continuously

### Technology
- **Parallax**: CSS custom properties (`--mouse-x`, `--mouse-y`) updated by JS on `mousemove`, consumed by `transform: translate()` on each layer with different multipliers
- **Intro animation**: CSS keyframes with staggered delays — layers scale/fade in from bottom, typography clip-paths from center
- **Idle state**: Slow floating oscillation via `@keyframes`, badge rotation, subtle glitch lines
- **No heavy libraries**: No GSAP, no canvas. Pure CSS animations + lightweight vanilla JS for mouse tracking
- **Performance**: All animated properties are transforms and opacity (GPU composited)

### Timing
- Intro: ~1.5s total, staggered 0.1–0.3s between layers
- Easing: `cubic-bezier(0.16, 1, 0.3, 1)` (aggressive ease-out)
- Idle rotation: 120s linear (full turn)
- Mouse parallax: lerped with ~0.05 factor for smooth follow

### Responsive
- On mobile: floating objects scale down, fewer visible
- Frame and hand centralize
- Typography scales via `clamp()`
- Mouse parallax disabled (no hover on touch)

### What was adapted for Blank II
- Multi-layer composition principle → applied to SVG rings + monogram
- Mouse-driven parallax via CSS vars → same technique, different layers
- Staggered intro → applied to text, rings, fragments, glow
- Idle rotation → applied to outer/inner rings
- Noise/grain texture → same approach, SVG filter background
- Glitch lines → adapted as scanline overlay
- Premium easing → same cubic-bezier curve
- Performance approach → transforms/opacity only, IntersectionObserver for offscreen pause
