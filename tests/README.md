# Tests

No automated tests exist yet. This directory is scaffolding so they can be added
coherently, mirroring the layout of [`src/ocote/`](../src/ocote/), e.g.:

```
tests/
├── coaddmaker/
│   ├── test_custom_coadd.py
│   └── test_custom_inject_coadd.py
├── coherentinjection/
│   └── test_injection.py
├── shortcuts/
│   ├── test_exposure_sh.py
│   └── test_visit_sh.py
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
fixture (see `ocote.LocalButler`) or mocks around the `lsst.*` calls. A suggested,
not-yet-wired starting point once tests exist:

```bash
pip install -e ".[test]"   # after adding a `test` extra (e.g. pytest) to pyproject.toml
pytest
```
