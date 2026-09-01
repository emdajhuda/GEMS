# gems v1.0
# visit_selection.visit_selection.py
# IMPORTANT: The visit IDs (visit.id) must be unique across bands.

import os, sys
import numpy as np

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ...utils.sky.sky import tract_patch, patch_center

class VisitSL():
    """ 
    Class to query visits based on sky coordinates or tract/patch.
    """

    # Class attribute
    ###################################################################################################
    def __init__(self, loc_data, band, sky_coordinates=True, repository="dp1", collections="LSSTComCam/DP1", butler=None):
        """
        Parameters
        ----------
        loc_data : tuple
                Either (RA, Dec) in degrees, or (tract, patch) integers.
        band : str
                Photometric band name (e.g., 'r', 'i', etc.)
        sky_coordinates : bool
                If True, loc_data is (RA, Dec). If False, loc_data is (tract, patch).
        repository : str
                Path or name of the Butler repository (e.g., "dp1").
        collections : str or list
                Collection or list of collections to query from (e.g., "LSSTComCam/DP1").
        """
        self.band = band
        if butler:
            self.butler = butler
        else:
            from butler.butler import ExpButler
            self.butler = ExpButler(repository=repository, collections=collections)._create_butler()

        if sky_coordinates:
            self.ra_deg, self.dec_deg = loc_data
        else:
            tract, patch = loc_data
            ra_deg, dec_deg = patch_center(self.butler, tract, patch, sequential_index=True)
            self.ra_deg = ra_deg
            self.dec_deg = dec_deg

    def __repr__(self):
        return f"<Visit band={self.band}, RA={self.ra_deg:.4f}, Dec={self.dec_deg:.4f}>"
    
    # ------------------------------------------------------------
    # Get images overlapping a particular sky position
    # ------------------------------------------------------------
    def query_visit_image(self, detectors=None, timespan=None, visit_ids=None, use_patch_area=False,
                          filter_by_region=True, instrument="LSSTComCam"):
        """
        Identify images overlapping a particular sky position and select one to inject sources into.

        Parameters
        ----------
        detectors : int, list of int, or None
            Detector(s) to query (default=None means all detectors)
        timespan : tuple or None
            Optional time range for the visit images (begin, end)
        lazy : bool
            If True, query returns lazy references instead of fully loaded datasets
        visit_ids : list[int] or None
            Optional list of visit IDs to filter
        use_patch_area : bool
            If True, query uses the entire patch area (like coadd construction);
        filter_by_region: bool
            If True, query uses visit_detector_region.region OVERLAPS POINT to filter visits;

        Returns
        -------
        list
            References to visit_image datasets matching the query

        See also:
        https://dp1.lsst.io/tutorials/notebook/202/notebook-202-2.html
        https://dp1.lsst.io/tutorials/notebook/105/notebook-105-4.html
        """

        # Base query
        query_parts = [f"band='{self.band}'"]

        # Instrument filter
        query_parts.append(f"instrument='{instrument}'")

        # Spatial filter: by point or by patch
        if use_patch_area:
            # Get tract and patch for RA/Dec
            tract, patch = tract_patch(self.butler, self.ra_deg, self.dec_deg, sequential_index=True)
            query_parts.append(f"tract={tract}")
            query_parts.append(f"patch={patch}")
        
        if filter_by_region:
            # Point query
            query_parts.append(f"visit_detector_region.region OVERLAPS POINT({self.ra_deg}, {self.dec_deg})")

        # Detector filter (if None, query all)
        if detectors is not None:
            if isinstance(detectors, int):
                query_parts.append(f"detector={detectors}")
            else:
                detector_str = ",".join(map(str, detectors))
                query_parts.append(f"detector IN ({detector_str})")

        # Timespan filter
        if timespan is not None:
            query_parts.append("visit.timespan OVERLAPS :timespan")
        
        # Visit ID filter
        if visit_ids:
            query_parts.append(f"visit.id IN ({','.join(map(str, visit_ids))})")

        # Join query parts, omit empty strings
        query = " AND ".join(query_parts)

        #### Execute query
        visit_img_refs = self.butler.query_datasets(
            'visit_image',
            where=query,
            order_by='visit.timespan.begin'
        )

        return visit_img_refs

    # ------------------------------------------------------------
    # Get visit list for a given band
    # ------------------------------------------------------------
    def visit_list(self, type_coadd='deep_coadd'):
        """
        Return the list of visit IDs used to build a deep coadd for the current band and coordinates.

        Parameters
        ----------
        type_coadd : str
            Type of coadd dataset to retrieve (default: 'deep_coadd').

        Returns
        -------
        my_visit_list : list
            List of visit IDs that contributed to the selected coadd.
        """
        # Determine tract and patch for the given coordinates (RA, Dec)
        my_tract, my_patch = tract_patch(self.butler, self.ra_deg, self.dec_deg, sequential_index=True)
    
        # Define the data ID for the coadd based on band, tract, and patch
        coaddId = {
            'band': self.band,
            'tract': my_tract,
            'patch': my_patch
        }
    
        # Retrieve the "type_coadd" from the Butler
        deepCoadd = self.butler.get(type_coadd, dataId=coaddId)
    
        # Extract the list of visit IDs used to construct the coadd
        my_visit_list = deepCoadd.getInfo().getCoaddInputs().visits['id']
    
        return my_visit_list

    # ------------------------------------------------------------
    # Read the visit tables: 'visit_table', 'visit_detector_table'
    # ------------------------------------------------------------
    def read_visit_tables(self, tables=['visit_table', 'visit_detector_table'], info=True):
        """
        Load visit-related tables from the LSST Butler.

        Parameters
        ----------
        butler : lsst.daf.butler.Butler
            An initialized Butler object.
        tables : list of str
            List of dataset type names to retrieve (e.g. 'visit_table', 'visit_detector_table').
        info : bool, optional
            If True, print column names of each retrieved table.
        Returns
        -------
        dict
            Dictionary where keys are dataset names and values are the corresponding Astropy tables.
            Tables not found will not appear in the output.
        """
        visit_tables = {}
        for table in tables:
            refs = list(self.butler.registry.queryDatasets(table))
            if not refs:
                print(f"Dataset '{table}' not found in the registry.")
                continue

            try:
                visit_table = self.butler.get(refs[0])
                visit_tables[table] = visit_table
                if info:
                    print(f"\n Columns in '{table}':\n{visit_table.colnames}")
            except Exception as e:
                print(f" Error retrieving '{table}': {e}")
        return visit_tables
    

    # ------------------------------------------------------------
    # Read the visit tables: 'visit_table', 'visit_detector_table'
    # ------------------------------------------------------------
    def visit_selection(self, 
                    selection=['psfSigma', 'seeing', 'airmass', 'obsStartMJD'],
                    n_visits=None, flatten=False, type_coadd='deep_coadd'):
        """
        From my_visit_list IDs, extract selected the columns gives by "selection" from one or more visit-related tables.

        Parameters
        ----------
        selection : list of str
            List of column names to extract.
        n_visits : int or None
            If provided, only return the first n visits.
        flatten: bool
            True: From my_visit_list, extract selected quantities grouped by column, each with a dict of visitId -> list of values.
            False: From my_visit_list, extract selected quantities on an only column
    
        Returns
        -------
        dict -> when flatten=True 
            Dictionary with keys being column names and values being arrays of data for selected visits.

        dict -> when flatten=False
            {column_name: {visitId: [values, ...], ...}, ...}
        """

        my_visit_list = self.visit_list(type_coadd=type_coadd)

        # Optionally reduce list of visits
        if n_visits is not None:
            my_visit_list = my_visit_list[:n_visits]
        
        visit_tables = self.read_visit_tables(tables=['visit_table', 'visit_detector_table'], info=False)

        selected_data = {} if flatten else {col: {} for col in selection}

        # Iterate over tables and extract available columns
        for _, table in visit_tables.items():
            if 'visitId' not in table.colnames:
                continue  # Skip tables without visitId

            # Filter rows with matching visitId
            mask = np.isin(table['visitId'], my_visit_list)
            table_visits = table[mask]

            if flatten:
                # Extract each column that exists in this table
                for col in selection:
                    if col in table.colnames and col not in selected_data:
                        selected_data[col] = table_visits[col]
            else:
                for row in table_visits:
                    visit_id = int(row['visitId'])
                    for col in selection:
                        if col in row.colnames:
                            value = float(row[col])
                            if visit_id not in selected_data[col]:
                                selected_data[col][visit_id] = []
                            selected_data[col][visit_id].append(value)
        return selected_data

    # ------------------------------------------------------------
    # Filt the visit tables: 'visit_table', 'visit_detector_table'
    # ------------------------------------------------------------
    def filt_visit(self, statistics={'std', 'mean'},
                   selection=['psfSigma', 'seeing', 'airmass', 'obsStartMJD'],
                   filt_cut=None, n_visits=None, type_coadd='deep_coadd'):
        """
        Compute statistics (mean, std) from selected_data for each visit ID.

        Parameters
        ----------
        selected_data : dict
                Dictionary as returned by visit_selection: {column_name: {visitId: [values, ...]}}.
        statistics : set
                Set of statistics to compute. Options: 'mean', 'std'.
        filt_cut : dict or None
                Optional dictionary of filters like {'airmass_mean': ' < 1.5', 'seeing_std': ' > 0.2'}.
        n_visits : int or None
                If provided, only use the first n_visits from my_visit_list.

        Returns
        -------
        df_metrics : pd.DataFrame
                DataFrame with one row per visit, containing computed statistics.
        visits_selected : pd.DataFrame or None
                Filtered DataFrame if filt_cut is provided.
        """
        import pandas as pd
        
        my_visit_list = self.visit_list(type_coadd=type_coadd)

        if n_visits is not None:
            my_visit_list = my_visit_list[:n_visits]
        
        # Get data: {column_name: {visitId: [values, ...], ...}, ...}
        visit_selection_data = self.visit_selection(selection=selection,
            n_visits=n_visits, flatten=False, type_coadd=type_coadd)
        
        metrics = {'id_plot': [], 'visit_id': [], 'band': []}
        
        for idx, visit_id in enumerate(my_visit_list):
            metrics['id_plot'].append(idx)
            metrics['visit_id'].append(visit_id)
            metrics['band'].append(self.band)

            for name in selection:
                if name not in visit_selection_data or visit_id not in visit_selection_data[name]:
                    continue

                temp = np.asarray(visit_selection_data[name][visit_id], dtype='float')
                nan_mask = np.isnan(temp).any()

                # Compute statistics if there are multiple values
                if len(temp) > 1:
                    if 'std' in statistics:
                        key = f"{name}_std"
                        value = np.nanstd(temp) if nan_mask else np.std(temp)
                        metrics.setdefault(key, []).append(value)
                        if nan_mask:
                            print(f"[Warning] NaNs in {key} for visit {visit_id}")

                    if 'mean' in statistics:
                        key = f"{name}_mean"
                        value = np.nanmean(temp) if nan_mask else np.mean(temp)
                        metrics.setdefault(key, []).append(value)
                        if nan_mask:
                            print(f"[Warning] NaNs in {key} for visit {visit_id}")
                else:
                    # Just one value: store directly
                    key = name
                    metrics.setdefault(key, []).append(float(temp[0]))
            
            # Fill missing keys (ensure columns are aligned)
            for stat in statistics:
                for name in selection:
                    key = f"{name}_{stat}"
                    if key not in metrics:
                        metrics[key] = [np.nan] * (idx + 1)
                    elif len(metrics[key]) < (idx + 1):
                        metrics[key].append(np.nan)

        df_metrics = pd.DataFrame(metrics)

        # Apply filter cuts if provided
        visits_selected = df_metrics
        if filt_cut:
            try:
                # Build a combined boolean mask
                mask = np.ones(len(df_metrics), dtype=bool)
                for col, expr in filt_cut.items():
                    if col in df_metrics.columns:
                        cond = df_metrics.eval(f"{col}{expr}")
                        mask &= cond
                    else:
                        print(f"[Warning] Column '{col}' not found for filtering.")
                visits_selected = df_metrics[mask]
            except Exception as e:
                print("[Error] Failed to evaluate filter expression:", e)
                visits_selected = None

        return df_metrics, visits_selected


########### EXTRA FUNCTIONS ##############################################################################

def visit_dataset(
    butler,
    band,
    loc_data,
    repository=None,
    use_patch_area=False,
    collections="LSSTComCam/DP1",
    detectors=None,
    timespan=None,
    visit_ids=None,
    filter_by_region=True,
    instrument="LSSTComCam",
):
    """
    Query LSST visit-level calibrated exposures (calexp) around a location.

    Parameters
    ----------
    butler : lsst.daf.butler.Butler
        Butler instance to access the LSST data repository.
    band : str
        Filter band (e.g., "g", "r", "i").
    loc_data : tuple
        Location of interest:
        - If (ra, dec) in degrees: query visits covering this position.
        - If (tract, patch): query visits overlapping that patch.
    repository: str
        Path to the LSST data repository
    use_patch_area : bool, optional
        If True, use the full patch area for the query. 
        If False (default), use only the central coordinate.
    detectors : list of int, optional
        Restrict query to specific detectors.
    timespan : lsst.daf.butler.Timespan, optional
        Restrict query to a specific time interval.
    visit_ids : list of int, optional
        Restrict query to specific visit IDs.
    filter_by_region : bool, optional
        If True, use visit_detector_region to filter visits.
    instrument : str, optional
        Instrument name (default: "LSSTComCam").

    Returns
    -------
    visit_refs : list of lsst.daf.butler.DeferredDatasetHandle
        References to the matching visit-level exposures.
    """

    if butler:
        # Use an existing Butler
        visit_obj = VisitSL(
            loc_data=loc_data,
            butler=butler,
            band=band,
        )
    elif repository:
        # Use a repository path
        visit_obj = VisitSL(
            loc_data=loc_data,
            repository=repository,
            band=band,
            collections=collections,
        )
    else:
        print('[Error] A butler or repository path must be provided.')
        raise ValueError("Missing 'butler' or 'repository' input")

    # Query matching visit images
    visit_refs = visit_obj.query_visit_image(
        detectors=detectors,
        visit_ids=visit_ids,
        use_patch_area=use_patch_area,
        filter_by_region=filter_by_region,
        timespan=timespan,
        instrument=instrument
    )

    return visit_refs

def combine_visits_selected(visits_selected_list):
    """
    Combine a list of DataFrames (each representing a band) into a single DataFrame.

    Parameters
    ----------
    visits_selected_list : list of pd.DataFrame
        Each DataFrame must contain a 'band' column.
        The columns may differ between DataFrames.

    Returns
    -------
    pd.DataFrame
        A combined DataFrame with missing columns filled with NaN.
    """
    import pandas as pd

    if not isinstance(visits_selected_list, list):
        raise ValueError("Input must be a list of pandas DataFrames.")

    for i, df in enumerate(visits_selected_list):
        if 'band' not in df.columns:
            raise ValueError(f"DataFrame at index {i} is missing the required 'band' column.")
        if not isinstance(df, pd.DataFrame):
            raise ValueError(f"Element at index {i} is not a pandas DataFrame.")

    combined_df = pd.concat(visits_selected_list, ignore_index=True, sort=False)
    return combined_df

