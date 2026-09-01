# API reference (overview)

This is a hand-written index of the public API re-exported from the top-level
`gems` package (`import gems`), grouped by the sub-package that defines it. It
mirrors `gems.__all__`. A generated, per-function reference (e.g. via Sphinx
autodoc/autosummary or `mkdocstrings`) can be added under `docs/` later; see
[docs/architecture.md](architecture.md) for how these pieces fit together.

| Group | Names | Defined in |
|---|---|---|
| Butler | `ExpButler` | `gems.utils.butler.butler` |
| Local Butler | `LocalButler`, `log_menseger`, `create_empty_repo`, `instrument_register_from_remote`, `register_datasetTypes`, `skymap_register_from_remote`, `discover_datasets`, `transfer_dataset`, `ensure_chained_collection` | `gems.utils.butler.local_butler` |
| Coadd | `custom_coadd_filter`, `custom_coadd_multiband`, `load_custom_coadd_from_file` | `gems.coaddmaker.custom_coadd` |
| Coadd validation / injection pipeline | `coadd_exposures_pipeline`, `leave_one_out_residual`, `validate_rotation` | `gems.coaddmaker.custom_inject_coadd` |
| Warp | `custom_warp`, `select_visits`, `runDirectWarpTask`, `ensure_directWarp_datasetType`, `setup_run_and_chain` | `gems.utils.warp.custom_warp` |
| Exposure | `load_exposures`, `save_exposure`, `normalize_exposures`, `exposure_to_fits_datahdr`, `cutout_exposure` | `gems.py.exposure.exposure` |
| Visit | `VisitSL`, `combine_visits_selected`, `visit_dataset` | `gems.py.visit_selection.visit_selection` |
| Fits | `fits_to_exposure`, `cutout_fits` | `gems.utils.fits.fits` |
| Plot configuration | `general`, `FigParam`, `LineParam`, `axesParam`, `labelParam`, `legendParam`, `fontParam`, `get_colors` | `gems.utils.plot.plot_conf` |
| Statistics plots | `StatisticsPlots` | `gems.utils.plot.statistics_plot` |
| Array plots | `pixel_intensity` | `gems.utils.plot.array_plot` |
| Butler plots | `filt_plot`, `display_ccds_and_cutout`, `plot_compare` | `gems.utils.plot.butler_plot` |
| Coadd plots | `plot_custom_coadd`, `plot_original_coadd`, `normalize_image`, `make_rgb_image`, `compare_rgb_coadds` | `gems.utils.plot.coadd_plot` |
| Exposure plots | `fix_wcsaxes_labels`, `extract_array`, `normalize_axes`, `render_image`, `overlay_sky_point`, `plot_histogram`, `injection_steps`, `plot_exposures_full` | `gems.utils.plot.exposure_plot` |
| Sky | `tract_patch`, `patch_center`, `get_patch_center_radius`, `RA_to_degree`, `Dec_to_degree`, `skywcs_to_astropy` | `gems.utils.sky.sky` |
| Injection | `make_serializable`, `measure_quality`, `create_crowded_injection_catalog`, `apply_correction_from_data`, `apply_correction_to_stamp`, `inject_stamp`, `main_inject_stamp`, `apply_correction_from_exposureF`, `save_visit_images` | `gems.coherentinjection.injection` |
| Tools | `progressbar`, `setup_logger`, `_run`, `get_butler_location`, `mjds_to_dates`, `diff_AlardLupton`, `warp_img` | `gems.utils.tools.tools` |

All of the above are importable directly from the top level, e.g.:

```python
import gems
eb = gems.ExpButler(repository="dp1", collections="LSSTComCam/DP1")
```

or from their defining sub-module, e.g. `from gems.utils.sky.sky import tract_patch`.
