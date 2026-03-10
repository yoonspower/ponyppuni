# CLAUDE.md — PonyPpuni (포니쁘니)

## Project Overview

PonyPpuni (포니쁘니) is a **static client-side web application** that automatically detects and displays a user's phone model. It identifies Samsung Galaxy devices via User-Agent `SM-` model codes and iPhones via screen resolution combined with iOS version. The UI is in Korean.

## Repository Structure

```
ponyppuni/
├── index.html    # Main application — all HTML, CSS, and JS in one file (287 lines)
├── debug.html    # Debug utility — displays raw UA string and detection flags
├── README.md     # Minimal project readme
└── CLAUDE.md     # This file
```

## Tech Stack

- **Pure HTML5 + vanilla JavaScript (ES5/ES6)** — no frameworks, no build tools, no dependencies
- **Inline CSS** with flexbox, gradients, media queries, mobile-first responsive design
- **No package manager** (no `package.json`, no npm)
- **No build step** — files are served as-is as static assets
- **No tests** — testing is manual via browser
- **No CI/CD pipeline**

## Key Architecture

### Device Detection Logic (`index.html`)

1. **Samsung detection** — regex `/SM-[A-Z0-9]/` against `navigator.userAgent`. The `SM` dictionary (lines 62–162) maps model codes like `"SM-S938"` to Korean display names like `"갤럭시 S25 Ultra"`. The first 7 characters of the code are used as lookup keys.

2. **iPhone detection** — computes physical pixel resolution (`screen.width * devicePixelRatio`) and combines it with the iOS major version to look up the `IP` dictionary (lines 165–202). When multiple models share the same resolution, the user is prompted to pick.

3. **In-app browser detection** — regex for Kakao, Naver, Instagram, Facebook, Line. Shows a warning prompting users to open in a real browser.

4. **Fallback** — non-Samsung Android and desktop/tablet visitors see appropriate warning messages.

### Key Functions

- `makeResult(bgClass, modelName, modelCode, osStr, screenStr)` — builds the result card HTML
- `sel(btn, name)` — handles user selection when multiple iPhone models match

### Debug Page (`debug.html`)

Displays raw User-Agent, SM-code extraction, Samsung Browser flag, and Android detection status. Useful for troubleshooting detection issues on specific devices.

## Development Guidelines

### Code Conventions

- All UI text is in **Korean**
- Code comments are in **Korean**
- CSS class names use short abbreviations (`.rl`, `.rm`, `.rs`, `.ik`, `.iv`, etc.)
- Everything is **inline** within HTML files — no external CSS or JS files
- DOM manipulation uses vanilla `getElementById` and `innerHTML`
- String concatenation for HTML building (no template literals for ES5 compat)

### When Adding New Device Models

- **Samsung**: Add entries to the `SM` dictionary object in `index.html`. Key format is `"SM-XXXX"` (7 chars), value is the Korean display name. Group by series with comment headers.
- **iPhone**: Add entries to the `IP` dictionary. Key format is `"<width>x<height>"` or `"<width>x<height>_<iOS major version>"`. Value is `[minIOS, maxIOS, [array of model names]]`.

### Styling

- Samsung result cards use `.samsung-bg` (blue gradient: `#1428A0` → `#0B52CE`)
- Apple result cards use `.apple-bg` (dark gradient: `#1c1c1e` → `#48484a`)
- Page background is a purple gradient (`#1a1a6e` → `#c850c0`)
- Main card has `max-width: 400px` with `border-radius: 28px`

### Deployment

This is a static site. Deploy by copying `index.html` and `debug.html` to any web server or static hosting service (GitHub Pages, Netlify, Vercel, etc.). No build step required.

## Git Conventions

- Primary branch: `master` (remote has `main`)
- Commit messages have been simple and descriptive
- All commits by a single author
