
import pathlib
import logging
import os, sys
import subprocess

from lsst.daf.butler import Butler, DatasetType, CollectionType

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ..tools.tools import setup_logger, _run

class LocalButler:
    """
    Manages the interaction between a local repository and a remote repository.
    """

    REQUIRED_TYPES: set[str] = {
        "visit_image", "visit_summary", "visit_summary_schema", "visit_summary_metadata",
        "deep_coadd",
    }

    def __init__(self, local_repo: str, remote_repo: str, LOGDIR: str = "logs",):
        """
        Initialize the instance with local and remote repository references.
        param local_repo: Path or name of the local repository.
        :param remote_repo: URL or name of the remote repository.
        """

        self.local_repo = local_repo
        self.remote_repo = remote_repo
        self.logger = log_menseger(local_repo + LOGDIR, local_repo)
        

    def make_repo(self) -> None:
        """
        Creating an empty repo if requested
        """
        if os.path.exists(os.path.join(self.local_repo, "butler.yaml")):
            raise FileExistsError(f"Repository already exists: {self.local_repo}")

        os.makedirs(self.local_repo, exist_ok=True)
        self.logger.info(f"Creating Butler repo at {self.local_repo}")
        Butler.makeRepo(self.local_repo)
        return None
    
    def reg_instruments(self, visits_datasetRef, remote_collection: str = "LSSTComCam/DP1") -> None:
        """
        Register instruments (collect unique instrument names from DatasetRefs)
        """

        instruments: set[str] = {ref.dataId["instrument"] for ref in visits_datasetRef}
        self.logger.info(f"Registering instruments: {sorted(instruments)}")
        try:
            instrument_register_from_remote(
                local_repo=self.local_repo,
                remote_repo=self.remote_repo,
                instruments=instruments,
                remote_collection=remote_collection,
                logger=self.logger
            )
            self.logger.info("Instrument registration complete.")
        except Exception:
            self.logger.exception("Could not register instruments")
            raise
    
    def reg_transfer_skyMap(self, remote_collection: str = "LSSTComCam/DP1") -> None:
        """
        First: Registering SkyMap DatasetType and copying skyMap dataset(s) (preserving UUIDs)
        Ensure skyMap DatasetType exists locally so transfer-datasets can attach refs

        Second: Transfer skyMap(s)
        """
    ##############
        remote_butler = Butler(self.remote_repo, collections=remote_collection)
        remote_dt = [dt for dt in remote_butler.registry.queryDatasetTypes()
                     if dt.name == "skyMap"]
        if remote_dt:
            self.logger.info("Registering DatasetType 'skyMap' in local repo before transfer.")
            register_datasetTypes(self.local_repo, remote_dt, logger=self.logger)
        else:
            self.logger.warning("Remote repo does NOT contain datasetType 'skyMap'.")
            raise

        # transfering skyMap(s)
        try:
            self.logger.info("Copying skyMap(s) from remote to local (preserving UUIDs)...")
            skymap_register_from_remote(self.remote_repo, self.local_repo, remote_collections=remote_collection,
                                        logger=self.logger)
            self.logger.info("SkyMap copy finished.")
        except Exception:
            self.logger.exception("SkyMap copy failed.")
            raise

    def discover_transfer_datasets(self, visits_datasetRef, remote_collection: str = "LSSTComCam/DP1"):
        """
        First: Recompile information over the choosed datasets
        Second: Transfering datasets
        """
        # In order to improve, we recompile some data_info as first step
        ############################
        self.logger.info("Starting recompilation of some Datas")
        remote_butler = Butler(self.remote_repo, collections=remote_collection)

        try:
            # discover datasets
            out_dic = discover_datasets(self.remote_repo, self.REQUIRED_TYPES, 
                                    remote_collection=remote_collection, logger=self.logger)
            required_present = out_dic["required_present"]
            missing_required = out_dic["missing_required"]

            if not required_present:
                raise RuntimeError("No required datasets found in remote repo. Cannot proceed with transfer.")
            datasettypes_to_register = {dt_name: remote_butler.registry.getDatasetType(dt_name) for dt_name in required_present}
        except Exception:
            self.logger.exception(f"Recompilation failed")
            raise

        # Registering datasetTypes in local
        ##############
        self.logger.info("Starting registering DatasetTypes")
        try:
            register_datasetTypes(self.local_repo, list(datasettypes_to_register.values()), logger=self.logger)
            self.logger.info("DatasetType registration complete.")
        except Exception:
            self.logger.exception("Could not register DatasetTypes")
            raise
        del datasettypes_to_register  # free memory
    
        # Transfering datasets
        ##############
        self.logger.info("Starting dataset transfer loop")
        collections_str = remote_collection  # pass to CLI
        for ref in visits_datasetRef:
            dataId = ref.dataId
            visit = dataId["visit"]
            band = dataId["band"]
            instrument=dataId["instrument"]
            self.logger.info(f"\n[VISIT] Processing visit {visit}")
            
            transfer_dataset(remote_repo=self.remote_repo, local_repo=self.local_repo, id_dataset=[visit],
                             band=band, instrument=instrument, detector=None, day_obs=None, physical_filter=None,
                             skymap=None, collections=collections_str, dataset=list(required_present),
                             logger=self.logger,
            )
            self.logger.info(f"Transfer succeeded for dataId: {dataId}")
        del required_present  # free memory


    def chained(self, chain_name):
        """
        Create a chained collection that includes skymaps and the imported runs (so butler.get finds skyMap)
        """
        # Create a chained collection that includes skymaps and the imported runs (so butler.get finds skyMap)
        self.logger.info("Making a chained collection")
        
        # Determine available collections in local registry
        local_butler = Butler(self.local_repo, writeable=True)
        runs = [c for c in local_butler.registry.queryCollections()
                if local_butler.registry.getCollectionType(c) == CollectionType.RUN
            ]
        
        chain_members = []
        if "skymaps" in local_butler.registry.queryCollections():
            chain_members.append("skymaps")
        chain_members.extend(runs)

        try:
            self.logger.info(f"Creating chained collection '{chain_name}' with members: {chain_members}")
            ensure_chained_collection(self.local_repo, chain_name, members=chain_members, logger=self.logger)
        except Exception:
            self.logger.exception("Could not create or set chained collection.")
            raise

##########
def log_menseger(LOGDIR, LOCAL_REPO):
    """
    Setup logging directory and logger
    """
    log_path = pathlib.Path(LOGDIR)
    log_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["chmod", "ug+rw", LOGDIR], check=True)

    logfile = log_path / "pipeline.log"
    logger = setup_logger(str(logfile))
    logger.info(f"Created LOGDIR at {LOGDIR}")
    logger.info(f"Starting pipeline for local repo: {LOCAL_REPO}")

    return logger

def create_empty_repo(path: str, logger: logging.Logger = None) -> bool:
    """Create a new local Butler repo (using Butler.makeRepo)."""
    if os.path.exists(os.path.join(path, "butler.yaml")):
        raise FileExistsError(f"Repository already exists: {path}")
    os.makedirs(path, exist_ok=True)

    if logger:
        logger.info(f"Creating Butler repo at {path}")
    else:
        print(f"Creating Butler repo at {path}")

    Butler.makeRepo(path)
    return True

def instrument_register_from_remote(
    local_repo: str,
    remote_repo: str,
    instruments: set[str],
    remote_collection: str = "LSSTComCam/DP1",
    logger: logging.Logger = None,
) -> bool:
    """
    Register instruments in the local Butler repo using definitions
    retrieved from a remote repo.

    Parameters
    ----------
    instruments: set of instrument names (strings)
    remote_collection: collection to open the remote Butler with
    """
    if not instruments: raise RuntimeError("No instrument names provided.")
    if logger: logger.info(f"Detected instruments to register: {sorted(instruments)}") 
    if logger: logger.info(f"Opening remote Butler: {remote_repo} (collections={remote_collection})")
    
    remote = Butler(remote_repo, collections=remote_collection)

    # Get instrument records from remote registry
    remote_inst_records = [
        rec for rec in remote.registry.queryDimensionRecords("instrument")
        if rec.name in instruments
    ]

    found_names = {rec.name for rec in remote_inst_records}
    missing = instruments - found_names
    if missing and logger:
        logger.warning(f"Some instruments not found in remote registry: {sorted(missing)}")
        # still continue with those found; you can choose to raise instead

    # Full instrument class names (e.g., lsst.obs.lsst.LsstCam)
    instrument_full = [rec.class_name for rec in remote_inst_records]
    if logger:
        logger.debug(f"Instrument classes from remote: {instrument_full}")

    # Local registry
    local_registry = Butler(local_repo).registry
    local_instrument_names = {rec.name for rec in local_registry.queryDimensionRecords("instrument")}

    for rec, class_name in zip(remote_inst_records, instrument_full):
        if rec.name in local_instrument_names:
            if logger:
                logger.info(f"Instrument '{rec.name}' already registered locally — skipping.")
            continue

        cmd = ["butler", "register-instrument", local_repo, class_name]
        _run(cmd, logger=logger)
        if logger:
            logger.info(f"Registered instrument '{rec.name}' -> {class_name}")

    return True

def register_datasetTypes(local_repo: str, 
                          datasettypes: list[DatasetType],
                          logger: logging.Logger = None,
                          check: bool = True) -> bool:
    """
    Register given DatasetType objects into the local repository.

    Parameters:
        local_repo (str): Path to the local Butler repository.
        datasettypes (list[DatasetType]): List of DatasetType objects to register.
        check (bool): If True, print the list of registered DatasetTypes after registration (default True).

    Returns:
        bool: True if registration completed successfully.
    """
    lbutler = Butler(local_repo, writeable=True)
    lreg = lbutler.registry

    # Get names of already registered DatasetTypes
    already = {d.name for d in lreg.queryDatasetTypes()}

    # Register types if not already present
    for dt in datasettypes:
        if dt.name in already:
            if logger:
                logger.debug(f"DatasetType '{dt.name}' already registered — skipping.")
            continue
        dt = dt.conform_to(lbutler.dimensions)
        lreg.registerDatasetType(dt)
        if logger:
            logger.info(f"Registered DatasetType: {dt.name}")

    # Optional check: print registered DatasetTypes
    if check and logger:
        logger.debug("Current DatasetTypes in registry:")
        for d in lreg.queryDatasetTypes():
            logger.debug(f"  - {d.name}")

    return True

def skymap_register_from_remote(
    remote_repo: str,
    local_repo: str,
    remote_collections: str | list[str] = "LSSTComCam/DP1",
    logger: logging.Logger = None) -> bool:
    """
    1) Detect SkyMap dimension record.
    2) Find which RUN actually contains the skyMap dataset.
    3) Copy it using 'butler transfer-datasets' (preserves UUIDs).
    """
    # Normalize input
    if isinstance(remote_collections, str): remote_collections = [remote_collections]

    # Open remote repo
    remote = Butler(remote_repo, collections=remote_collections)

    # SkyMap DIMENSION RECORD
    skymap_dimrecs = list(remote.registry.queryDimensionRecords("skymap"))
    if not skymap_dimrecs:
        raise RuntimeError(
            f"Remote repo '{remote_repo}' contains the 'skymap' dimension "
            "but no SkyMap records are stored in the given collections."
        )

    skymap_name = skymap_dimrecs[0].name
    if logger: logger.info(f"[SKYMAP] SkyMap dimension found: {skymap_name}")

    # FIND ACTUAL SKYMAP DATASET (search all collections)
    all_remote_collections = [
        c for c in remote.registry.queryCollections() 
        if remote.registry.getCollectionType(c) == CollectionType.RUN
    ]
    found_refs = []
    for coll in all_remote_collections:
        try:
            refs = list(remote.registry.queryDatasets(
                datasetType="skyMap", dataId={"skymap": skymap_name}, collections=coll))
            if refs:
                found_refs.extend(refs)
                if logger: logger.info(f"[SKYMAP] Found skyMap dataset in collection: {coll}")
        except Exception:
            # ignore incompatible collections
            pass

    if not found_refs:
        raise RuntimeError(
            "SkyMap DimensionRecord exists, BUT no actual skyMap dataset exists "
            "in any collection of the remote repository."
        )

    cmd = [
        "butler",
        "transfer-datasets",
        remote_repo,
        local_repo,
        "--dataset-type", "skyMap",
        "--collections", ",".join(remote_collections),
        "--where", f"skymap='{skymap_name}'",
        "--transfer-dimensions",
    ]

    if logger: logger.info("[CMD] " + " ".join(cmd))
    subprocess.run(cmd, check=True)
    if logger: logger.info("[SKYMAP] SkyMap successfully transferred.")

    return True

def discover_datasets(
        REMOTE_REPO: str,
        REQUIRED_TYPES: set[str],
        remote_collection: str = "LSSTComCam/DP1",
        logger: logging.Logger = None) -> dict:
    """
    Identify all datasetTypes available for a REQUIRED_TYPES in the remote repo.
    Returns a dictionary: {'required_present': set[str], 'optional_present': set[str], 'missing_required': set[str], 'missing_optional': set[str],}
    """

    try:
        if logger:
            logger.info(f"Getting the remote Butler registry on: {REMOTE_REPO}.")
        remote = Butler(REMOTE_REPO, collections=remote_collection).registry
        dt_available = {dt.name: dt for dt in remote.queryDatasetTypes()}
    except Exception as e:
        if logger:
            logger.exception(f"Could not have access to Butler registry on: {REMOTE_REPO}")
            logger.error(f"Command failed: {e}")
        raise

    out_dic = {'required_present': set(), 'missing_required': set()}

    # Required datasets
    for dt_name in REQUIRED_TYPES:
        if dt_name not in dt_available:
            out_dic['missing_required'].add(dt_name)
        else:
            out_dic['required_present'].add(dt_name)
            
    if logger:
        logger.info(f"  Required present : {sorted(out_dic['required_present'])}")
        logger.info(f"  Missing required : {sorted(out_dic['missing_required'])}")

    return out_dic

def transfer_dataset(remote_repo: str,
                    local_repo: str,
                    id_dataset: list[int] | int,
                    band: str, instrument: str,
                    detector=None,
                    day_obs=None,
                    physical_filter=None, skymap=None,
                    collections: str | list[str] = None,
                    dataset: str | list[str] = None,
                    logger: logging.Logger = None) -> bool:
    """
    Transfer (use CLI 'butler transfer-datasets' to preserve UUIDs)
    one-or-more dataset from remote_repo to local_repo via `butler transfer-datasets`.

    Returns:
        bool: True if the transfer completed successfully.
    """
    # Build where clause
    id_dataset_list = [id_dataset]if isinstance(id_dataset, int) else list(id_dataset)

    if not id_dataset_list: raise ValueError("No dataset IDs provided to transfer_dataset().")
    if logger: logger.info("[INFO] Transferring datasets...")

    # Create dataset IDs string
    id_dataset_str = "(" + ",".join(map(str, id_dataset_list)) + ")"

    # Build the query parts
    query_parts = [f"instrument='{instrument}'", f"visit IN {id_dataset_str}", f"band='{band}'"]
    if detector is not None:
        if isinstance(detector, (list, tuple, set)):
            det_str = "(" + ",".join(map(str, detector)) + ")"
            query_parts.append(f"detector IN {det_str}")
        else:
            query_parts.append(f"detector={int(detector)}")

    if day_obs is not None:
        if isinstance(day_obs, (list, tuple, set)):
            day_str = "(" + ",".join(map(str, day_obs)) + ")"
            query_parts.append(f"day_obs IN {day_str}")
        else:
            query_parts.append(f"day_obs={int(day_obs)}")

    if physical_filter:
        query_parts.append(f"physical_filter='{physical_filter}'")

    if skymap:
        query_parts.append(f"skymap='{skymap}'")
    query_string = " AND ".join(query_parts)

    # Build the command
    cmd = ["butler", "transfer-datasets", remote_repo, local_repo, "--where", query_string]

    if collections:
        if isinstance(collections, (list, tuple, set)):
            collections_str = ",".join(collections)
        else:
            collections_str = collections
        cmd.extend(["--collections", collections_str])

    if dataset:
        dataset_list = dataset if isinstance(dataset, list) else [dataset]
        cmd.extend(["--dataset-type", ",".join(dataset_list)])

    try:
        _run(cmd, logger=logger)
    except Exception:
        if logger: logger.error(f"Failed to transfer datasets for dataset={dataset}, visits={id_dataset_str}")
        raise

    if logger: logger.info(f"Completed transfer-datasets for dataset={dataset}, visits={id_dataset_str}")
    return True

def ensure_chained_collection(
        local_repo: str,
        chain_name: str,
        members: list[str],
        run_name: str = None,
        logger: logging.Logger = None) -> bool:
    """
    Creation/update of a CHAINED collection:
      - Avoids inserting the chain into itself
      - Avoids ingest/transfer/curated/other system collections
    """
    reg = Butler(local_repo, writeable=True).registry
    existing = reg.queryCollections()

    # Create RUN if not exists
    if run_name and run_name not in existing:
        if logger: logger.info(f"[CREATE] RUN collection: {run_name}")
        reg.registerCollection(run_name, CollectionType.RUN)
        members.append(run_name)
    else:
        if run_name and logger: logger.info(f"[OK] RUN already exists: {run_name}")

    # Create chain if it does not exist
    if chain_name not in existing:
        reg.registerCollection(chain_name, CollectionType.CHAINED)
        if logger: logger.info(f"Registered CHAINED collection: {chain_name}")

    # Filter dangerous or irrelevant collections
    safe_members = []
    for m in members:
        if m == chain_name: continue # Never include the chain itself
        if m.startswith("ingest") or m.startswith("transfer") or m.startswith("_"): continue  # Skip system collections
        if "butler" in m.lower(): continue # Skip curated/registry internals
        safe_members.append(m)

    # Apply chain
    reg.setCollectionChain(chain_name, safe_members)
    if logger: logger.info(f"Set chain for '{chain_name}' -> {safe_members}")

    return True
