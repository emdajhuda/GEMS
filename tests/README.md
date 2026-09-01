# Tests

No automated tests exist yet. This directory is scaffolding so they can be added
coherently, mirroring the layout of [`py/gems/`](../py/gems/), e.g.:

```
tests/
├── coaddmaker/
│   ├── test_custom_coadd.py
│   └── test_custom_inject_coadd.py
├── coherentinjection/
│   └── test_injection.py
├── py/
│   ├── test_exposure.py
│   └── test_visit_selection.py
└── utils/
    ├── test_butler.py
    ├── test_fits.py
    ├── test_plot.py
    ├── test_sky.py
    ├── test_tools.py
    └── test_warp.py
```

Most of this package's functions call into the LSST Science Pipelines (`lsst.daf.butler`,
`lsst.afw`, ...), so tests will generally need either a small local Butler repository
fixture (see `gems.LocalButler`) or mocks around the `lsst.*` calls. A suggested,
not-yet-wired starting point once tests exist:

```bash
pip install -e ".[test]"   # after adding a `test` extra (e.g. pytest) to pyproject.toml
pytest
```
