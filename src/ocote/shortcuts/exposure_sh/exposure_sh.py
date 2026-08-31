# vera rubin v1.0
# exposure.exposure.py

import lsst.geom as geom
import numpy as np
import subprocess
import pathlib
import os, sys

from lsst.daf.butler import Butler, DatasetRef, CollectionType
from lsst.afw.image import ExposureF
from astropy.io import fits


# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ...utils.tools.tools import setup_logger

##################################################################

# Low-level helpers
# ---------------------------------------------------------------------
def load_exposures(items):
    """
    Load a mixed list of:
      - FITS image paths
      - FITS stamps (with optional MASK extension)
      - LSST ExposureF file paths
      - ExposureF objects

    Returns a list of dictionaries with standardized content:
    {
        "type": "fits" or "lsst",
        "data": np.ndarray,
        "mask": np.ndarray(bool),
        "header": fits.Header or None,
        "exposure": ExposureF or None
    }
    """
    results = []
    for item in items:
        # ExposureF object already given
        if "ExposureF" in str(type(item)):
            exp = item
            img = exp.getMaskedImage().getImage().getArray()
            mask = np.isfinite(img)
            results.append({"type": "lsst", "data": img,
                "mask": mask, "header": None, "exposure": exp})
            continue

        # Case: String → must be a file
        if isinstance(item, str):
            if not os.path.exists(item):
                raise FileNotFoundError(f"{item} not found.")

            # Look for FITS by extension
            if item.lower().endswith(".fits") or item.lower().endswith(".fits.gz"):
                try:
                    with fits.open(item) as hdul:
                        data = hdul[0].data
                        header = hdul[0].header.copy()

                        # Optional MASK extension
                        if "MASK" in [hdu.name for hdu in hdul]:
                            mask = hdul["MASK"].data.astype(bool)
                        else:
                            mask = np.isfinite(data)

                    results.append({"type": "fits", "data": data, "mask": mask,
                        "header": header, "exposure": None})
                    continue

                except Exception:
                    # If FITS loading fails, try LSST ExposureF
                    pass

            # Try LSST ExposureF
            try:
                exp = ExposureF(item)
                img = exp.getMaskedImage().getImage().getArray()
                mask = np.isfinite(img)
                results.append({"type": "lsst", "data": img, "mask": mask,
                    "header": None, "exposure": exp})
                continue
            except Exception as e:
                raise RuntimeError(f"Could not interpret file {item} as FITS or ExposureF: {e}")
        # Anything else
        else:
            raise TypeError("Items must be FITS paths, ExposureF paths, or ExposureF objects.")
    return results

def save_exposure(
        injected_exposure: ExposureF | list[ExposureF],
        list_DatasetRef: list[DatasetRef],
        LOCAL_REPO: str = None,
        run_collection: str = None,
        use_butler: bool = False,
        output_root: str = None,
        overwrite: bool = True,
        LOGDIR: str = "/logs"):
    """
    Save a list of ExposureF objects either into a Butler repository  or as FITS files in a local directory.
    """

    # checking
    if isinstance(injected_exposure, ExposureF):
        injected_exposure = [injected_exposure]

    # Logging
    log_path = pathlib.Path(LOGDIR)
    log_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["chmod", "ug+rw", LOGDIR], check=True)

    logfile = log_path / "pipeline.log"
    logger = setup_logger(str(logfile))
    logger.info("Starting exposure-saving pipeline")

    # SAVE USING BUTLER
    if use_butler:
        logger.info("Saving using Butler")

        if LOCAL_REPO is None:
            raise ValueError("LOCAL_REPO is required when use_butler=True")

        if len(injected_exposure) != len(list_DatasetRef):
            raise ValueError("Length mismatch between exposures and DatasetRefs")

        try:
            lbutler = Butler(LOCAL_REPO, writeable=True)
            lreg = lbutler.registry
        except Exception:
            logger.exception(f"Could not open repo: {LOCAL_REPO}")
            raise

        # Register run collection if needed
        if run_collection:
            logger.info(f"Using RUN collection: {run_collection}")
            existing_run_collections = lreg.queryCollections()
            if run_collection not in existing_run_collections:
                lreg.registerCollection(run_collection, CollectionType.RUN)
                logger.info(f"Registered new RUN collection {run_collection}")
            else:
                logger.info(f"RUN collection {run_collection} already exists")

        # Open butler writer
        bw = Butler(LOCAL_REPO, writeable=True, run=run_collection)

        # Loop save
        for exp, ref in zip(injected_exposure, list_DatasetRef):
            try:
                dataId = ref.dataId
                dataset = ref.datasetType.name
                bw.put(exp, dataset, dataId)
                logger.info(f"Saved {dataset} {dataId} into collection '{run_collection}'")
            except Exception:
                logger.exception(f"FAILED saving {ref}")
                raise
        logger.info("Finished saving in Butler")

    # SAVE AS FITS FILES
    if output_root:
        os.makedirs(output_root, exist_ok=True)
        logger.info(f"Saving FITS files into: {output_root}")

        for exp, ref in zip(injected_exposure, list_DatasetRef):
            dataId = ref.dataId
            band = dataId.get("band", "x")
            visit_id = int(dataId.get("visit", 0))

            file_name = f"{band}_{visit_id:03d}.fits"
            file_path = os.path.join(output_root, file_name)

            if os.path.exists(file_path) and not overwrite:
                logger.error(f"File exists and overwrite=False: {file_path}")
                raise FileExistsError(f"Cannot overwrite {file_path}")

            exp.writeFits(file_path)
            logger.info(f"Saved FITS: {file_path}")

        logger.info("Finished saving FITS files")

    logger.info("Pipeline finished successfully")
    return True


# Medium-level helpers
# ---------------------------------------------------------------------
def normalize_exposures(exp_ref, exp_coadd, method="rescale"):
    """
    Normalize two LSST Exposure images to the same intensity range,
    returning full ExposureF objects with metadata preserved.

    Parameters
    ----------
    exp_ref : lsst.afw.image.ExposureF
        Reference exposure
    exp_coadd : lsst.afw.image.ExposureF
        Coadd exposure
    method : str, optional
        Normalization method:
        - "rescale": Rescale intensity of each image independently to [0,1]
        - "global_rescale": Rescale both using the global min and max
        - "zscore": Normalize to zero mean and unit variance

    Returns
    -------
    exp_ref_norm : lsst.afw.image.ExposureF
        Normalized reference exposure
    exp_coadd_norm : lsst.afw.image.ExposureF
        Normalized coadd exposure
    """

    # Convert Exposure -> NumPy arrays
    img_ref = exp_ref.getImage().getArray()
    img_coadd = exp_coadd.getImage().getArray()

    if method == "rescale":
        ref_norm = (img_ref - np.min(img_ref)) / (np.max(img_ref) - np.min(img_ref))
        coadd_norm = (img_coadd - np.min(img_coadd)) / (np.max(img_coadd) - np.min(img_coadd))

    elif method == "global_rescale":
        global_min = min(np.min(img_ref), np.min(img_coadd))
        global_max = max(np.max(img_ref), np.max(img_coadd))
        ref_norm = (img_ref - global_min) / (global_max - global_min)
        coadd_norm = (img_coadd - global_min) / (global_max - global_min)

    elif method == "zscore":
        ref_norm = (img_ref - np.mean(img_ref)) / np.std(img_ref)
        coadd_norm = (img_coadd - np.mean(img_coadd)) / np.std(img_coadd)

    else:
        raise ValueError("Invalid method. Choose 'rescale', 'global_rescale', or 'zscore'.")

    # Build normalized ExposureF with metadata preserved
    def build_normalized_exposure(exp_original, norm_array):
        # Make a deep copy of the original exposure
        exp_copy = exp_original.clone()

        # Replace only the image plane with normalized values
        exp_copy.getImage().getArray()[:, :] = norm_array.astype(np.float32)

        return exp_copy

    exp_ref_norm = build_normalized_exposure(exp_ref, ref_norm)
    exp_coadd_norm = build_normalized_exposure(exp_coadd, coadd_norm)

    return exp_ref_norm, exp_coadd_norm

def exposure_to_fits_datahdr(exposure):
    """
    Convert an LSST Exposure to FITS-like (data, header).

    Parameters
    ----------
    exposure : `lsst.afw.image.Exposure`
        Input exposure.

    Returns
    -------
    data : 2D numpy.ndarray
        Image array from the exposure.
    hdr : astropy.io.fits.Header
        FITS header including WCS metadata.
    """
    from astropy.io import fits

    # Extract image array
    mi = exposure.getMaskedImage()
    data = mi.getImage().getArray()

    # Build WCS header
    wcs = exposure.getWcs()
    hdr = fits.Header()
    hdr.update(wcs.getFitsMetadata())

    return data, hdr

def cutout_exposure(ref_exposure, center_coord, radius_pixels, info=True):
    """
    Cut out an LSST exposure centered on a celestial position with a given radius.
    If the cutout exceeds the image boundaries, missing regions are filled with zeros.
    Updates the WCS of the cutout to remain consistent.

    Parameters
    ----------
    ref_exposure : `lsst.afw.image.Exposure`
        Input exposure.
    center_coord : `lsst.afw.coord.Coord`
        Cutout center in celestial coordinates.
    radius_pixels : float
        Radius of the cutout in pixels.

    Returns
    -------
    cutout_exp : `lsst.afw.image.Exposure`
        Cutout exposure with updated WCS.
    """
    import lsst.afw.image as afwImage

    wcs = ref_exposure.getWcs()
    bbox = ref_exposure.getBBox()

    # Convert celestial center to pixel coordinates
    center_point = wcs.skyToPixel(center_coord)

    # Desired cutout BBox
    size = int(2 * radius_pixels)
    min_x = int(center_point.getX() - radius_pixels)
    min_y = int(center_point.getY() - radius_pixels)
    desired_bbox = geom.Box2I(geom.Point2I(min_x, min_y), geom.Extent2I(size, size))

    # Checking if box is subset of desired_bbox
    # when this happened intersect_bbox is clipped to box
    intersect_bbox = desired_bbox.clippedTo(bbox)
    is_subset = (intersect_bbox != bbox)

    if is_subset:
        # Case when intersect_bbox is subset of bbox
        x0, y0 = 0, 0
    else:
        # Case when bbox is subset of intersect_bbox
        x0 = intersect_bbox.getMinX() - desired_bbox.getMinX()
        y0 = intersect_bbox.getMinY() - desired_bbox.getMinY()

    # Create empty arrays for image, mask, and variance
    dtype = ref_exposure.getMaskedImage().getImage().getArray().dtype
    empty_image = np.zeros((size, size), dtype=dtype)
    empty_mask = np.zeros((size, size), dtype=np.uint16)
    empty_variance = np.zeros((size, size), dtype=dtype)

    # Copy image, mask, and variance from the original
    mi = ref_exposure.getMaskedImage()
    empty_image[y0:y0 + intersect_bbox.getHeight() - 1, x0:x0 + intersect_bbox.getWidth() - 1] = \
            mi.getImage().getArray()[intersect_bbox.getMinY():intersect_bbox.getMaxY(),
                                 intersect_bbox.getMinX():intersect_bbox.getMaxX()]
    empty_mask[y0:y0 + intersect_bbox.getHeight() - 1, x0:x0 + intersect_bbox.getWidth() - 1] = \
            mi.getMask().getArray()[intersect_bbox.getMinY():intersect_bbox.getMaxY(),
                                intersect_bbox.getMinX():intersect_bbox.getMaxX()]
    empty_variance[y0:y0 + intersect_bbox.getHeight() - 1, x0:x0 + intersect_bbox.getWidth() - 1] = \
            mi.getVariance().getArray()[intersect_bbox.getMinY():intersect_bbox.getMaxY(),
                                    intersect_bbox.getMinX():intersect_bbox.getMaxX()]
        
    # Create MaskedImage and Exposure
    mi_cutout = afwImage.MaskedImageF(empty_image.shape[1], empty_image.shape[0])
    mi_cutout.getImage().getArray()[:, :] = empty_image
    mi_cutout.getMask().getArray()[:, :] = empty_mask
    mi_cutout.getVariance().getArray()[:, :] = empty_variance

    cutout_exp = afwImage.ExposureF(mi_cutout)

    # Shift WCS
    shift = geom.Extent2D(-desired_bbox.getMinX(), -desired_bbox.getMinY())
    shifted_wcs = wcs.copyAtShiftedPixelOrigin(shift)
    cutout_exp.setWcs(shifted_wcs)
    
    if info:
        center_point_cutout = cutout_exp.getWcs().skyToPixel(center_coord)
        print("Referential point in exposure:", center_point)
        print("Desired bbox:", desired_bbox)
        print("Intersection bbox:", intersect_bbox)
        print("Referential point in cutout:", center_point_cutout)
        print("Cutout shape:", cutout_exp.getMaskedImage().getImage().getArray().shape)

    return cutout_exp