# Max Wels — Personal Website

A premium, dark, atmospheric personal website built with Astro, TypeScript, and Tailwind CSS v4. Designed for static hosting.

## Quick Start

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Tech Stack

- **Astro v6** — static site generator
- **TypeScript** — type safety
- **Tailwind CSS v4** — utility-first styling via `@tailwindcss/vite`
- **Google Fonts** — Space Grotesk, Inter, JetBrains Mono

## Project Structure

```
src/
├── components/       # Reusable Astro components
│   ├── Nav.astro             # Sticky nav with mobile menu
│   ├── Footer.astro          # Site footer
│   ├── Hero.astro            # Homepage hero section
│   ├── Section.astro         # Reusable section wrapper
│   ├── ProjectCard.astro     # Project showcase card
│   ├── SkillCard.astro       # Skill area card
│   ├── LifeCard.astro        # Life interest card
│   ├── SocialLinks.astro     # Social link icons
│   ├── QuoteBlock.astro      # Statement/quote block
│   ├── CurrentFocusList.astro # Focus items list
│   └── MediaGalleryStrip.astro # Horizontal image gallery
├── content/          # Content collections (Markdown)
│   ├── config.ts             # Collection schemas (Zod)
│   └── projects/             # Project entries
├── data/
│   └── site.ts               # Centralized site config & content
├── layouts/
│   └── BaseLayout.astro      # HTML document wrapper
├── pages/            # Route pages
│   ├── index.astro           # Homepage
│   ├── projects.astro        # Projects listing
│   ├── about.astro           # About page
│   ├── life.astro            # Life/interests page
│   └── connect.astro         # Contact page
├── styles/
│   └── global.css            # Design system & global styles
public/
├── favicon.svg
├── robots.txt
└── images/           # Place your images here
```

## Content Editing

### Site Config (`src/data/site.ts`)
Edit brand info, tagline, social links, skills, life cards, and current focus items.

### Projects (`src/content/projects/`)
Add/edit Markdown files. Each needs frontmatter:
```yaml
---
title: "Project Name"
description: "Short description"
tags: ["Tag1", "Tag2"]
image: "/images/project-screenshot.jpg"
featured: true
order: 1
---

Markdown body content here.
```

### Social Links
Update URLs in `src/data/site.ts` → `socialLinks` array.

## Placeholder Replacements

Replace these files in `public/images/`:

| Placeholder | Purpose | Recommended Size |
|---|---|---|
| `portrait-placeholder.jpg` | Main portrait photo | 800×1067px (3:4) |
| `travel-placeholder.jpg` | Travel photography | 1200×800px |
| `fitness-placeholder.jpg` | Fitness/training photo | 1200×800px |
| `mood-placeholder.jpg` | Atmospheric mood image | 1200×800px |
| `project-placeholder.jpg` | Project screenshot | 1200×800px |
| `og-image.jpg` | Open Graph share image | 1200×630px |

## Deployment

### Build

```bash
npm run build
```

Output goes to `./dist/` — pure static HTML, CSS, JS.

### Deploy to VPS with Caddy

1. Upload `dist/` contents to your server (e.g., `/var/www/maxwels.com/`)

2. Caddy config (`Caddyfile`):
```
maxwels.com {
    root * /var/www/maxwels.com
    file_server
    encode gzip zstd

    # SPA-style fallback (optional)
    try_files {path} {path}.html {path}/index.html

    # Cache static assets
    @static path *.css *.js *.svg *.jpg *.png *.webp *.woff2
    header @static Cache-Control "public, max-age=31536000, immutable"

    # Security headers
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

3. Reload Caddy:
```bash
sudo systemctl reload caddy
```

### Alternative: Nginx

```nginx
server {
    listen 80;
    server_name maxwels.com;
    root /var/www/maxwels.com;
    index index.html;

    location / {
        try_files $uri $uri.html $uri/ =404;
    }

    location ~* \.(css|js|svg|jpg|png|webp|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    gzip on;
    gzip_types text/css application/javascript image/svg+xml;
}
```

## Design System

- **Colors**: Black (#0a0a0a) base, neon green (#39ff14) accent, purple (#8b5cf6) secondary accent
- **Fonts**: Space Grotesk (display), Inter (body), JetBrains Mono (mono)
- **Animations**: CSS-only scroll reveals via IntersectionObserver, hover glow effects
- **Theme**: Dark only (v1)

## License

Private — all rights reserved.
