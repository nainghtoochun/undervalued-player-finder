# Web frontend

React + TypeScript + Vite + Tailwind + Recharts. Three pages: Home, Explorer and a page per player, plus Method.

The site reads JSON files from `public/data/`, written by `python -m pipeline.export_web`.
So it needs no server and loads instantly on GitHub Pages.

## Run it

```bash
cd web
npm install        # first time only
npm run dev        # http://localhost:5173
```

## Build

```bash
npm run build      # type checks, then writes dist/
npm run preview    # serve dist/ locally
```

GitHub Actions builds and publishes the site on every push to `main` (see `.github/workflows/deploy.yml`).
