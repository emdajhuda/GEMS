# vera rubin v1.0
# source_injection/injection.py
# see:
# https://pipelines.lsst.io/v/daily/modules/lsst.source.injection/index.html
# https://dp1.lsst.io/tutorials/notebook/105/notebook-105-4.html
# https://github.com/alxogm/SL-MEX-1/blob/main/stamp_inyect_1.ipynb
import os, sys
import time
import json

import numpy as np
import astropy.units as u

from lsst.source.injection import VisitInjectConfig, VisitInjectTask, generate_injection_catalog
from astropy.coordinates import SkyCoord
from astropy.table import Table, vstack
from astropy.io import fits
from lsst.daf.butler import Butler
from lsst.daf.butler.registry import ConflictingDefinitionError

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ..utils.sky.sky import patch_center
from ..py.visit_selection.visit_selection import visit_dataset



##############################################################################

# Low-level helpers
# ---------------------------------------------------------------------
def make_serializable(obj):
    if isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    return obj

def measure_quality(calexp):
    """
    Estimate the approximate SNR (signal-to-noise ratio) of an LSST calexp image.

    Parameters:
    -----------
    calexp : lsst.afw.image.ExposureF
        A single calibrated LSST exposure (calexp) containing:
        - image array
        - mask array
        - variance array

    Returns:
    --------
    float
        Approximate global SNR for the image.
    """

    # Extract arrays from calexp
    image = calexp.image.array        # Pixel values after calibration
    variance = calexp.variance.array  # Per-pixel noise estimate
    mask = calexp.mask.array          # Pixel mask flags

    # Create a boolean mask for "good" pixels
    # Exclude bad pixels, saturated pixels, and those with zero variance
    GOOD = (mask == 0) & (variance > 0)

    # Estimate the background using the median of good pixels
    background = np.median(image[GOOD])

    # Signal: mean of pixels above the background
    signal = np.mean(image[GOOD & (image > background)])

    # Noise: sqrt of mean variance of good pixels
    noise = np.sqrt(np.mean(variance[GOOD]))

    # Compute SNR, handle division by zero
    SNR = signal / noise if noise > 0 else 0
    return SNR

def save_visit_images(
    local_repo: str,
    collections: str,
    run_name: str,
    injected_exposures: list,
    visits: list[dict],
    dataset_type: str = "visit_image",
):
    """
    Save injected exposures into a local butler repository.
    
    Returns
    -------
    dict{"saved": list of visit IDs saved,
        "skipped": list of visit IDs already existing
        }
    """
    configured_butler = Butler(local_repo, collections=collections,
                                run=run_name, writeable=True)

    saved, skipped = [], []
    for i, exposure in enumerate(injected_exposures):
        dataId = visits[i]
        visit = dataId["visit"]

        try:
            # Check if dataset already exists
            existing = configured_butler.registry.queryDatasets(
                dataset_type,
                dataId=dataId,
            )
            if list(existing):
                msg = f"[SKIP] visit {visit} already exists."
                print(msg)
                skipped.append(visit)
                continue

            # Save dataset
            configured_butler.put(exposure, dataset_type, dataId)

            msg = f"[SAVE] visit {visit} stored successfully."
            print(msg)
            saved.append(visit)

        except ConflictingDefinitionError:
            msg = f"[SKIP] visit {visit} conflict detected."
            print(msg)

            skipped.append(visit)

        except Exception as e:
            msg = f"[ERROR] visit {visit} failed: {e}"
            print(msg)
            raise

    return {
        "saved": saved,
        "skipped": skipped,
    }

# High-level operations
# ---------------------------------------------------------------------
def create_crowded_injection_catalog(
        ra_list,
        dec_list,
        stamp_paths,
        mags,
        min_sep=0.0005,
        separation_spherical=True):
    """
    Create an injection catalog for multiple 'Stamp'-type sources while ensuring a minimum separation 
    between them to avoid overlaps.

    Parameters
    ----------
    ra_list : list of float
        Right Ascensions of the sources in degrees.
    dec_list : list of float
        Declinations of the sources in degrees.
    stamp_paths : list of str
        File paths to the stamp images used for injection.
    mags : list of float
        Apparent magnitudes of the injected sources.
    min_sep : float, optional
        Minimum allowed separation between injected sources in degrees. Default is 0.0005.
    separation_spherical : bool, optional
        If True, compute angular separations using spherical geometry (more accurate for larger separations).
        If False, use plain Euclidean separation (fine for very small separations).

    Returns
    -------
    astropy.table.Table
        Table containing the injection catalog with non-overlapping sources.
    """
    
    n_sources = len(ra_list)
    
    # Validate input lengths to avoid mismatched parameters
    if not (len(dec_list) == len(stamp_paths) == len(mags) == n_sources):
        raise ValueError("All input lists must have the same length.")
    
    accepted = []  # Stores only the sources that pass the separation check
    for i in range(n_sources):
        ra_i, dec_i = ra_list[i], dec_list[i]
        too_close = False

        if min_sep is not None:
        
            # Compare this source to all previously accepted ones
            for src in accepted:
                if separation_spherical:
                    sep = SkyCoord(ra_i*u.deg, dec_i*u.deg).separation(
                        SkyCoord(src['ra']*u.deg, src['dec']*u.deg)
                    ).deg
                else:
                    sep = np.sqrt((ra_i - src['ra'])**2 + (dec_i - src['dec'])**2)  # Approximation valid for small separations
                
                if sep < min_sep:
                    too_close = True
                    break
        
        if not too_close:
            accepted.append({
                "ra": ra_i,
                "dec": dec_i,
                "mag": mags[i],
                "stamp": stamp_paths[i]
            })
    print(accepted)

    # Return an empty table if no sources are accepted
    if not accepted:
        return Table(names=["injection_id", "ra", "dec", "source_type", "mag", "stamp"])
    
    # Try using LSST's generate_injection_catalog
    try:
        cat_list = []
        if min_sep == None:
            min_sep=0.00000001
        for idx, src in enumerate(accepted):
            ra_lim = [src['ra'] - min_sep/2, src['ra'] + min_sep/2]
            dec_lim = [src['dec'] - min_sep/2, src['dec'] + min_sep/2]
            
            # number=1 → inject exactly one source in this RA/Dec bounding box ([ra_min, ra_max], [dec_min, dec_max])
            # seed controls the random placement; adding idx ensures reproducibility but variation between sources
            cat = generate_injection_catalog(
                ra_lim=ra_lim,
                dec_lim=dec_lim,
                number=1,
                seed=f'{3210 + idx}',
                source_type="Stamp",
                mag=[src['mag']],
                stamp=[src['stamp']]
            )
            cat_list.append(cat)
        
        return vstack(cat_list)
    
    except Exception as e:
        print(f"generate_injection_catalog failed: {e}")
    
    # Fallback: create the catalog manually without LSST helper function
    return Table({
        "injection_id": list(range(len(accepted))),
        "ra": [src['ra'] for src in accepted],
        "dec": [src['dec'] for src in accepted],
        "source_type": ["Stamp"] * len(accepted),
        "mag": [src['mag'] for src in accepted],
        "stamp": [src['stamp'] for src in accepted]
    })

def apply_correction_from_exposureF(
        data, hdr, rotation_angle,
        warping_kernel='lanczos4',
        keep_size=False,
        update_wcs=True,
        fill_value=0.0
    ):
    """
    Rotate an astronomical image (2D numpy array) using LSST ExposureF 
    and optionally update its WCS.

    Parameters
    ----------
    ...
    fill_value : float, optional
        Value used to fill invalid pixels after rotation. Default 0.0.
    """
    import lsst.geom as geom
    import lsst.afw.math as afwMath
    import lsst.afw.geom as afwGeom
    from lsst.afw.image import ExposureF, ImageF, MaskedImageF

    rotation_angle = float(rotation_angle) % 360.0
    valid_kernels = ['bilinear', 'lanczos2', 'lanczos3', 'lanczos4', 'nearest']
    if warping_kernel not in valid_kernels:
        raise ValueError(f"Invalid warping kernel '{warping_kernel}'. Must be one of {valid_kernels}")

    image = ImageF(data.astype(np.float32, order="C"), deep=False)
    exposure = ExposureF(MaskedImageF(image))

    # Build WCS
    crpix = geom.Point2D(hdr["CRPIX1"], hdr["CRPIX2"])
    crval = geom.SpherePoint(hdr["CRVAL1"] * geom.degrees, hdr["CRVAL2"] * geom.degrees)
    if "CD1_1" in hdr:
        cd = np.array([[hdr["CD1_1"], hdr["CD1_2"]], [hdr["CD2_1"], hdr["CD2_2"]]])
    else:
        cd = np.array([[hdr["PC1_1"] * hdr["CDELT1"], hdr["PC1_2"] * hdr["CDELT1"]],
                       [hdr["PC2_1"] * hdr["CDELT2"], hdr["PC2_2"] * hdr["CDELT2"]]])
    exposure.setWcs(afwGeom.makeSkyWcs(crpix, crval, cd))

    # Rotation transform
    dims = exposure.getDimensions()
    center = geom.Point2D(0.5 * dims.getX(), 0.5 * dims.getY())
    R = geom.AffineTransform.makeRotation(rotation_angle * geom.degrees)
    # Compose the transforms: T2 * R * T1
    rot_center = geom.AffineTransform.makeTranslation(geom.Extent2D(center.getX(), center.getY())) * R * geom.AffineTransform.makeTranslation(geom.Extent2D(-center.getX(), -center.getY()))
    transform = afwGeom.makeTransform(rot_center)
    rotated_wcs = afwGeom.makeModifiedWcs(transform, exposure.getWcs(), False)

    # Warp
    warper = afwMath.Warper(warping_kernel)
    bbox = exposure.getBBox() if keep_size else None
    rotated_exp = warper.warpExposure(rotated_wcs, exposure, destBBox=bbox)
    rotated_data = np.nan_to_num(rotated_exp.getMaskedImage().getImage().getArray(), nan=fill_value)

    hdr_new = hdr.copy()
    if update_wcs:
        offset = geom.Extent2D(geom.Point2I(0, 0) - rotated_exp.getXY0())
        wcs_adj = rotated_exp.getWcs().copyAtShiftedPixelOrigin(offset)
        for k, v in wcs_adj.getFitsMetadata().toDict().items():
            if k.startswith(('CR', 'CD', 'PC', 'CDELT', 'CTYPE', 'CUNIT')):
                hdr_new[k] = v

    return rotated_data, hdr_new

def apply_correction_from_data(data,
        hdr,
        rotation_angle,
        keep_size=False,
        interp_order=3,
        update_wcs=True,
        mode="constant",
        cval=0.0, c=1):
    """
    Rotate a 2D image array and optionally update its WCS (World Coordinate System) in the FITS header.

    Parameters
    ----------
    data : 2D ndarray
        Input image data.
    hdr : astropy.io.fits.Header
        FITS header associated with the image.
    rotation_angle : float
        Rotation angle in degrees (anticlockwise).
    keep_size : bool, optional
        If True, output image keeps same shape as input (may crop edges). Default False.
    interp_order : int, optional
        Spline interpolation order used in rotation. Default is 3 (cubic).
    update_wcs : bool, optional
        If True, modifies the WCS in the header to match the rotated image. Default True.
    mode : str, optional
        How to handle values outside the input boundaries. Default 'constant'.
    cval : float, optional
        Value to fill past edges if mode='constant'. Default 0.0.

    Returns
    -------
    rotated_data : 2D ndarray
        Rotated image data.
    hdr_new : astropy.io.fits.Header
        Updated FITS header with rotated WCS if update_wcs=True, else original header.
    """
    from scipy import ndimage
    # from reproject import reproject_interp
    
    # Rotate the image array
    rotated_data = ndimage.rotate(
        data,
        rotation_angle,
        reshape=not keep_size,
        order=interp_order,
        mode=mode,
        cval=cval,
        prefilter=True
    )

    hdr_new = hdr.copy()

    # Update WCS if present
    if update_wcs and 'CTYPE1' in hdr:
        from astropy.wcs import WCS
        
        w = WCS(hdr)  # Initialize WCS object

        # Original and rotated image shapes
        ny, nx = data.shape
        ny2, nx2 = rotated_data.shape

        # Original and new image centers (FITS is 1-based, the pixel (1,1) is on the upper left)
        cx, cy = (nx + 1) / 2.0, (ny + 1) / 2.0
        cx2, cy2 = (nx2 + 1) / 2.0, (ny2 + 1) / 2.0

        # 2x2 rotation matrix (anticlockwise)
        theta = np.deg2rad(rotation_angle)
        R = np.array([[np.cos(theta), - c * np.sin(theta)],
                      [c * np.sin(theta),  np.cos(theta)]])

        # Adjust reference pixel (CRPIX) for center shift
        v = np.array([w.wcs.crpix[0] - cx, w.wcs.crpix[1] - cy])  # vector from the original center to CRPIX (in pixels, FITS 1-based convention)
        v_rot = R @ v  # rotate this vector
        w.wcs.crpix = [v_rot[0] + cx2, v_rot[1] + cy2]  # shifting it to the new center

        # Rotate linear transformation (CD or PC matrix)
        # w.wcs.pc or cd linear part (matrix) of WCS which transform pixel offsets to intermediate coordinates (before sky projection and CDELT scaling).
        # When compute R @ PC, we inject the same rotation applied to the imagen to the system axes of the WCS, in order that the "header" describe
        # correctly as the pixel point out the sky after the array rotation.
        if w.wcs.has_cd():
            w.wcs.cd = R @ w.wcs.cd
        else:
            w.wcs.pc = R @ w.wcs.pc

        # Update header with rotated WCS, preserving other keywords
        hdr_new = w.to_header()
        for key in hdr:
            try:
                # copy only the non problematic FITS
                if key not in hdr_new:
                    val = hdr[key]
                    if isinstance(val, (int, float, str, bool, type(None))):
                        hdr_new[key] = val
            except ValueError:
                print("Warning: Ignoring illegal keyword: ", key)

        # rotated_data, footprint = reproject_interp((data, hdr), hdr_new, shape_out=(ny2, nx2))
                
    return rotated_data, hdr_new

def apply_correction_to_stamp(
        stamp_file,
        rotation_angle,
        output_path=None,
        keep_size=False,
        interp_order=3,
        update_wcs=True,
        c=1,
        from_data=False,
        warping_kernel='lanczos4'
    ):
    """
    Rotate/Shift a FITS (Flexible Image Transport System) stamp image by a given angle (anticlockwise), optionally updating the WCS.

    Parameters:
    -----------
    stamp_file : str
        Path to the input FITS stamp.
    rotation_angle : float
        Rotation angle in degrees (anticlockwise).
    output_path : str
        Path to save the rotated FITS file.
    keep_size : bool
        If True, keeps the original image size (cropping or padding as needed).
    interp_order : int
        Interpolation order for rotation (0=nearest, 1=linear, 3=cubic).
    update_wcs : bool
        If True, rotate and update the WCS information in the header.
    from_data : bool
        if True used the function apply_correction_from_data else apply_correction_from_exposureF
    warping_kernel : str
        Interpolation kernel for warping. Options: "lanczos3", "bilinear", etc.

    Returns:
    --------
    str or astropy.io.fits.HDUList
        Path to the rotated FITS file if output_path is given, else HDU object.

    see:
    https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.rotate.html
    """
    try:
        # Load the original data and header
        with fits.open(stamp_file) as hdul:
            data = hdul[0].data.astype(np.float32, copy=False)  # Give the pixels of the first extension
            hdr = hdul[0].header.copy()  # Copy its metadata (header)
            # Note: The header may contain WCS (World Coordinate System) keywords such as:
            # NAXIS1, NAXIS2: size of the image in pixels along X and Y axes.
            # CRPIX1, CRPIX2: pixel coordinates of the reference point in the image.
            #                 This is the “anchor” pixel used for coordinate transformations.
            # CRVAL1, CRVAL2: celestial coordinates (RA/Dec in degrees) corresponding to the reference pixel (CRPIX1, CRPIX2).
            #                  They define the position on the sky that the reference pixel represents.
            # CDELT1, CDELT2: pixel scale in degrees per pixel along X and Y axes.
            #                  They are used to convert pixel offsets to sky coordinate offsets.
            # CTYPE1, CTYPE2: type of projection used for mapping the sky onto the image (e.g., 'TAN' for gnomonic, 'CAR' for Cartesian).
            #                  Determines how RA/Dec are computed for pixels away from the reference pixel.
            # etc.
            # Using these WCS parameters, the celestial coordinates (RA, Dec) of any pixel (x, y) can be calculated as:
            #   RA  = CRVAL1 + (x - CRPIX1) * CDELT1 (with projection applied by CTYPE1)
            #   Dec = CRVAL2 + (y - CRPIX2) * CDELT2 (with projection applied by CTYPE2)
            # This allows transforming pixel positions to accurate sky coordinates.
        if from_data:
            rotated_data, hdr_new = apply_correction_from_data(
                data, hdr, rotation_angle,
                keep_size=keep_size, interp_order=interp_order, update_wcs=update_wcs, c=c
            )
        else:
            rotated_data, hdr_new = apply_correction_from_exposureF(
                data, hdr, rotation_angle,
                warping_kernel=warping_kernel,
                keep_size=keep_size,
                update_wcs=update_wcs
            )
        
        # Create new HDU with rotated data and header
        hdu = fits.PrimaryHDU(data=rotated_data, header=fits.Header(hdr_new)) # Dumps the modified WCS back to the header. Thus the FITS you are going to write will already have the rotated WCS.
        # IMPORTANT: This methodology ajust only the linear part (orientation/scale). If the "header" has distortions (SIP A_*, B_*, PV/TPV…), 
        #            they are not recalculated here. For distorted mappings, reprojection with tools like reproject would be needed.

        # Remove NAXIS1/NAXIS2 to let FITS recalc from data shape
        for key in ['NAXIS1', 'NAXIS2']:
            hdu.header.pop(key, None)

        # Add metadata about rotation
        hdu.header['ROT_ANG'] = (rotation_angle, 'Rotation applied (deg, anticlockwise)')
        #hdu.header['ROT_KEEP'] = (keep_size, 'True if original image size kept')
        hdu.header['ROT_INT'] = (interp_order, 'Interpolation order used')
        
        # Save to file if requested
        if output_path:
            hdu.writeto(output_path, overwrite=True)
            return output_path
        else:
            return hdu

    except Exception as e:
        print(f"Error rotating stamp '{stamp_file}': {e}")
        return None

def inject_stamp(visit_image, inj_cat):
    """
    Inject artificial sources ("stamps") into an LSST exposure.

    This function uses the LSST VisitInjectTask to add synthetic sources 
    defined in an input injection catalog into a given calibrated exposure.

    Parameters
    ----------
    visit_image : lsst.afw.image.ExposureF
        The calibrated LSST exposure (calexp/visit image) to inject sources into.
    inj_cat : lsst.afw.table.SourceCatalog
        Injection catalog with source positions, magnitudes, etc.

    Returns
    -------
    injected_exposure : lsst.afw.image.ExposureF or None
        The exposure with injected sources, or None if injection failed.
    
    https://dp1.lsst.io/tutorials/notebook/105/notebook-105-4.html
    """
    # Create the injection task
    inject_config = VisitInjectConfig()
    inject_task = VisitInjectTask(config=inject_config)

    try:
        injected_output = inject_task.run(
            injection_catalogs=inj_cat,
            input_exposure=visit_image.clone(),  # clone to avoid modifying the original
            psf=visit_image.getPsf(),
            photo_calib=visit_image.getPhotoCalib(),
            wcs=visit_image.wcs
        )
    except Exception as e:
        print(f"  -> Error during injection in {visit_image.dataId}: {e}")
        return None
    
    # Extract the exposure with injected sources
    injected_exposure = injected_output.output_exposure
    return injected_exposure

def main_inject_stamp(
        REPO: str,
        collections: str | list[str],
        loc: list | tuple,
        band: str,
        stamp_paths: str | list[str],
        mags: list[float],
        ra_list: list[float],
        dec_list: list[float],    
        REPO_SAVE: str = '', 
        collection_save: str = "local_with_injection",
        run_name_save: str = "direct_injected_run",
        sky_coordinates=True,
        use_patch_area=False,
        detectors=None,
        timespan=None,
        visit_ids=None,
        num_select=None, 
        min_sep=0.0005,
        separation_spherical=True,
        from_data=False,
        keep_size=False,
        interp_order=3,
        update_wcs=True,
        warping_kernel='lanczos4',
        info_save_path=None,
        visit_name="visit_image",
        rot_name_save="stamp_rotated",
        remove_rotated_stamps=True,
        info=True,
        ref_wcs=None):
    """
    Inject artificial sources (stamps) into multiple LSST visit images.

    Parameters
    ----------
    butler : lsst.daf.butler.Butler
        Butler instance for accessing LSST data.
    loc : tuple
        If `sky_coordinates=True`: (ra, dec) in degrees.  
        If `sky_coordinates=False`: (tract, patch).
    band : str
        Filter band (e.g. "r", "i").
    stamp_paths : list of str
        File paths to stamp images (PSF-like cutouts to inject).
    mags : list of float
        Magnitudes of the sources to inject.
    ra_list, dec_list : list of float
        RA/Dec positions for the injected sources (degrees).
    sky_coordinates : bool, optional
        If True, loc is interpreted as (ra, dec).  
        If False, loc is interpreted as (tract, patch).
    use_patch_area : bool, optional
        If False (default), uses only the central coordinate of the patch.  
        If True, uses the full patch area (as in coadd construction).
    detectors : list of int, optional
        Restrict query to specific detectors.
    timespan : lsst.daf.butler.Timespan, optional
        Restrict query to a given time range.
    visit_ids : list of int, optional
        Restrict to specific visit IDs.
    num_select : int, optional
        Limit the number of visits selected (after sorting by SNR).
    min_sep : float or None, optional
        Minimum separation between injected sources [deg]. Default = 0.0005. 
        If None stamp in the same position is posible.
    separation_spherical : bool, optional
        If True, use spherical separation for spacing. Otherwise, Euclidean.
    from_data : bool
        if True used the function `apply_correction_from_data` else `apply_correction_from_exposureF`
    keep_size, interp_order, update_wcs, warping_kernel : passed to `apply_correction_to_stamp`
        Options for stamp rotation and resampling.
    info_save_path : str, optional
        Save address for data: {}, Default = None
    visit_name : str, optional
        Dataset type to fetch from Butler. Default "visit_image".
    rot_name_save : str, optional
        Name for the saved rotated stamps, Default: "stamp_rotated"
    remove_rotated_stamps : bool, optional
        If True (default), remove the rotated stamp FITS files after injection.  
        Set to False to keep them for inspection.
    info : bool, optional
        Print debug info.
    ref_wcs : lsst.afw.geom.SkyWcs
        Wcs used as reference to rotate stamps, recomended if working with
        multiple bands if None the first visit is used as reference.

    Returns
    -------
    injected_exposure : lsst.afw.image.ExposureF
        List of exposures with injected sources (in sorter order).

    Notes
    -----
    If `info_save_path` is defined, metadata and injection details will be 
    saved to `{info_save_path}.txt`.
    """
    # loading the butler
    if info: print(f"[INFO] Loading the butler...")
    try:
        butler = Butler(REPO, collections=collections)
    except Exception as e:
        if info: print(f"Could not have access to Butler registry on: {REPO}")
        raise

    # Resolve coordinates
    if sky_coordinates:
        ra_deg, dec_deg = loc
    else:
        tract, patch = loc
        ra_deg, dec_deg = patch_center(butler, tract, patch, sequential_index=True)
    loc = (ra_deg, dec_deg)
    if info: print(f"[INFO] Injection on sky coordinates: RA={ra_deg}, Dec={dec_deg}")

    # Identify visit images around location
    visit_calexp_dataset = visit_dataset(
        butler,
        band,
        loc,
        use_patch_area=use_patch_area,
        detectors=detectors,
        timespan=timespan,
        visit_ids=visit_ids
    )
    if info:
        print(f"[INFO] Found {len(visit_calexp_dataset)} visits for band={band}")
        start = time.time()
    
    if info_save_path:
        table_info = {}
        table_info['Parameters'] = {
            'visit_name': visit_name,
            'use_patch_area': use_patch_area,
            'points': list(zip(ra_list, dec_list)),
            'detectors': detectors,
            'timespan': timespan,
            'visit_ids': visit_ids
        }
        table_info['Visit_Data'] = {
            'RA': ra_deg, 'Dec': dec_deg,
            'Found': len(visit_calexp_dataset), 'band': band
            }

    # Load exposures, compute SNR + WCS
    snr_list, getWcs_list = [], []
    for ref in visit_calexp_dataset:
        try:
            exp = butler.get(visit_name, dataId=ref.dataId)
            snr_list.append(measure_quality(exp))
            getWcs_list.append(exp.getWcs())
            del exp  # free memory early
        except Exception as e:
            print(f"[ERROR] Could not load exposure {ref.dataId}: {e}")
    if info:
        print("END: Collect visit exposures and getWcs info")
        end = time.time()
        print(f"Execution time: {end - start:.3f} seconds")

    # Sort by SNR
    sorter_snr = np.argsort(snr_list)[::-1]  # descending
    sort_visit_calexp_dataset = [visit_calexp_dataset[i] for i in sorter_snr]
    sort_getWcs_list = [getWcs_list[i] for i in sorter_snr]

    # Optionally restrict number of visits
    if num_select is not None:
        sort_visit_calexp_dataset = sort_visit_calexp_dataset[:num_select]
        sort_getWcs_list = sort_getWcs_list[:num_select]
    if info:
        print(f"[INFO] Using {len(sort_visit_calexp_dataset)} visits after sorting and selection.")
    
    if info_save_path: table_info['snr'] = sorter_snr

    # Compute relative rotation angles w.r.t first visit
    if ref_wcs is None:
        ref_wcs = sort_getWcs_list[0]  # referential visit
    rotation_angle_list = [0.0]  # reference visit has 0 rotation
    rotation_angle_list.extend([
        wcs.getRelativeRotationToWcs(ref_wcs).asDegrees()
        for wcs in sort_getWcs_list[1:]
    ])
    if info:
        print(f"[INFO] Computed {len(rotation_angle_list)} rotation angles.")
    
    if info_save_path:
        table_info['rotation_angle'] = rotation_angle_list

    # Rotate stamps, build catalogs, and inject in one loop
    injected_exposures = []
    for i, angle in enumerate(rotation_angle_list):
        visit_id = sort_visit_calexp_dataset[i].dataId
        visit_image = butler.get(visit_name, dataId=visit_id)

        # Rotate all stamps for this visit
        rotated_stamps_path = [
            apply_correction_to_stamp(
                stamp_file,
                angle,
                output_path=f"{rot_name_save}_angle_{angle}_stamp_{j}.fits",
                keep_size=keep_size,
                interp_order=interp_order,
                update_wcs=update_wcs,
                c=1,
                from_data=from_data,
                warping_kernel=warping_kernel
            )
            for j, stamp_file in enumerate(stamp_paths)
        ]  # [rotate_stamp1_path, rotate_stamp2_path, ...]
        print(rotated_stamps_path)
        if info_save_path: table_info[f'rotated stamps path angle {str(angle)}'] = rotated_stamps_path

        # Create injection catalog
        inj_cat = create_crowded_injection_catalog(
            ra_list,
            dec_list,
            rotated_stamps_path,
            mags,
            min_sep=min_sep,
            separation_spherical=separation_spherical
            
        )

        # Perform injection
        try:
            inj_exp = inject_stamp(visit_image, inj_cat)

            if REPO_SAVE:
                save_visit_images(local_repo=REPO_SAVE,
                         collections=collection_save,
                         run_name=run_name_save,
                         injected_exposures=[inj_exp],
                         dataset_type = "visit_image",
                         visits=[visit_id],
                        )
            else:
                injected_exposures.append(inj_exp)
        except Exception as e:
            print(f"[ERROR] Injection failed for visit {visit_image.getInfo().getVisitInfo().getId()}: {e}")
        finally:
            if info_save_path: table_info.setdefault('data_Id', {})[f'{i}'] = dict(visit_id.to_simple())
            if remove_rotated_stamps:
                for path in rotated_stamps_path:
                    if os.path.exists(path):
                        os.remove(path)
                
    if info: print("[INFO] Injection complete.")

    if info_save_path:
        # Make the directory if it doesn't exist
        dir_name = os.path.dirname(info_save_path)
        if dir_name:  # avoid make a folder if info_save_path is just a filename without a folder
            os.makedirs(dir_name, exist_ok=True)

        # Save the JSON file
        with open(info_save_path + '.txt', "w") as f:
            json.dump(table_info, f, indent=4, default=make_serializable)

    return injected_exposures
