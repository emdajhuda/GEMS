# verarubin/__init__.py

#CoaddMaker

from .CoaddMaker.custom_coadd import custom_coadd_filter, custom_coadd_multiband, load_custom_coadd_from_file
from .CoaddMaker.custom_inject_coadd import coadd_exposures_pipeline, coadd_exposures_pipeline, leave_one_out_residual, validate_rotation

#CoherentInjection
from .CoherentInjection.injection import make_serializable, measure_quality, create_crowded_injection_catalog, apply_correction_from_data,\
                                       apply_correction_to_stamp, inject_stamp, main_inject_stamp, apply_correction_from_exposureF,\
                                       save_visit_images

#Shortcuts
# exposure
from .Shortcuts.exposure_sh.exposure_sh import load_exposures, save_exposure, normalize_exposures, exposure_to_fits_datahdr, cutout_exposure
# Visit
from .Shortcuts.visit_sh.visit_sh import VisitSH, combine_visits_selected, visit_dataset

#Utils
# Butler
from .Utils.butler.butler import ExpButler
from .Utils.butler.local_butler import LocalButler, log_menseger, create_empty_repo, instrument_register_from_remote,\
                                  register_datasetTypes, skymap_register_from_remote,\
                                  discover_datasets, transfer_dataset, ensure_chained_collection
# Warp
from .Utils.warp.custom_warp import custom_warp, select_visits, runDirectWarpTask, ensure_directWarp_datasetType, setup_run_and_chain
# Fits
from .Utilsfits.fits import fits_to_exposure, cutout_fits
# Plot
from .Utils.plot.plot_conf import general, FigParam, LineParam, axesParam, labelParam, legendParam, fontParam, get_colors
from .Utils.plot.statistics_plot import StatisticsPlots
from .Utils.plot.array_plot import pixel_intensity
from .Utils.plot.butler_plot import filt_plot, display_ccds_and_cutout, plot_compare
from .Utils.plot.coadd_plot import plot_custom_coadd, plot_original_coadd, normalize_image, make_rgb_image, compare_rgb_coadds
from .Utils.plot.exposure_plot import fix_wcsaxes_labels, extract_array, normalize_axes, render_image, overlay_sky_point,\
    plot_histogram, injection_steps, plot_exposures_full
# Tools
from .Utils.tools.tools import progressbar, setup_logger, _run, get_butler_location, mjds_to_dates, diff_AlardLupton, warp_img
# Sky
from .Utils.sky.sky import tract_patch, patch_center, get_patch_center_radius, RA_to_degree, Dec_to_degree, skywcs_to_astropy


__all__ = [
    # ExpButler
    'ExpButler', 
    'LocalButler', 'log_menseger', 'create_empty_repo','instrument_register_from_remote', 'register_datasetTypes', 'skymap_register_from_remote',
    'discover_datasets', 'transfer_dataset', 'ensure_chained_collection',
    # Coadd
    'custom_coadd_filter', 'custom_coadd_multiband', 'load_custom_coadd_from_file',
    'coadd_exposures_pipeline', 'leave_one_out_residual', 'validate_rotation',
    # Warp
    'custom_warp', 'select_visits', 'runDirectWarpTask', 'ensure_directWarp_datasetType',
    'setup_run_and_chain',
    # Exposure
    'load_exposures', 'save_exposure', 'normalize_exposures', 'exposure_to_fits_datahdr', 'cutout_exposure',
    # Fits
    'fits_to_exposure', 'cutout_fits',
    # Plots
    'general', 'FigParam', 'LineParam', 'axesParam', 'labelParam', 'legendParam', 'fontParam', 'get_colors', 'StatisticsPlots',
    'pixel_intensity', 'filt_plot', 'display_ccds_and_cutout', 'plot_compare', 'plot_custom_coadd', 'plot_original_coadd',
    'normalize_image', 'make_rgb_image', 'compare_rgb_coadds', 'fix_wcsaxes_labels', 'extract_array', 'normalize_axes', 'render_image',
    'overlay_sky_point', 'plot_histogram', 'injection_steps', 'plot_exposures_full',
    # Sky
    'tract_patch', 'patch_center', 'get_patch_center_radius', 'RA_to_degree', 'Dec_to_degree', 'skywcs_to_astropy',
    # Injection
    'make_serializable', 'measure_quality', 'create_crowded_injection_catalog', 'apply_correction_from_data',
    'apply_correction_to_stamp', 'inject_stamp', 'main_inject_stamp', 'apply_correction_from_exposureF', 'save_visit_images',
    # Tools
    'progressbar', 'setup_logger', '_run', 'get_butler_location', 'mjds_to_dates', 'diff_AlardLupton', 'warp_img',
    # Visit
    'Visit', 'combine_visits_selected', 'visit_dataset'
]