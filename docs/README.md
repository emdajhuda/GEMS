# GEMS documentation

- [installation.md](installation.md) — full installation guide (Rubin Science
  Platform and local options) and troubleshooting.
- [architecture.md](architecture.md) — diagram and explanation of how the
  sub-packages fit together, from Butler exposures to diagnostic plots.
- [api_reference.md](api_reference.md) — index of the public API re-exported from
  the top-level `gems` package.
- [science/](science/) — the scientific method behind GEMS; the seed for a future,
  fuller scientific description and companion article (see [`../paper/`](../paper/)).

Rendered assets (banner/logo images) used by the top-level [README](../README.md)
live in [assets/](assets/).

This is currently a set of plain Markdown pages, rendered directly by GitHub. If the
project grows a generated API reference later (e.g. Sphinx autodoc/autosummary or
mkdocstrings), it can be added under this same `docs/` directory without disturbing
these pages.
