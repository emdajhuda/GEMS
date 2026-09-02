# butler/butler.py

# Loading modules
import os, sys
from lsst.daf.butler import Butler  #  modules for data access via the Butler

from ..plot.statistics_plot import StatisticsPlots

###################################################################################################
class ExpButler:
    """ 
    Class to manage data access using the LSST Butler.

    Example
    -------
    eb = ExpButler(repository="dp1", collections="LSSTComCam/DP1")
    eb.butler.get("camera")
    """

    # Class attribute
    #######################
    def __init__(self, repository="dp1", collections="LSSTComCam/DP1", info=False, **kwargs):
        """
        Parameters
        ----------
        repository : str
                Path or name of the Butler repository (e.g., "dp1").
        collections : str or list
                Collection or list of collections to query from (e.g., "LSSTComCam/DP1").
        info : bool
                If True, prints repository and collection info upon initialization.
        """
        self.repository = repository
        self.collections = collections
        self.kwargs = kwargs
        self.info = info
        self.butler = self._create_butler()

        # Connect plotting/stats utilities
        self.plot = StatisticsPlots(self.butler)  # Statistic plots

        if self.info:
            self.show_repo_info()

    # ------------------------------
    # Private: Butler loader
    # ------------------------------
    def _create_butler(self):
        """
        Create and return a Butler instance based on current repository and collections.
        """
        try:
            butler = Butler(config=self.repository, collections=self.collections)
        except Exception as e:
            raise ValueError(f"Failed to create Butler: {e}")
        return butler

    # ------------------------------
    # Informational methods
    # ------------------------------
    def show_repo_info(self):
        """
        Print repository and available collections for user reference.
        """
        print(f"Repository: {self.repository}")
        print("Available collections:")
        for col in self.butler.registry.queryCollections():
            print(f"  - {col}")

    def list_dataset_types(self, pattern=None):
        """
        List dataset types registered in the Butler, optionally filtered by a substring.

        Parameters
        ----------
        pattern : str or None
            If provided, filters dataset names containing the pattern.

        Returns
        -------
        list
            List of dataset type names.
        """
        dataset_types = self.butler.registry.getDatasetTypes()
        if pattern:
            return [name for name in dataset_types if pattern in name]
        return list(dataset_types)

    def list_collections(self):
        """
        Return a list of all available collections in the repository.

        Returns
        -------
        list
            Collection names.
        """
        return list(self.butler.registry.queryCollections())

    def list_dimensions(self):
        """
        Return a list of dimension names known to the Butler.

        Returns
        -------
        list
            Dimension names.
        """
        return list(self.butler.registry.dimensions.names)

    # ------------------------------
    # Data and query methods
    # ------------------------------
    def dimension_records(self, dimension_name):
        """
        Query all records of a specific dimension.

        Parameters
        ----------
        dimension_name : str
            Name of the dimension (e.g., "visit", "instrument", "tract").

        Returns
        -------
        list
            List of records for the given dimension.
        """
        return self.butler.registry.queryDimensionRecords(dimension_name)

    def get_dataset(self, dataset_type, data_id):
        """
        Retrieve a specific dataset.

        Parameters
        ----------
        dataset_type : str
            Dataset type name (e.g., "raw", "calexp").
        data_id : dict
            Dictionary with identifying dimensions (e.g., {"instrument": ..., "visit": ..., ...}).

        Returns
        -------
        object
            The requested dataset.
        """
        return self.butler.get(dataset_type, dataId=data_id)