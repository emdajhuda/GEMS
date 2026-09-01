# v1.0
# plots/exposure_plot.py
# set of functions that plot exposure results


import lsst.afw.display as afwDisplay
import matplotlib.pyplot as plt
import numpy as np
# import lsst.geom
import sys, os

from astropy.wcs import WCS

afwDisplay.setDefaultBackend('matplotlib')

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ..sky.sky import skywcs_to_astropy

###################################################################################################

# Low-level helpers
# ---------------------------------------------------------------------
def fix_wcsaxes_labels(ax):
    """
    Automatically fix RA/Dec axis formatting in WCSAxes.

    Parameters
    ----------
    ax : WCSAxes
        Matplotlib axis with WCS projection.
    """
    from astropy import units as u
    
    for _, coord in enumerate(ax.coords):
        ctype = coord.coord_type.upper()  # usually "RA" or "DEC"
        # print(ctype)
        if "RA" in ctype:
            coord.set_format_unit(u.hourangle)
            coord.set_axislabel("RA", fontsize=12)
        elif "DEC" in ctype:
            coord.set_format_unit(u.deg)
            coord.set_axislabel("Dec", fontsize=12)
        else:
            # fallback: just leave as degrees
            coord.set_format_unit(u.deg)
            coord.set_axislabel(ctype)
    return None

def extract_array(obj, variance=False):
    """Return image or variance array from LSST Exposure or numpy."""
    if hasattr(obj, "getMaskedImage"):
        mi = obj.getMaskedImage()
        return mi.getVariance().getArray() if variance else mi.getImage().getArray()
    return obj

def normalize_axes(axes, nrows, ncols):
    axes = np.asarray(axes)
    if nrows == 1 and ncols == 1:
        return axes.reshape((1, 1))
    if nrows == 1:
        return axes.reshape((1, ncols))
    if ncols == 1:
        return axes.reshape((nrows, 1))
    return axes

def render_image(ax, img, title, scale, percentiles, cmap="gray", extent=None):
    from astropy.visualization import ZScaleInterval, ImageNormalize, AsinhStretch
    if scale == "zscale_asinh":
        norm = ImageNormalize(img, interval=ZScaleInterval(),
                               stretch=AsinhStretch())
        im = ax.imshow(img, origin="lower", cmap=cmap, norm=norm, extent=extent)
    else:
        vmin, vmax = np.nanpercentile(img, percentiles)
        im = ax.imshow(img, origin="lower", cmap=cmap,
                       vmin=vmin, vmax=vmax, extent=extent)

    ax.set_title(title, fontsize=11)
    return im

def overlay_sky_point(ax, exp, sky_coord, marker="r*", size=8):
    """Mark a sky coordinate on an LSST exposure."""
    if not sky_coord:
        return

    try:
        x, y = exp.getWcs().skyToPixel(sky_coord)
        bbox = exp.getBBox()
        x -= bbox.getMinX()
        y -= bbox.getMinY()

        img = exp.getMaskedImage().getImage().getArray()
        if 0 <= x < img.shape[1] and 0 <= y < img.shape[0]:
            ax.plot(x, y, marker, markersize=size)
    except Exception as e:
        print(f"[WARN] overlay_sky_point failed: {e}")

def plot_histogram(ax, img, filter_nan=True):
    data = img[np.isfinite(img)] if filter_nan else img.flatten()
    if data.size == 0:
        ax.text(0.5, 0.5, "No finite data", ha="center", va="center")
    else:
        ax.hist(data, bins=100, histtype="step")

# Top-level
# ---------------------------------------------------------------------
def injection_steps(before, after, points, diference=True,
                    grid=True, add_colorbar=True, percentiles=[5, 95],
                    cutout_radius_arcsec=None,
                    xlim_world=None, ylim_world=None,
                    save_path=None, names=['Before', 'After', 'Difference'],
                    extent=None):
    """
    Compare exposures before/after injection and plot with WCS coordinates.

    Automatically detects whether inputs are LSST ExposureF objects
    or Astropy (FITS/CCDData-like) objects.

    Parameters
    ----------
    before : lsst.afw.image.ExposureF or Astropy object
        Exposure before injection.
    after : lsst.afw.image.ExposureF or Astropy object
        Exposure after injection.
    points : list of [ra, dec]
        Positions of injected sources in degrees.
    grid : bool, optional
        If True, overlay a coordinate grid.
    percentiles : list, optional
        Percentiles for image scaling (default = [5, 95]).
    cutout_radius_arcsec : float, optional
        If set, zoom around the first injected point by this radius (arcsec).
    xlim_world : tuple, optional
        Manual RA limits (deg), e.g. (RA_min, RA_max).
    ylim_world : tuple, optional
        Manual Dec limits (deg), e.g. (Dec_min, Dec_max).
    save_path : str, optional
        If provided, the figure will be saved at this path instead of being displayed.
    names :  list, optional
        List of panel Name, default, ['Before', 'After', 'Difference']
    """
    labelpoint = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    # Detect type automatically
    if hasattr(after, "getWcs"):  # LSST object
        try:
            wcs_for_plot = after.getWcs()
            # Convert to Astropy WCS for matplotlib
            wcs_for_plot = skywcs_to_astropy(wcs_for_plot)
            print("[INFO] Converted LSST SkyWcs -> Astropy WCS")
        except Exception as e:
            raise TypeError(f"Failed to convert LSST SkyWcs to Astropy WCS: {e}")
        before_data = extract_array(before, variance=False)  # before.image.array
        after_data = extract_array(after, variance=False)  # after.image.array
    elif hasattr(after, "header") and hasattr(after, "data"):  # Astropy object
        print("[INFO] Detected Astropy data with WCS")
        wcs_for_plot = WCS(after.header)
        before_data = before.data
        after_data = after.data
    else:
        raise TypeError("Unsupported input type. Must be LSST ExposureF or Astropy HDU/CCDData.")

    # Build image panels
    images = [
        (before_data, names[0]),
        (after_data, names[1]),
        (after_data - before_data, names[2])
    ]

    # Plotting
    ncols = 3 if diference else 2
    fig = plt.figure(figsize=(ncols*5, 5))
    for i, (data, title_str) in enumerate(images[:ncols:], start=1):
        ax = fig.add_subplot(1, 3, i, projection=wcs_for_plot)

        # Plot injection points
        for label, (ra_deg, dec_deg) in zip(labelpoint, points):
            ax.scatter(ra_deg, dec_deg,
                       transform=ax.get_transform('world'),
                       edgecolor='red', facecolor='None')
            ax.text(ra_deg, dec_deg, label,
                    transform=ax.get_transform('world'),
                    color='yellow', fontsize=12, weight='bold')

        # Contrast scaling
        im = render_image(ax, data, title_str, "percentiles", percentiles, cmap="gray", extent=extent)

        if add_colorbar:
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label='Intensity')

        if grid:
            ax.coords.grid(color="white", ls="dotted")

        ax.set_xlabel('RA')
        ax.set_ylabel('Dec')

        # Fix RA/Dec formatting automatically
        # fix_wcsaxes_labels(ax)
        
        # Zoom options
        # Automatic
        if cutout_radius_arcsec is not None:
            # Take first point
            ra0, dec0 = points[0]
            radius_deg = cutout_radius_arcsec / 3600.0  # arcsec → degrees

            # World → pixel
            x_center, y_center = wcs_for_plot.world_to_pixel_values(ra0, dec0)

            # Approx pixel scale (deg/pixel)
            scale_deg = np.mean(np.abs(wcs_for_plot.pixel_scale_matrix.diagonal()))
            radius_pix = radius_deg / scale_deg

            ax.set_xlim(x_center - radius_pix, x_center + radius_pix)
            ax.set_ylim(y_center - radius_pix, y_center + radius_pix)

        # Manual zoom overrides automatic
        if xlim_world is not None:
            ax.set_xlim(*xlim_world)
        if ylim_world is not None:
            ax.set_ylim(*ylim_world)

    plt.tight_layout()
    
    # Save or show the figure depending on argument
    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"[INFO] Figure saved to {save_path}")
    else:
        plt.show()

    # Free memory after plotting
    plt.close(fig)
    return None

def plot_exposures_full(
    exposures,
    coadd_exp=None,
    center_coord=None,
    titles=None,
    axeslabels=None,
    save_path=None,
    show_second_row=False,
    show_histograms=False,
    add_colorbar=False,
    filter_nan_hist=True,
    exposures_scale="zscale_asinh",
    coadd_exp_scale="zscale_asinh",
    percentiles=(1, 99),
    grid=True,
    projection=None,
):
    """
    Modular exposure plotting with safe axes handling and WCS overlays.
    """

    n_exps = len(exposures)
    ncols = n_exps + (1 if coadd_exp else 0)
    nrows = 1
    if show_second_row: nrows += 1
    if show_histograms: nrows += 1

    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(5 * ncols, 4 * nrows),
        subplot_kw={"projection": projection},
    )

    axes = normalize_axes(axes, nrows, ncols)

    SCI = 0
    VAR = 1 if show_second_row else None
    HIST = nrows - 1 if show_histograms else None

    # Science exposures
    for i, exp in enumerate(exposures):
        ax = axes[SCI, i]
        img = extract_array(exp)
        title = titles[i] if titles and i < len(titles) else f"Exposure {i+1}"
        
        im = render_image(ax, img, title, exposures_scale, percentiles)

        if add_colorbar:
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        if grid and projection:
            ax.coords.grid(color="white", ls="dotted")

        overlay_sky_point(ax, exp, center_coord)

    # Coadd
    if coadd_exp:
        ax = axes[SCI, -1]
        img = extract_array(coadd_exp)
        
        im = render_image(ax, img, "Coadd", coadd_exp_scale, percentiles)

        if add_colorbar:
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        overlay_sky_point(ax, coadd_exp, center_coord)

    # Variance row
    if show_second_row:
        for i, exp in enumerate(exposures):
            ax = axes[VAR, i]
            var = extract_array(exp, variance=True)
            im = render_image(ax, var, f"Var {i+1}", "percentile",
                              percentiles, cmap="inferno")

            if add_colorbar:
                fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        if coadd_exp:
            ax = axes[VAR, -1]
            var = extract_array(coadd_exp, variance=True)
            im = render_image(ax, var, "Coadd Var", "percentile",
                              percentiles, cmap="inferno")

            if add_colorbar:
                fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    # Histogram row
    if show_histograms:
        for i, exp in enumerate(exposures):
            ax = axes[HIST, i]
            img = extract_array(exp)
            plot_histogram(ax, img, filter_nan_hist)
            ax.set_title(f"Hist {i+1}")

        if coadd_exp:
            ax = axes[HIST, -1]
            img = extract_array(coadd_exp)
            plot_histogram(ax, img, filter_nan_hist)
            ax.set_title("Coadd Hist")

    # Axis labels
    if axeslabels:
        for r in range(nrows):
            for c in range(ncols):
                axes[r, c].set_xlabel(axeslabels[0])
                axes[r, c].set_ylabel(axeslabels[1])

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"[INFO] Saved to {save_path}")
    else:
        plt.show()

    plt.close(fig)


