
# v1.0
# plots/coadd_plot.py
# set of functions that plot coadd results

import lsst.afw.display as afwDisplay
import matplotlib.pyplot as plt
import numpy as np

afwDisplay.setDefaultBackend('matplotlib')

###################################################################################################
######### Display coadds
def plot_custom_coadd(fig, axes, custom_coadds, bands_to_plot=None, algorithm='asinh',
                      min='zscale', max=None, unit=None):
    """
    Plot custom coadds for selected bands.
    """
    if not custom_coadds:
        print("Warning: No custom coadds provided.")
        return fig, axes

    if bands_to_plot is None:
        bands_to_plot = list(custom_coadds.keys())
    elif isinstance(bands_to_plot, str):
        bands_to_plot = [bands_to_plot]

    axes = np.atleast_1d(axes)
    if len(bands_to_plot) != len(axes):
        print("Warning: Number of bands to plot does not match number of axes.")
        return fig, axes

    titles_Custom = [f"Custom Coadd ({b})" for b in bands_to_plot]

    for ax, title, band in zip(axes, titles_Custom, bands_to_plot):
        plt.sca(ax)
        display = afwDisplay.Display(frame=fig)
        display.scale(algorithm, min, max, unit)
        display.mtv(custom_coadds[band].image)
        display.show_colorbar(False)
        ax.axis('off')
        ax.set_title(title)

    return fig, axes

def plot_original_coadd(fig, axes, butler, my_tract, my_patch, bands_to_plot=None, skymap_name='lsst_cells_v1',
                        algorithm='asinh', min='zscale', max=None, unit=None):
    """
    Plot original coadds from Butler.
    """
    
    if bands_to_plot is None:
        print("Warning: No bands to plot specified.")
        return fig, axes
    elif isinstance(bands_to_plot, str):
        bands_to_plot = list(bands_to_plot)
    
    axes = np.atleast_1d(axes)
    if len(bands_to_plot) != len(axes):
        print("Warning: Number of bands to plot does not match number of axes.")
        return fig, axes

    titles_Original = [f"Original Coadd ({b})" for b in bands_to_plot]

    coaddId = {
        'band': None,
        'tract': my_tract,
        'patch': my_patch,
        'skymap': skymap_name
    }

    for ax, title, band in zip(axes, titles_Original, bands_to_plot):
        coaddId['band'] = band
        original_coadd = butler.get_dataset('deep_coadd', coaddId)
        plt.sca(ax)
        display = afwDisplay.Display(frame=fig)
        display.scale(algorithm, min, max, unit)
        display.mtv(original_coadd.image)
        display.show_colorbar(False)
        ax.axis('off')
        ax.set_title(title)

    return fig, axes

######### Display RGB coadds
def normalize_image(img, p1=None, p99=None):
    """Normalize an image array to [0, 1] using percentiles."""
    if p1 is None or p99 is None:
        p1, p99 = np.percentile(img, (1, 99))
    img_clip = np.clip((img - p1) / (p99 - p1), 0, 1)
    return img_clip, p1, p99

def make_rgb_image(coadd_dict, bands, p1_vals=None, p99_vals=None):
    """Create RGB composite from coadd dict and bands."""
    rgb = []
    for i, b in enumerate(bands):
        img = coadd_dict[b].image.array.astype(float)
        if p1_vals is not None and p99_vals is not None:
            img_norm, _, _ = normalize_image(img, p1_vals[i], p99_vals[i])
        else:
            img_norm, _, _ = normalize_image(img)
        rgb.append(img_norm)
    return np.dstack(rgb)

def compare_rgb_coadds(custom_coadd=None, butler=None, my_tract=None, my_patch=None,
                       skymap_name='lsst_cells_v1', bands=('g', 'r', 'i'),
                       titles=("Original Coadd", "Custom Coadd"), normalize_together=True):
    """
    Compare RGB composites between the original and custom coadds.
    """
    original_dict = None
    custom_dict = None

    # Load original coadd from Butler if provided
    if butler is not None:
        original_dict = {}
        coaddId = {
            'band': None,
            'tract': my_tract,
            'patch': my_patch,
            'skymap': skymap_name
        }
        for band in bands:
            coaddId['band'] = band
            original_dict[band] = butler.get_dataset('deep_coadd', coaddId)

    # Load custom coadd if provided
    if custom_coadd is not None:
        custom_dict = custom_coadd

    # Determine normalization percentiles if needed
    if normalize_together and original_dict is not None and custom_dict is not None:
        p1_vals = []
        p99_vals = []
        for b in bands:
            all_pixels = np.concatenate([
                original_dict[b].image.array.ravel(),
                custom_dict[b].image.array.ravel()
            ])
            p1, p99 = np.percentile(all_pixels, (1, 99))
            p1_vals.append(p1)
            p99_vals.append(p99)
    else:
        p1_vals = p99_vals = None

    # Build RGB images
    original_rgb = make_rgb_image(original_dict, bands, p1_vals, p99_vals) if original_dict else None
    custom_rgb = make_rgb_image(custom_dict, bands, p1_vals, p99_vals) if custom_dict else None

    # Decide layout
    imgs = []
    lbls = []
    if original_rgb is not None:
        imgs.append(original_rgb)
        lbls.append(titles[0])
    if custom_rgb is not None:
        imgs.append(custom_rgb)
        lbls.append(titles[1])

    ncols = len(imgs)
    fig, axes = plt.subplots(1, ncols, figsize=(6 * ncols, 6))
    if ncols == 1:
        axes = [axes]  # make iterable

    for ax, img, title in zip(axes, imgs, lbls):
        ax.imshow(img, origin='lower')
        ax.set_title(title, fontsize=14)
        ax.axis('off')

    plt.tight_layout()
    plt.show()
    print(f"Displayed RGB comparison using bands {bands} "
          f"(normalize_together={normalize_together}).")

