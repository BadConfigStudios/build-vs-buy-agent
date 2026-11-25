# Vendored dependencies

- `marked.min.js`: marked 12.0.2, MIT license (`LICENSE-marked.md`).
  Source: https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js
  sha256: 15fabce5b65898b32b03f5ed25e9f891a729ad4c0d6d877110a7744aa847a894
  Pinned exactly. `build_html.py` overrides `renderer.html` and `renderer.link` using the 12.x signatures; re-check those overrides before bumping.
