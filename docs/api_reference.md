# API reference (overview)

This is a hand-written index of the public API re-exported from the top-level
`ocote` package (`import ocote as oc`), grouped by the sub-package that defines it. It
mirrors `ocote.__all__`. A generated, per-function reference (e.g. via Sphinx
autodoc/autosummary or `mkdocstrings`) can be added under `docs/` later; see
[docs/architecture.md](architecture.md) for how these pieces fit together.

| Group | Names | Defined in |
|---|---|---|
| Butler | `ExpButler` | `ocote.utils.butler.butler` |
| Local Butler | `LocalButler`, `log_menseger`, `create_empty_repo`, `instrument_register_from_remote`, `register_datasetTypes`, `skymap_register_from_remote`, `discover_datasets`, `transfer_dataset`, `ensure_chained_collection` | `ocote.utils.butler.local_butler` |
| Coadd | `custom_coadd_filter`, `custom_coadd_multiband`, `load_custom_coadd_from_file` | `ocote.coaddmaker.custom_coadd` |
| Coadd validation / injection pipeline | `coadd_exposures_pipeline`, `leave_one_out_residual`, `validate_rotation` | `ocote.coaddmaker.custom_inject_coadd` |
| Warp | `custom_warp`, `select_visits`, `runDirectWarpTask`, `ensure_directWarp_datasetType`, `setup_run_and_chain` | `ocote.utils.warp.custom_warp` |
| Exposure | `load_exposures`, `save_exposure`, `normalize_exposures`, `exposure_to_fits_datahdr`, `cutout_exposure` | `ocote.shortcuts.exposure_sh.exposure_sh` |
| Visit | `VisitSH`, `combine_visits_selected`, `visit_dataset` | `ocote.shortcuts.visit_sh.visit_sh` |
| Fits | `fits_to_exposure`, `cutout_fits` | `ocote.utils.fits.fits` |
| Plot configuration | `general`, `FigParam`, `LineParam`, `axesParam`, `labelParam`, `legendParam`, `fontParam`, `get_colors` | `ocote.utils.plot.plot_conf` |
| Statistics plots | `StatisticsPlots` | `ocote.utils.plot.statistics_plot` |
| Array plots | `pixel_intensity` | `ocote.utils.plot.array_plot` |
| Butler plots | `filt_plot`, `display_ccds_and_cutout`, `plot_compare` | `ocote.utils.plot.butler_plot` |
| Coadd plots | `plot_custom_coadd`, `plot_original_coadd`, `normalize_image`, `make_rgb_image`, `compare_rgb_coadds` | `ocote.utils.plot.coadd_plot` |
| Exposure plots | `fix_wcsaxes_labels`, `extract_array`, `normalize_axes`, `render_image`, `overlay_sky_point`, `plot_histogram`, `injection_steps`, `plot_exposures_full` | `ocote.utils.plot.exposure_plot` |
| Sky | `tract_patch`, `patch_center`, `get_patch_center_radius`, `RA_to_degree`, `Dec_to_degree`, `skywcs_to_astropy` | `ocote.utils.sky.sky` |
| Injection | `make_serializable`, `measure_quality`, `create_crowded_injection_catalog`, `apply_correction_from_data`, `apply_correction_to_stamp`, `inject_stamp`, `main_inject_stamp`, `apply_correction_from_exposureF`, `save_visit_images` | `ocote.coherentinjection.injection` |
| Tools | `progressbar`, `setup_logger`, `_run`, `get_butler_location`, `mjds_to_dates`, `diff_AlardLupton`, `warp_img` | `ocote.utils.tools.tools` |

All of the above are importable directly from the top level, e.g.:

```python
import ocote as oc
eb = oc.ExpButler(repository="dp1", collections="LSSTComCam/DP1")
```

or from their defining sub-module, e.g. `from ocote.utils.sky.sky import tract_patch`.
