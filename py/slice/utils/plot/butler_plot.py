# v1.0
# plots/butler_plot.py
# set of functions that plot butler information

import matplotlib.pyplot as plt
import numpy as np
import os, sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from .coadd_plot import plot_original_coadd, plot_custom_coadd

###################################################################################################
def filt_plot(df_metrics, visits_selected, filt_cut_select, incr=1000,
              xysc=('id_plot', 'psfSigma_mean', 'psfSigma_std', 'airmass'),
              cmap='viridis', alpha=0.2, ec='red', linewidths=1.5, save=False):
    """
    Plot PSF, id and airmass give a filter data for the mean and std PSF and an airmass upperbound

    Parameters
    ----------
    df_metrics : Data Frame which columns correspond to:
                'id_plot', 'psfSigma_mean', 'psfSigma_std', 'airmass', ...
    visits_selected : Data Frame containing the selected visits
    filt_cut_select : Dictionary containing filter cut values for the plot
    incr : Increment value for marker size
    xysc : Tuple containing the names of the columns to be plotted on the x and y axes
    cmap : Colormap to be used for the scatter plot
    alpha : Alpha value for the scatter plot markers
    ec : Edge color for the scatter plot markers
    linewidths : Linewidths for the scatter plot markers
    save : Boolean or string indicating whether to save the plot
    """
    xticklabels = df_metrics["visit_id"]
    my_filter = df_metrics["band"].unique()
    size_visit = 8 if my_filter[0] in list('ugz') else 5
    
    fig, ax = plt.subplots(figsize=(15, 5))

    # Full visit
    x, y, s, c = [df_metrics[name] for name in xysc]
    sc = ax.scatter(x, y, s=s*incr, c=c, cmap=cmap, alpha=alpha)
    cbar = plt.colorbar(sc, ax=ax, label='airmass')

    # Select_visit
    x, y, s, c = [visits_selected[name] for name in xysc]
    ax.scatter(x, y, s=s*incr, fc='none', linewidths=linewidths, ec=ec) 

    xc, yc, s_c, cc = [filt_cut_select.get(name, None) for name in xysc]
    if yc:
        yc = float(yc.strip().split()[-1])
        ax.axhline(y=yc, lw=3, ls='--', color='k', alpha=0.5)
    if cc:
        cc = float(cc.strip().split()[-1])
        # norm = sc.norm(cc)
        # cbar.ax.hlines(norm, *cbar.ax.get_xlim(), color='red', linewidth=2)
        cbar.ax.hlines(cc, *cbar.ax.get_xlim(), color='red', linewidth=2)
    if s_c:
        pass

    ax.set_xticks(range(len(df_metrics)))
    ax.tick_params(axis='y', which='major', labelsize=12)
    ax.tick_params(axis='x', which='major', labelsize=size_visit)

    ax.set_xticklabels(xticklabels, rotation = 90)
    ax.set_xlabel('Visit ID', fontsize=14)
    ax.set_ylabel('PSF size', fontsize=14)

    ax.set_xlim(0, len(df_metrics))

    fig.suptitle(my_filter[0] + " band", fontsize=16)

    # Save output
    if save:
        filename = save if isinstance(save, str) else 'filt_output.pdf'
        fig.savefig(
            filename, format='pdf', metadata=None,
            pad_inches=0.1, dpi=1000,
            bbox_inches='tight'
            )
        
    plt.show()
    return None

######### Display CCDs and cutout region
def display_ccds_and_cutout(butler, my_tract, my_patch, skymap_name='lsst_cells_v1'):
    """
    Display the CCDs and cutout region for a given tract and patch.
    """
    # Get the skymap
    skymap = butler.get_dataset('skymap', skymap_name)

    # Get the CCDs for the specified tract and patch
    ccds = skymap.get_ccds(tract=my_tract, patch=my_patch)

    # Plot the CCDs
    fig, ax = plt.subplots(figsize=(10, 10))
    for ccd in ccds:
        ax.add_patch(plt.Rectangle((ccd.x0, ccd.y0), ccd.width, ccd.height,
                                     edgecolor='red', facecolor='none'))
    ax.set_title(f"CCDs for Tract {my_tract}, Patch {my_patch}")
    plt.show()

def plot_compare(butler=None, my_tract=None, my_patch=None,
                 custom_coadd=None, bands_to_plot=None, skymap_name='lsst_cells_v1',
                 algorithm='asinh', min='zscale', max=None, unit=None):
    """
    Compare original and custom coadds for the same bands.
    see: https://pipelines.lsst.io/modules/lsst.afw.display/index.html
    """
    if bands_to_plot is None:
        if custom_coadd:
            bands_to_plot = list(custom_coadd.keys())
        else:
            print("Warning: No bands specified.")
            return None
    elif isinstance(bands_to_plot, str):
        bands_to_plot = list(bands_to_plot)

    ncols = len(bands_to_plot)

    # Caso: Original + Custom
    if butler and custom_coadd:
        fig, axes = plt.subplots(nrows=2, ncols=ncols, figsize=(5*ncols, 8))
        axes = np.atleast_2d(axes)
        plot_original_coadd(fig, axes[0], butler, my_tract, my_patch, bands_to_plot, skymap_name, algorithm, min, max, unit)
        plot_custom_coadd(fig, axes[1], custom_coadd, bands_to_plot, algorithm, min, max, unit)
    # Only Original
    elif butler and not custom_coadd:
        fig, axes = plt.subplots(nrows=1, ncols=ncols, figsize=(5*ncols, 4))
        plot_original_coadd(fig, axes, butler, my_tract, my_patch, bands_to_plot, skymap_name, algorithm, min, max, unit)
    # Only Custom
    elif custom_coadd and not butler:
        fig, axes = plt.subplots(nrows=1, ncols=ncols, figsize=(5*ncols, 4))
        plot_custom_coadd(fig, axes, custom_coadd, 
                          bands_to_plot=bands_to_plot, algorithm=algorithm, min=min, max=max, unit=unit)
    else:
        print("Warning: No Butler or custom coadd provided.")
        return None

    plt.tight_layout()
    plt.show()
    return None