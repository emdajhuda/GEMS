# Installation

GEMS is a normal, `pip`-installable Python package — published on PyPI as
[`gems-astro`](https://pypi.org/project/gems-astro/) (import it as `import gems`) —
but most of its functionality depends on the **LSST Science Pipelines** (imported as
`lsst.*`), which are distributed outside of PyPI. Pick one of the two paths below
depending on where you plan to run it.

## Option A — Rubin Science Platform (recommended)

The [Rubin Science Platform](https://data.lsst.cloud/) (RSP) provides a JupyterLab
environment with the LSST Science Pipelines already installed, so you only need to
install GEMS itself:

1. Log in to the RSP and open a terminal from JupyterLab.
2. Install GEMS, either:

   - **from PyPI** (published as `gems-astro`; simplest if you just want the library):

     ```bash
     pip install gems-astro
     ```

   - **from source** (if you also want the example notebooks, or plan to edit the code):

     ```bash
     git clone https://github.com/emdajhuda/GEMS.git gems
     cd gems
     pip install -e .
     ```

3. Restart the notebook kernel so it picks up the newly installed package, then:

   ```python
   import gems
   ```

## Option B — Local installation

1. **Install the LSST Science Pipelines.** Follow the official
   [installation guide](https://pipelines.lsst.io/install/index.html) (conda-based), or
   use one of the LSST-maintained `sciplat-lab` container images. This step provides the
   `lsst.*` modules and is independent of GEMS.

2. **Activate the LSST environment** (typically via `source loadLSST.bash` and
   `setup lsst_distrib`, per the guide above), so that `python -c "import lsst.daf.butler"`
   succeeds.

3. **Install GEMS** into that same environment, either:

   - **from PyPI** (published as `gems-astro`; simplest if you just want the library):

     ```bash
     pip install gems-astro
     ```

   - **from source** (if you also want the example notebooks, or plan to edit the code):

     ```bash
     git clone https://github.com/emdajhuda/GEMS.git gems
     cd gems
     pip install -e .
     ```

   Either way this installs GEMS's own Python dependencies (NumPy, Matplotlib, Astropy,
   pandas, cycler) automatically; the LSST stack from step 1 is used as-is.
```

## Requirements

- Python >= 3.10
- The LSST Science Pipelines (`lsst.daf.butler`, `lsst.afw`, `lsst.geom`,
  `lsst.pipe.base`, `lsst.pipe.tasks`, `lsst.drp.tasks`, `lsst.skymap`,
  `lsst.source.injection`, `lsst.utils`)
- Access to an LSST Butler repository (remote, e.g. `LSSTComCam/DP1` on the RSP, or a
  local one created with `gems.LocalButler`)

## Troubleshooting

- **`ModuleNotFoundError: No module named 'lsst'`** — the LSST Science Pipelines are not
  installed or not activated in your current environment; see Option B, steps 1-2.
- **`ImportError` when running `import gems`** — double check you installed GEMS
  (`pip install gems-astro`, or `pip install -e .` from the repository root — the
  directory containing `pyproject.toml`), and that you're using the same Python/kernel
  you installed into.
- **Butler authentication/connection errors** — these come from the LSST Butler client
  itself, not from GEMS; see the
  [Butler documentation](https://pipelines.lsst.io/modules/lsst.daf.butler/index.html)
  and confirm you have access to the collection you're querying.
