# Architecture & data flow

This diagram shows how the sub-packages under [`py/gems/`](../py/gems/) fit
together, from raw Butler exposures to diagnostic plots. It reflects the actual
import relationships between modules (see the package docstrings for per-function
details).

```mermaid
flowchart TD
    A["LSST Butler\n(remote repository, e.g. LSSTComCam/DP1)"] -->|"ExpButler / LocalButler\ngems.utils.butler"| B["Local Butler repository"]

    subgraph Select["Visit & exposure selection — gems.py"]
        C["VisitSL / combine_visits_selected\nvisit_selection"]
        D["load_exposures / save_exposure\nexposure"]
    end
    B --> C
    B --> D

    subgraph Core["Core processing"]
        E["custom_coadd_filter / custom_coadd_multiband\ngems.coaddmaker.custom_coadd"]
        F["coadd_exposures_pipeline\nleave_one_out_residual / validate_rotation\ngems.coaddmaker.custom_inject_coadd"]
        G["inject_stamp / main_inject_stamp\ngems.coherentinjection.injection"]
        H["custom_warp / select_visits\ngems.utils.warp"]
    end
    C --> E
    E --> F
    D --> G
    C --> G
    C --> H

    subgraph Support["Shared support utilities"]
        S1["gems.utils.sky\nWCS / sky-coordinate math"]
        S2["gems.utils.fits\nFITS <-> Exposure conversion"]
        S3["gems.utils.tools\nlogging, progress, misc helpers"]
    end
    C -.-> S1
    E -.-> S1
    G -.-> S1
    D -.-> S3
    E -.-> S3
    H -.-> S3
    D -.-> S2

    subgraph Diagnostics["Diagnostics & plotting — gems.utils.plot"]
        I["StatisticsPlots"]
        J["plot_custom_coadd / plot_original_coadd"]
        K["render_image / injection_steps / plot_exposures_full"]
    end
    A --> I
    E --> J
    F --> J
    G --> K
```

## Layers

1. **Data access** (`gems.utils.butler`) — `ExpButler` wraps a remote LSST `Butler`;
   `LocalButler` creates and populates a local Butler repository by transferring
   datasets from a remote one, so later steps can run against local data.

2. **Selection helpers** (`gems.py`) — `visit_selection` selects visits by sky
   position/tract-patch and combines them (`VisitSL`); `exposure` loads, saves,
   normalizes, and cuts out exposures.

3. **Core processing**:
   - `gems.coaddmaker` builds custom, filter-aware coadds from a selected set of
     visits (`custom_coadd`), then runs injection-aware coadd pipelines and validation
     (leave-one-out residuals, rotation checks) in `custom_inject_coadd`.
   - `gems.coherentinjection` injects synthetic strong-lensing sources into exposures
     (via `lsst.source.injection`) to test recovery/detectability.
   - `gems.utils.warp` re-projects ("warps") exposures onto a common sky grid ahead of
     coaddition.

4. **Diagnostics** (`gems.utils.plot`) — turns the outputs of the layers above into
   figures: PSF/airmass statistics (`statistics_plot`), coadd comparisons
   (`coadd_plot`), exposure/injection visualizations (`exposure_plot`), and general
   array/Butler plots (`array_plot`, `butler_plot`).

Cutting across all of the above, `gems.utils.sky` (WCS and sky-coordinate math),
`gems.utils.fits` (FITS <-> `Exposure` conversion), and `gems.utils.tools` (logging,
progress bars, misc helpers) provide shared functionality used by several layers.

See [`examples/`](../examples/) for notebooks that walk through this pipeline
end-to-end, and [README.md](../README.md#project-layout) for the repository layout.
