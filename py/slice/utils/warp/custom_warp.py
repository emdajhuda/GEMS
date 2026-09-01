# vera rubin v1.0
# coadd.custom_warp.py

#import subprocess
import lsst.geom
import logging
import os, sys
#import pathlib

from lsst.drp.tasks.make_direct_warp import MakeDirectWarpTask, MakeDirectWarpConfig, WarpDetectorInputs
from lsst.pipe.tasks.selectImages import WcsSelectImagesTask
from lsst.pipe.tasks.coaddBase import makeSkyInfo
from lsst.skymap import TractInfo, PatchInfo
from lsst.daf.butler import Butler, DatasetRef, DatasetType, CollectionType
from collections import defaultdict
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ...py.visit_selection.visit_selection import visit_dataset
from ..tools.tools import setup_logger

###################################################################################################

# Top-level
# ---------------------------------------------------------------------
def custom_warp(
    REPO: str,
    collections: str | list[str],
    loc: list | tuple,
    run_name: str = "direct_warp_run",
    name_chain: str = "local_with_warps",
    band: str = "u",
    instrument: str = "LSSTComCam",
    datasetType: str = "visit_image",
    skymap_name: str = "lsst_cells_v1",
    # Optional advanced features
    filter_by_patch: bool = True,        # use tract/patch to restrict visits
    filter_by_region: bool = False,      # use visit_detector_region (if available)
    detectors: list = None,              # allowed detectors
    LOGDIR: str = "warps",
    out: bool = True,
):
    """
    Custom warping function for LSST coaddition.

    This function selects visits overlapping a specified patch and runs the MakeDirectWarpTask
    to generate warped exposures for coaddition.
    """
    # Setup logging directory and logger
    log_path = Path.cwd() / LOGDIR
    log_path.mkdir(parents=True, exist_ok=True)
    # subprocess.run(["chmod", "ug+rw", LOGDIR], check=True)

    logfile = log_path / "warp.log"
    logger = setup_logger(str(logfile))
    logger.info(f"Created LOGDIR at {LOGDIR}")
    
    logger.info(f"Starting warping process...")

    # select visits
    logger.info(f"Selecting visits overlapping the patch...")
    visit_refs, tract_info, patch_info = select_visits(
        REPO=REPO,
        collections=collections,
        loc=loc,
        band=band,
        instrument=instrument,
        datasetType=datasetType,
        skymap_name=skymap_name,
        filter_by_patch=filter_by_patch,
        filter_by_region=filter_by_region,
        detectors=detectors,
        logger=logger
    )

    # run warping task
    logger.info(f"Running warping task for selected visits...")
    visit_warps = runDirectWarpTask(
        REPO=REPO,
        run_name=run_name,
        name_chain=name_chain,
        collections=collections,
        dataset_refs=visit_refs,
        tract_info=tract_info,
        patch_info=patch_info,
        datasetType=datasetType,
        skymap_name=skymap_name,
        use_visit_summary=True,
        out=out,
        logger=logger
    )

    logger.info(f"Warping process completed.")
    return visit_warps, visit_refs

# Low-level helpers
# ---------------------------------------------------------------------
def select_visits(
    REPO: str,
    collections: str | list[str],
    loc: list | tuple,
    band: str = "u",
    instrument: str = "LSSTComCam",
    datasetType: str = "visit_image",
    skymap_name: str = "lsst_cells_v1",
    # Optional advanced features
    filter_by_patch: bool = True,        # use tract/patch to restrict visits
    filter_by_region: bool = False,      # use visit_detector_region (if available)
    detectors: list = None,              # allowed detectors
    logger: logging.Logger = None,):
    """
    Return DatasetRefs for images overlapping the patch.
    https://github.com/lsst/pipe_tasks/blob/main/python/lsst/pipe/tasks/selectImages.py
    """
    ra_deg, dec_deg = loc
    point_sky = lsst.geom.SpherePoint(ra_deg, dec_deg, lsst.geom.degrees)

    # loading the butler
    logger.info(f"Loading the butler...")
    try:
        butler = Butler(REPO, collections=collections)
    except Exception as e:
        if logger: logger.exception(f"Could not have access to Butler registry on: {REPO}")
        raise

    # Load sky map
    sky_map = butler.get("skyMap", skymap=skymap_name)
    tract_info = sky_map.findTract(point_sky)
    patch_info = tract_info.findPatch(point_sky)

    tract_id = tract_info.getId()
    patch_index = patch_info.getIndex()
    if logger: logger.info(f"[SELECT] Tract={tract_id}, Patch={patch_index}")
    
    # Query all visits for this band + instrument
    visit_refs = visit_dataset(butler=butler,
                               band=band, loc_data=loc,
                               use_patch_area=filter_by_patch,
                               filter_by_region=filter_by_region,
                               detectors=detectors, 
                               instrument=instrument)
    if logger: logger.info(f"[SELECT] Candidate visits: {len(visit_refs)}")

    # Load WCS + BBox to filter images by footprint intersection
    wcsList, bboxList, validRefs = [], [], []
    for ref in visit_refs:
        try:
            exp = butler.get(datasetType, dataId=ref.dataId)
            wcsList.append(exp.getWcs())
            bboxList.append(exp.getBBox())
            validRefs.append(ref)
        except Exception as e:
            if logger: logger.exception(f"[WARN] Failed reading {ref.dataId}: {e}")

     # Prepare polygon vertices
    poly = patch_info.getOuterSkyPolygon()
    coordList = [lsst.geom.SpherePoint(v) for v in poly.getVertices()]
    
    # Filter with WCS intersection
    task = WcsSelectImagesTask()
    indices = task.run(wcsList=wcsList, bboxList=bboxList, coordList=coordList, dataIds=validRefs,)
    visit_refs = [validRefs[i] for i in indices]
    if logger: logger.info(f"[SELECT] Overlapping visits: {len(visit_refs)}")

    return visit_refs, tract_info, patch_info

# High-level operations
# ---------------------------------------------------------------------
def runDirectWarpTask(
    REPO: str,
    collections: str | list[str],
    dataset_refs: list[DatasetRef] | tuple[DatasetRef],
    tract_info: TractInfo,
    patch_info: PatchInfo,
    run_name: str = "direct_warp_run",
    name_chain: str = "local_with_warps",
    datasetType: str = "visit_image",
    skymap_name: str = "lsst_cells_v1",
    use_visit_summary: bool = True,
    out: bool = False,
    logger: logging.Logger | None = None,
    ) -> dict[int, list] | None:
    """
    Run MakeDirectWarpTask per visit

    Comment:
    This function is an adaptation of runQuantum tha appear on the class MakeDirectWarpTask:
    https://github.com/lsst/drp_tasks/blob/main/python/lsst/drp/tasks/make_direct_warp.py

    Returns:
    dict[visit_id, list[ExposureF]] or None
        Warps per visit if out=True, else None.
    """
    
    # loading the butler
    logger.info(f"Loading the butler with the respectively RUN...")
    butler = setup_run_and_chain(repo=REPO, run_name=run_name,
                                 base_chain=collections, new_chain=name_chain, logger=logger)

    if logger: logger.info(f"[INF] Build WarpDetectorInputs")
    
    # Build WarpDetectorInputs (visit → detector → inputs)
    inputs: dict[int, dict[int, WarpDetectorInputs]] = defaultdict(dict)   # visit_id -> [Detector ID -> WarpDetectorInputs]
    registry = butler.registry
    
    for ref in dataset_refs:
        handle = butler.getDeferred(datasetType, dataId=ref.dataId)  # lazy copy (handle)
        # exp = butler.get(datasetType, dataId=ref.dataId)  # Load exposure for this ref

        expanded_data_id = registry.expandDataId(ref.dataId)  # EXPANDED dataId is REQUIRED for IdGenerator
        
        visit_id = handle.dataId["visit"]  # Visit ID
        det_id = handle.dataId['detector'] # Detector ID

        # Store in structures
        inputs[visit_id][det_id] = WarpDetectorInputs(
            exposure_or_handle=handle,
            data_id=expanded_data_id,
            background_revert=None,
            background_apply=None,
            background_ratio_or_handle=None
        )
    if not inputs:
        logger.exception("[ERROR] No input warps provided for co-addition")
        raise

    if logger: logger.info(f"[INF] Warping visits: {sorted(inputs.keys())}")

    # Load SkyMap
    sky_map = butler.get("skyMap", skymap=skymap_name)
    
    # Configure task
    config = MakeDirectWarpConfig()
    config.doSelectPreWarp = False
    
    # Leave visit_summary enabled (default DRP behavior)
    if not use_visit_summary:
        config.useVisitSummaryPsf = False
        config.useVisitSummaryPhotoCalib = False
        config.useVisitSummaryWcs = False
    task = MakeDirectWarpTask(config=config)
    
    # Output container
    visit_warps = {} if out else None
    
    # Run per visit (IMPORTANT: SkyInfo recreated every time for bug)
    for visit_id, detector_inputs in inputs.items():
        if logger: logger.info(f"Processing visit {visit_id}")
        
        # Recreate SkyInfo
        sky_info = makeSkyInfo(sky_map, tract_info.getId(), patch_info.getIndex())
        
        # Use first detector to fetch visit_summary
        first_input = next(iter(detector_inputs.values()))
        visit_summary = butler.get('visit_summary', dataId=first_input.data_id)

        # Run warp
        results = task.run(inputs=detector_inputs,
                           sky_info=sky_info,
                           visit_summary=visit_summary,)

        if out:
            if logger: logger.info(f"WARP SAVED: visit={visit_id}")
            visit_warps[visit_id] = results.warp
        else:
            # Ensure datasetType exists
            ensure_directWarp_datasetType(butler)
            
            # Save each detector warp
            dataId_out = {}
            dataId_out["instrument"] = first_input.data_id.get('instrument')
            dataId_out["visit"] = first_input.data_id.get('visit')
            # dataId_out["detector"] = first_input.data_id.get('detector')
            # dataId_out["band"] = first_input.data_id.get('band')
            dataId_out["skymap"] = skymap_name
            dataId_out["tract"] = int(tract_info.getId())
            dataId_out["patch"] = int(patch_info.getSequentialIndex())
            
            butler.put(results.warp, "directWarp", dataId_out)

            if logger:
                logger.info(
                    f"[PUT] directWarp saved: visit={visit_id}, "
                    f"detector={det_id}, tract={dataId_out['tract']}, "
                    f"patch={dataId_out['patch']}"
                    )

        # Explicit cleanup
        del results
        del visit_summary
        del sky_info

    # Final cleanup
    inputs.clear()
    del inputs
    del sky_map
    
    return visit_warps if out else None

def ensure_directWarp_datasetType(butler):
    registry = butler.registry
    universe = registry.dimensions

    if "directWarp" in {dt.name for dt in registry.queryDatasetTypes()}:
        return

    dimensions = universe.conform(
        ("instrument", "visit", # "detector", 
         "skymap", "tract", "patch")
    )
    
    dt = DatasetType(
        name="directWarp",
        dimensions=dimensions,
        storageClass="ExposureF",
    )

    registry.registerDatasetType(dt)

def setup_run_and_chain(
    repo: str,
    run_name: str = "direct_warp_run",
    base_chain: str = "local_main_chain",
    new_chain: str = "local_with_warps",
    logger: logging.Logger | None = None,
):
    """
    Create a personal RUN collection and a CHAINED collection including it.

    Parameters
    ----------
    repo : str
        Butler repository path.
    run_name : str
        Name of the personal RUN.
    base_chain : str
        Existing chained collection (e.g. local_main_chain).
    new_chain : str
        Name of new chained collection to create.

    Returns
    -------
    Butler
        Butler instance configured with:
            collections=new_chain
            run=user/run_name
    """

    butler = Butler(repo, writeable=True)
    registry = butler.registry

    # Create RUN if not exists
    ############################
    existing = registry.queryCollections()

    if run_name not in existing:
        if logger: logger.info(f"[CREATE] RUN collection: {run_name}")
        registry.registerCollection(run_name, CollectionType.RUN)
    else:
        if logger: logger.info(f"[OK] RUN already exists: {run_name}")

    # Create CHAINED if not exists
    ############################
    if new_chain not in existing:
        if logger: logger.info(f"[CREATE] CHAINED collection: {new_chain}")
        registry.registerCollection(new_chain, CollectionType.CHAINED)
    else:
        if logger: logger.info(f"[OK] CHAINED already exists: {new_chain}")

    # Set chain structure (RUN first, base_chain after)
    # --------------------------------------------------
    registry.setCollectionChain(
        new_chain,
        [run_name, base_chain] if base_chain else run_name
    )

    # Return fully configured Butler
    ############################
    configured_butler = Butler(
        repo,
        collections=new_chain,
        run=run_name,
        writeable=True
    )

    if logger: logger.info("[READY] Butler configured for read/write")

    return configured_butler
