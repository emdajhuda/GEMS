# vera rubin v1.0
# coadd.custom_inject_coadd.py

import sys, os
import numpy as np
import matplotlib.pyplot as plt

from lsst.afw.image import ExposureF, MaskedImageF
from lsst.afw.math import warpExposure, WarpingControl

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from .Utils.tools.tools import progressbar

###################################################################################################
def coadd_exposures_pipeline(
    exposures,
    ref_exp=None,
    warping_kernel="lanczos4",
    save_path=None,
    coadd_name="coadd.fits",
    info=False,
    plot_debug=False,
    same_check=True,
):
    """
    Coadd exposures using LSST-style weighting and WCS alignment.
    Also returns a coverage map showing how many exposures contribute per pixel.

    Parameters
    ----------
    exposures : list of ExposureF
        List of exposures to coadd.
    ref_exp : ExposureF, optional
        Reference exposure for WCS and output size. If None, first exposure is used.
    warping_kernel : str
        Interpolation kernel for warping. Options: "lanczos3", "bilinear", etc.
    save_path : str, optional
        Directory to save coadd FITS. If None, coadd is not saved.
    coadd_name : str
        Filename for saved coadd.
    info : bool
        If True, print diagnostic information for each exposure.
    plot_debug : bool
        If True, display residual images at each step.

    Returns
    -------
    coadd_exp : ExposureF
        Final coadded exposure aligned in WCS.
    coverage_map : np.ndarray
        2D array counting how many exposures contribute to each pixel.
    """

    if len(exposures) == 0:
        raise ValueError("Exposure list is empty.")

    if ref_exp is None:
        ref_exp = exposures[0]

    # Get reference geometry and WCS
    dims = ref_exp.getMaskedImage().getDimensions()
    ref_wcs = ref_exp.getWcs()

    # Initialize empty accumulators
    coadd_mi = MaskedImageF(dims)
    coadd_array = coadd_mi.getImage().getArray()
    coadd_weight = np.zeros((dims.getY(), dims.getX()), dtype=np.float32)
    # Use float64 for accumulation (higher precision)
    #coadd_array = np.zeros((dims.getY(), dims.getX()), dtype=np.float64)
    #coadd_weight = np.zeros_like(coadd_array)
    coverage_map = np.zeros_like(coadd_weight, dtype=np.int32)

    print(f"[INFO] Starting coaddition of {len(exposures)} exposures...")

    # progressbar(0, len(exposures), bar_length=20, progress_char="#")
    for ind, exp in enumerate(exposures, start=1):

        # Skip invalid exposures
        if exp is None:
            print(f"[WARNING] Exposure {ind} is None. Skipping.")
            continue

        if same_check:
            # Compare WCS by checking if their centers match closely (within tolerance)
            ref_center = ref_wcs.pixelToSky(0.5 * dims.getX(), 0.5 * dims.getY())
            exp_center = exp.getWcs().pixelToSky(0.5 * dims.getX(), 0.5 * dims.getY())
            offset_arcsec = ref_center.separation(exp_center).asArcseconds()
            if offset_arcsec < 1e-3:  # ~0.001 arcsec ≈ identical WCS
                warped_exp = exp.clone() # If WCS is identical → skip warping (avoids resampling noise)
            else:
                warped_exp = ExposureF(dims, ref_wcs)
                warpExposure(warped_exp, exp, WarpingControl(warpingKernelName=warping_kernel))
        else:
            warped_exp = ExposureF(dims, ref_wcs)
            warpExposure(warped_exp, exp, WarpingControl(warpingKernelName=warping_kernel))

        warped_mi = warped_exp.getMaskedImage()
        img = warped_mi.getImage().getArray()
        var = warped_mi.getVariance().getArray()

        # Debug info
        if info:
            fraction_nan = np.isnan(img).sum() / img.size
            print(f"Warp {ind}: {fraction_nan:.3%} NaN pixels")

            c1 = ref_wcs.pixelToSky(0.5 * dims.getX(), 0.5 * dims.getY())
            c2 = exp.getWcs().pixelToSky(0.5 * dims.getX(), 0.5 * dims.getY())
            print("Offset (degree):", c1.separation(c2).asArcseconds()/3600)

            # Compute relative rotation angles w.r.t first visit
            print("Rotation angle (degree):", exp.getWcs().getRelativeRotationToWcs(ref_wcs).asDegrees())

        # Apply photometric scale factor if available
        try:
            ref_flux0 = ref_exp.getCalib().getFluxMag0()[0]
            exp_flux0 = exp.getCalib().getFluxMag0()[0]
            scale = exp_flux0 / ref_flux0
        except Exception:
            scale = 1.0

        img *= scale
        var *= scale ** 2

        # Mask invalid pixels
        valid = (var > 0) & (~np.isnan(img))
        w = np.zeros_like(var, dtype=np.float32)
        w[valid] = 1.0 / var[valid]

        img_safe = np.where(valid, img, 0.0)
        
        # Accumulate weighted flux and total weight
        coadd_array += img_safe * w
        # coadd_array += (img_safe) # * w
        coadd_weight += w
        coverage_map += valid.astype(np.int32)

        # Optional: visualize residual between partial coadd and current image
        if plot_debug:
            temp0 = np.where(coadd_weight == 0, 1.0, coadd_weight)
            #temp = coadd_array / temp0 - img_safe
            temp = img_safe - ref_exp.getImage().getArray()
            print("→ Total diff:", np.nansum(temp),
                  "Max:", np.nanmax(np.abs(temp)),
                  "Min:", np.nanmin(np.abs(temp)))

            plt.figure(figsize=(6, 5))
            im = plt.imshow(
                temp,
                origin="lower",
                cmap="gray",
                vmin=np.nanpercentile(temp, 0.01),
                vmax=np.nanpercentile(temp, 99.9),
            )
            plt.title(f"Residual after warp {ind}")
            plt.xlabel("X [pix]")
            plt.ylabel("Y [pix]")
            plt.colorbar(im, label="Intensity", pad=0.05, shrink=0.8)
            plt.show()

        print(f"[{ind}/{len(exposures)}] exposure coadded.")
        # progressbar(ind, len(exposures), bar_length=20, progress_char="#")

    # Final normalization
    coadd_weight_safe = np.where(coadd_weight == 0, 1.0, coadd_weight)
    coadd_array /= coadd_weight_safe
    #coadd_final = coadd_array / coadd_weight_safe
    
    # Variance of coadd = inverse of total weight
    coadd_mi.getVariance().getArray()[:, :] = 1.0 / coadd_weight_safe

    # Convert back to float32 for LSST ExposureF
    #coadd_mi = MaskedImageF(
    #    ImageF(np.float32(coadd_final)),
    #    None, #np.zeros_like(np.float32(coadd_final)),
    #    ImageF(np.float32(1.0 / coadd_weight_safe))
    #)

    # Build final coadded exposure
    coadd_exp = ExposureF(coadd_mi, ref_wcs)

    # Save FITS if requested
    if save_path is not None:
        os.makedirs(save_path, exist_ok=True)
        full_path = os.path.join(save_path, coadd_name)
        coadd_exp.writeFits(full_path)
        print(f"[INFO] LSST-style coadd saved to {full_path}")

        # Also save coverage map
        import astropy.io.fits as fits
        cov_path = os.path.join(save_path, "coverage_map.fits")
        fits.writeto(cov_path, coverage_map, overwrite=True)
        print(f"[INFO] Coverage map saved to {cov_path}")

    print("Coaddition complete.")
    print(f"Pixels with no coverage: {(coverage_map == 0).sum()} / {coverage_map.size}")

    return coadd_exp, coverage_map

def leave_one_out_residual(coadd_exp, exp, warping_kernel="lanczos3"):
    """
    Compare an individual exposure against a coadd by warping it to the coadd's WCS.

    Parameters
    ----------
    coadd_exp : ExposureF
        The final coadd exposure (already built).
    exp : ExposureF
        An individual exposure to compare against the coadd.
    warping_kernel : str
        Warping kernel for resampling.

    Returns
    -------
    warped_exp : ExposureF
        The exposure warped to the coadd's WCS.
    residual : np.ndarray
        Difference image = coadd - warped exposure.
    """

    dims = coadd_exp.getMaskedImage().getDimensions()
    ref_wcs = coadd_exp.getWcs()

    # Warp individual exposure to coadd WCS
    warped_exp = ExposureF(dims, ref_wcs)
    warpExposure(warped_exp, exp, WarpingControl(warpingKernelName=warping_kernel))

    # Image arrays
    coadd_arr = coadd_exp.getMaskedImage().getImage().getArray()
    warped_arr = warped_exp.getMaskedImage().getImage().getArray()

    # Compute raw residual: coadd - warped exposure
    residual = coadd_arr - warped_arr

    # Expected variance per pixel: Var(resid) = 1/sum_weights_coadd + 1/weight_exp
    coadd_var = coadd_exp.getVariance().getArray()
    exp_var = exp.getVariance().getArray()
    expected_var = coadd_var + exp_var
    expected_std = np.sqrt(expected_var)

    # Normalized residual
    residual_norm = residual / expected_std
    return warped_exp, residual, residual_norm

def validate_rotation(image_orig, image_rot, rotation_angle, n_points=5, offset_pixels=50):
    """
    Validate the rotation of an image by comparing several reference points
    in the original and rotated images.
    
    Parameters
    ----------
    image_orig : 2D numpy.ndarray
        Original image data.
    image_rot : 2D numpy.ndarray
        Rotated image data.
    rotation_angle : float
        Rotation angle in degrees (counter-clockwise).
    n_points : int, optional
        Number of points along each axis to test around the center. Default 5.
    offset_pixels : float, optional
        Maximum pixel distance from center to pick reference points. Default 50.
    
    Returns
    -------
    avg_error : float
        Average Euclidean pixel error between expected and actual positions.
    """
    rows, cols = image_orig.shape
    x_center, y_center = 0.5 * cols, 0.5 * rows
    theta = np.deg2rad(rotation_angle)

    errors = []

    # Generate a grid of points around the center
    offsets = np.linspace(-offset_pixels, offset_pixels, n_points)
    for dx in offsets:
        for dy in offsets:
            x0, y0 = x_center + dx, y_center + dy

            # Expected rotated coordinates
            dx0, dy0 = x0 - x_center, y0 - y_center
            x_rot_expected = dx0 * np.cos(theta) - dy0 * np.sin(theta) + x_center
            y_rot_expected = dx0 * np.sin(theta) + dy0 * np.cos(theta) + y_center

            # Get nearest pixel in rotated image
            x_pix = int(round(x_rot_expected))
            y_pix = int(round(y_rot_expected))

            # Skip points outside bounds
            if 0 <= x_pix < cols and 0 <= y_pix < rows:
                orig_value = image_orig[int(round(y0)), int(round(x0))]
                rot_value = image_rot[y_pix, x_pix]
                error = abs(orig_value - rot_value)
                errors.append(error)

    avg_error = np.mean(errors) if errors else np.nan
    print(f"Average pixel intensity error after rotation: {avg_error:.6f}")
    return avg_error