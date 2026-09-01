# vera rubin v1.0
# tools.tools.py
# set of utility functions for various tasks

import numpy as np
import subprocess
import logging
import sys

from lsst.daf.butler import Butler
from astropy.time import Time


###################################################################################################
def mjds_to_dates(mjd_list):
    """
    Convert a list of MJDs (Modified Julian Dates) to UTC calendar dates.
    """
    mjd_list = np.array(mjd_list)
    times = Time(mjd_list, format='mjd', scale='tai')
    return [t.to_datetime().date() for t in times]

def get_butler_location(butler: Butler) -> str | bool:
    """Return repository path for a local Butler or parsed location for remote Butler."""
    try:
        return butler.repo   # Local Butler
    except AttributeError:
        import re
        # Remote Butler: parse str(butler)
        s = str(butler)
        match = re.search(r"RemoteButler\((.+?)\)", s)
        if match:
            return match.group(1)
        else:
            return False  # Could not determine location

def _run(cmd: list[str], logger: logging.Logger = None) -> subprocess.CompletedProcess:
    """
    Run a subprocess command, log stdout/stderr and raise if it fails.
    Returns the CompletedProcess on success.
    """
    msg = "[CMD] " + " ".join(cmd)
    if logger:
        logger.info(msg)
    else:
        print(msg)

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if logger:
            logger.info(result.stdout.strip())
            if result.stderr.strip():
                logger.warning(result.stderr.strip())
        else:
            print(result)
    except subprocess.CalledProcessError as e:
        if logger:
            logger.error(f"Command failed: {e}")
            logger.error(e.stderr)
        else:
            print("Command failed:", e)
            print(e.stderr)
        raise

def setup_logger(logfile_path: str, name: str = 'pipeline.log') -> logging.Logger:
    """Create a logger that writes DEBUG to file and INFO to console."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # prevent duplicate handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatter with timestamp
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")

    # Log to file
    file_handler = logging.FileHandler(logfile_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Log to console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def progressbar(current_value, total_value, bar_length=20, progress_char='#'): 
    """
    Display a progress bar in the console.
    
    Parameters
    ----------
    current_value : int
        Current progress value.
    total_value : int
        Total value for completion.
    bar_length : int, optional
        Length of the progress bar.
    progress_char : str, optional
        Character used to fill the progress bar.
    """
    if total_value == 0:
        print("Error: total_value cannot be 0")
        return
    
    # Calculate the percentage and progress
    percentage = int((current_value / total_value) * 100)
    progress = int((bar_length * current_value) / total_value)
    
    # Build the progress bar string
    loadbar = f"Progress: [{progress_char * progress}{'.' * (bar_length - progress)}] {percentage}%"
    
    # Print the progress bar (overwrite line until finished)
    end_char = '\r' if current_value < total_value else '\n'
    print(loadbar, end=end_char)



## AlardLuptonSubtractTask

def diff_AlardLupton(templateExposure, scienceExposure, warp=True):
    """
    The idea was take from:
    https://community.lsst.org/t/issues-with-image-subtraction/10429
    """
    import numpy as np
    import lsst.afw.table as afwTable
    import lsst.daf.base as dafBase
    from lsst.meas.algorithms.detection import SourceDetectionTask
    from lsst.meas.deblender import SourceDeblendTask
    from lsst.meas.base import SingleFrameMeasurementTask
    from lsst.ip.diffim import AlardLuptonSubtractTask, AlardLuptonSubtractConfig
    
    # Remove the bit mask
    print("===> Cleaning masks")
    template_masks = set(templateExposure.mask.getMaskPlaneDict())
    scienceExposure_masks = set(scienceExposure.mask.getMaskPlaneDict())
    common_masks = template_masks & scienceExposure_masks

    for exp in [templateExposure, scienceExposure]:
        for mask in list(exp.mask.getMaskPlaneDict().keys()):
            if mask not in common_masks:
               print(f"masks: {mask}")
               try:
                   exp.mask.removeAndClearMaskPlane(mask)
               except Exception:
                   pass
    
    # Make a schema
    # Identified sources on the scienceExposure. 
    # This catalog is used to select sources to perform 
    # the AL PSF matching on stamp images around them.
    schema = afwTable.SourceTable.makeMinimalSchema()
    schema.addField("coord_raErr", type="F")
    schema.addField("coord_decErr", type="F")
    schema.addField("detect_isPrimary", type="F")  # Flag
    schema.addField("sky_source", type="Flag")
    algMetadata = dafBase.PropertyList()

    # Detection task
    detectConfig = SourceDetectionTask.ConfigClass()
    detectConfig.thresholdValue = 5
    detectConfig.thresholdType = "stdev"
    detectTask = SourceDetectionTask(schema=schema, config=detectConfig)

    # here because schema is modify by detectTask.run
    deblendTask = SourceDeblendTask(schema=schema)
    
    measConfig = SingleFrameMeasurementTask.ConfigClass()
    measTask = SingleFrameMeasurementTask(schema=schema, config=measConfig, algMetadata=algMetadata)

    print("===> Run detection")
    tab = afwTable.SourceTable.make(schema)
    result = detectTask.run(tab, scienceExposure)
    sources = result.sources

    # Deblend + Measurement
    print("===> Run Deblend and Measurement")
    deblendTask.run(scienceExposure, sources)
    measTask.run(measCat=sources, exposure=scienceExposure)
    sources = sources.copy(True)

    # Sky sources flag
    print("===> Selecting sky sources")
    select_sky_sources(sources, schema)
    
    # Warp the templateExposure to match with scienceExposure (imagen + PSF)
    if warp:
        print("===> Warping")
        warp_templateExposure = warp_img(
            ref_img=scienceExposure,
            img_to_warp=templateExposure)
    else:
        warp_templateExposure = templateExposure

    # Subtraction task 
    print("===> Subtracting")
    # https://pipelines.lsst.io/py-api/lsst.ip.diffim.AlardLuptonSubtractTask.html#lsst.ip.diffim.AlardLuptonSubtractTask.run
    config = AlardLuptonSubtractConfig()
    subtractTask = AlardLuptonSubtractTask(config=config)
    
    result = subtractTask.run(
        template=warp_templateExposure,
        science=scienceExposure,
        sources=sources
    )
    diff = result.difference
    return diff
    
def warp_img(ref_img, img_to_warp, warping_kernel="lanczos5"):
    """
    Warp an exposure (image + PSF) onto the coordinate system of another.
    """
    import copy
    import lsst.afw.math as afwMath
    import lsst.afw.geom as afwGeom
    import lsst.meas.algorithms as measAlg

    # warp imagen
    config = afwMath.Warper.ConfigClass()
    config.warpingKernelName = warping_kernel
    warper = afwMath.Warper.fromConfig(config)

    bbox = ref_img.getBBox()
    warpedExp = warper.warpExposure(ref_img.wcs, img_to_warp, destBBox=bbox)
    warpedExp = copy.deepcopy(warpedExp)

    # Warp PSF
    psf = img_to_warp.getPsf()
    if psf is not None:
        xyTransform = afwGeom.makeWcsPairTransform(img_to_warp.getWcs(),
                                                   ref_img.getWcs())
        warped_psf = measAlg.WarpedPsf(psf, xyTransform)
        warpedExp.setPsf(warped_psf)
    return warpedExp

def select_sky_sources(sources, schema, max_sky=500):
    import random

    sky_source_key = schema["sky_source"].asKey()
    selected = []
    for record in sources:
        try:
            flux = record.get("base_PsfFlux_instFlux")
            flux_err = record.get("base_PsfFlux_instFluxErr")

            snr = flux / flux_err if flux_err > 0 else 0

            psf_flag = record.get("base_PsfFlux_flag")
            saturated = record.get("base_PixelFlags_flag_saturated")
            bad = record.get("base_PixelFlags_flag_bad")
            edge = record.get("base_PixelFlags_flag_edge")
            nchild = record.get("deblend_nChild")
            
            is_sky = (
                abs(snr) < 20 and      # 2 stricto
                not saturated and
                not bad and
                not edge and
                nchild == 0
            )
        except Exception:
            is_sky = False

        record.set(sky_source_key, is_sky)
        if is_sky:
            selected.append(record)

    print(f"Sky sources seleccionadas: {len(selected)}")

    # FALLBACK SI NO HAY
    if len(selected) == 0:
        print("No sky sources → usando fallback aleatorio")
        n = len(sources)
        fallback_idx = random.sample(range(n), max(5, int(0.2 * n)))

        for i, record in enumerate(sources):
            record.set(sky_source_key, i in fallback_idx)
    elif len(selected) > max_sky:
        # limitar número
        keep = set(random.sample(range(len(selected)), max_sky))
        for i, record in enumerate(selected):
            if i not in keep:
                record.set(sky_source_key, False)