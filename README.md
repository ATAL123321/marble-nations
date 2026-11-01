# Marble Nations

Automated 3D country marble race Shorts (1080x1920).

- `app/` – three.js + cannon-es race page (procedural level per seed, 2 or 4 countries, 17 themes)
- `render.js` – finds a clean seed, renders frames, synthesizes SFX, mixes music that ducks under SFX
- `music/` – background tracks (YouTube Audio Library)
- `.github/workflows/render.yml` – `workflow_dispatch` render job, triggered by n8n

n8n adds the voice lines and uploads to YouTube.
