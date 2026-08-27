# vera rubin v1.0
# coadd.custom_coadd.py
import os, sys
import getpass
import json
import pandas
from lsst.daf.butler import Butler

from lsst.pipe.base.simple_pipeline_executor import SimplePipelineExecutor
from lsst.pipe.base import Pipeline

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from .Shortcuts.visit_sh.visit_sh import VisitSH, combine_visits_selected
from .Utils.sky.sky import tract_patch
from .Utils.plot.butler_plot import filt_plot
from .Utils.tools.tools import get_butler_location

###################################################################################################

# Low-level helpers
# ---------------------
def load_custom_coadd_from_file(info_txt_path):
    """
    Load custom coadd Butler using information from a text file.
    """
    from .Utils.butler.butler import ExpButler

    with open(info_txt_path, "r") as f:
        info = json.load(f)

    try:
        butler = Butler(config=info['repo_path'], collections=info['collection'])
        # butler = ExpButler(repository=info['repo_path'], collections=info['collection'])._create_butler()
    except Exception as e:
        raise

    results = {}
    for band in info['bands']:
        try:
            coadd = butler.get(
                info['coadd_type'],
                tract=info['tract'],
                patch=int(info['patch']),
                band=band,
                instrument=info['instrument'],
                skymap=info['skymap'],
                collections=info['collection']
            )
            results[band] = coadd
        except Exception as e:
            print(f"[WARNING] Could not load coadd for band {band}: {e}")

    return results

# higher-level helpers
# ------------------------
def custom_coadd_filter(loc_data: tuple,
                        bands: str = 'ugrizy', 
                        sky_coordinates: bool = True, 
                        butler: Butler = None,
                        repository: str = "dp1",
                        collections: str = "LSSTComCam/DP1",
                        skymap_name: str = "lsst_cells_v1",
                        type_coadd: str = 'deep_coadd',
                        statistics: set = {'std', 'mean'},
                        selection: dict = {'u': ['psfSigma', 'airmass'], 'g': ['psfSigma', 'airmass'], 'r': ['psfSigma', 'airmass'],
                                   'i': ['psfSigma', 'airmass'], 'z': ['psfSigma', 'airmass'], 'y': ['psfSigma', 'airmass']},
                        filt_cut: dict = {'u': None, 'g': None, 'r': None, 'i': None, 'z': None, 'y': None}, 
                        n_visits: dict = {'u': None, 'g': None, 'r': None, 'i': None, 'z': None, 'y': None},
                        plot: bool = False,
                        out: bool = True,
                        my_collection_name: str = 'custom_coadd',
                        BUTLER_SAVE_PATH: str = 'local_repo',
                        make_coadd = True,
                        ):
    """
    Run filtering and coaddition over multiple photometric bands.

    This function applies filtering criteria to visits per band using Visit.filt_visit,
    and optionally runs a custom coaddition pipeline for the selected visits.

    Returns
    -------
    visits_selected_list : list of pd.DataFrame
        Filtered visits per band.
    df_metrics_list : list of pd.DataFrame
        Computed statistics per band.
    coadd_results : dict (if out=True)
        Deep coadd results per band.
    """
    
    # Initialize Butler if not provided
    # ----------------------------
    if butler:
        butler = butler
    else:
        butler = Butler(repository, collections=collections)
    BUTLER_PATH = get_butler_location(butler)

    # Ensure bands is a list
    # ----------------------------
    bands = list(bands) if isinstance(bands, str) else bands
            
    # Visit filtering per band
    # ----------------------------
    visits_selected_list, df_metrics_list = [], []
    for band in bands:
        visit_instance = VisitSH(loc_data, band, butler=butler, sky_coordinates=sky_coordinates)
        df_metrics, visits_selected = visit_instance.filt_visit(
            statistics=statistics,
            type_coadd=type_coadd,
            selection=selection.get(band, []),
            filt_cut=filt_cut.get(band),
            n_visits=n_visits.get(band)
        )

        if plot:
            filt_plot(df_metrics, visits_selected, filt_cut.get(band),
              incr=1000, save=False)
        df_metrics_list.append(df_metrics)
        visits_selected_list.append(visits_selected)

    # Combine visits into single DataFrame
    visits_selected_comb = combine_visits_selected(visits_selected_list)

    # Run coadd if requested
    if make_coadd:
        coadd_results = custom_coadd_multiband(
            BUTLER_PATH,
            BUTLER_SAVE_PATH, 
            loc_data=loc_data,
            visits_selected=visits_selected_comb,
            bands=bands,
            skymap_name=skymap_name,
            remote_collection=collections,
            my_collection_name=my_collection_name,
            sky_coordinates=sky_coordinates,
            SAVE_FITS=False,
            out=out)
    
        return visits_selected_list, df_metrics_list, coadd_results

    else:
        return visits_selected_list, df_metrics_list

def custom_coadd_multiband(BUTLER_PATH: str,
                           BUTLER_SAVE_PATH: str,
                           loc_data: tuple,
                           visits_selected: pandas.DataFrame,
                           bands: list[str] = None,
                           skymap_name: str = "lsst_cells_v1",
                           remote_collection: str = "LSSTComCam/DP1",
                           my_collection_name: str = 'custom_coadd',
                           sky_coordinates: bool = True,
                           SAVE_FITS: bool = False,
                           out: bool = False,
                           meta_data_name: str = "custom_coadd_info"):
    """
    Run a custom multi-band coadd and optionally:
      - Save into an existing Butler repository
      - Create a new local Butler repository
      - Export results as FITS files
    """
    # Open butler
    _butler = Butler(BUTLER_PATH, collections=remote_collection)

    # Get tract and patch either from sky coords or directly
    my_tract, my_patch = tract_patch(_butler, loc_data[0], loc_data[1], sequential_index=True) if sky_coordinates else loc_data

    # Pipeline definition
    # ----------------------------
    drp_yaml_file = "$DRP_PIPE_DIR/pipelines/LSSTComCam/DRP-v2-compat.yaml"
    uri = drp_yaml_file + "#makeDirectWarp,assembleDeepCoadd,makePsfMatchedWarp,selectDeepCoaddVisits"
    pipeline = Pipeline.from_uri(uri)

    # Config overrides
    # https://pipelines.lsst.io/modules/lsst.pipe.tasks/tasks/lsst.pipe.tasks.make_direct_warp.MakeDirectWarpTask.html
    pipeline.addConfigOverride('makeDirectWarp', 'useVisitSummaryPsf', False)
    pipeline.addConfigOverride('makeDirectWarp', 'useVisitSummaryPhotoCalib', False)
    pipeline.addConfigOverride('makeDirectWarp', 'useVisitSummaryWcs', False)
    # DP1 visit_summary does not contain all PSF-quality fields
    # expected by PsfWcsSelectImagesTask in v30 (e.g. starEMedian).
    # Disable the pre-warp detector selection.
    pipeline.addConfigOverride('makeDirectWarp', 'doSelectPreWarp', False)
    pipeline.addConfigOverride('makeDirectWarp', 'connections.calexp_list', 'visit_image')

    # Bands auto-detection
    # ----------------------------
    bands = visits_selected['band'].unique() if bands is None else bands

    # Extract visit IDs for all bands
    visit_ids_all = []
    for band in bands:
        if band in visits_selected['band'].unique():
            visit_ids_band = visits_selected.query(f"band == '{band}'")['visit_id'].tolist()
            visit_ids_all.extend(visit_ids_band)

    if not visit_ids_all: raise ValueError("No visits to process.")

    # Construct query string for input dataset filtering
    visit_ids_str = "(" + ",".join(map(str, visit_ids_all)) + ")"
    query_string = (
        f"tract = {my_tract} AND patch = {my_patch} "
        f"AND visit IN {visit_ids_str} AND skymap = '{skymap_name}'"
    )

    # Executor
    # ----------------------------
    # Set up executor
    executor = SimplePipelineExecutor.from_pipeline(
        pipeline, butler=_butler, output=my_collection_name, where=query_string)
    
    # Transfer all inputs to a local data repository and set the executor to write outputs to it.
    # It created a local butler/repository if it does not exist.
    # https://pipelines.lsst.io/py-api/lsst.ctrl.mpexec.SimplePipelineExecutor.html#lsst.ctrl.mpexec.SimplePipelineExecutor.use_local_butler
    if os.path.exists(BUTLER_SAVE_PATH) and not os.path.exists(os.path.join(BUTLER_SAVE_PATH, "butler.yaml")):
        raise RuntimeError("BUTLER_SAVE_PATH exists but is not a Butler repo")
    out_butler = executor.use_local_butler(BUTLER_SAVE_PATH)

    # Run pipeline
    # ----------------------------
    try:
        executor.run(register_dataset_types=True)
    except Exception as e:
        raise RuntimeError(f"Pipeline execution failed: {e}")

    # Retrieve results
    # ----------------------------
    coadd_results = None
    if out or SAVE_FITS:
        coadd_results = {}
        for band in bands:
            try:
                coadd = out_butler.get(
                    'deep_coadd_predetection', tract=my_tract, patch=int(my_patch), band=band,
                    instrument='LSSTComCam', skymap=skymap_name, collections=executor.quantum_graph.metadata["output_run"]
                    )
                coadd_results[band] = coadd

                # Optional FITS export
                # ----------------------------
                if SAVE_FITS:
                    export_dir = BUTLER_SAVE_PATH or os.getcwd()
                    fits_name = (
                        f"deep_coadd_tract{my_tract}_patch{my_patch}_{band}.fits")
                    fits_path = os.path.join(export_dir, fits_name)

                    coadd.writeFits(fits_path)
                    print(f"[INFO] Exported FITS: {fits_path}")

            except Exception as e:
                print(f"[WARNING] Could not retrieve band {band}: {e}")
        
    # Save metadata file
    # ----------------------------
    metadata = {
        'repo_path': BUTLER_SAVE_PATH,
        'collection': executor.quantum_graph.metadata["output_run"],
        'coadd_type': 'deep_coadd_predetection',
        'tract': my_tract,
        'patch': str(my_patch),
        'bands': list(bands),
        'instrument': 'LSSTComCam',
        'skymap': skymap_name}

    meta_path = os.path.join(BUTLER_SAVE_PATH, meta_data_name + ".txt")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=4)
    print(f"[INFO] Metadata saved: {meta_path}")

    return coadd_results