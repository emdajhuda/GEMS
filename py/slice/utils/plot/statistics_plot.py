# v1.0
# plots/statistics_plots.py
# set of functions that plot statistics results
# IMPORTANT: The visit IDs (visit.id) must be unique across bands.

import os, sys
import numpy as np
import matplotlib.pyplot as plt

from astropy.time import Time
from lsst.utils.plotting import (get_multiband_plot_colors,
                                         get_multiband_plot_linestyles)

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ...py.visit_selection.visit_selection import VisitSL
from ..sky.sky import tract_patch

###################################################################################################
class StatisticsPlots:
    """
    Statistics and plotting utilities to be used with ExpButler.

    Example:
    eb = ExpButler(repository="dp1", collections="LSSTComCam/DP1")
    eb.plot.visit_date_plot(ra_deg=30.0, dec_deg=-10.0, degrees=0.5)
    """

    # Class attribute
    ##################
    def __init__(self, butler):
        self.butler = butler

    # ------------------------------
    # Plot visit data by filter
    # ------------------------------
    def get_visit_mjds(self, bands, ra_deg, dec_deg,
                   degrees=None, mode="global"):
        """
        Get visit MJDs (Modified Julian Date) by filter, either:
            - for visits overlapping a circular sky region (mode='global'), or
            - for visits used in the deepCoadd (mode='deepCoadd').

        Parameters
        ----------
        butler : lsst.daf.butler.Butler
                LSST Butler instance.
        bands : list of str
                List of filters to include (e.g., ['u', 'g', 'r']).
        mode : str
                Selection mode: 'global' (use sky region) or 'deepCoadd' (use tract & patch).
        ra_deg : float
                RA center of region (degrees). Required if mode='global'.
        dec_deg : float
                Dec center of region (degrees). Required if mode='global'.
        degrees : float, optional
                Radius of region (degrees). Required if mode='global'.

        Returns
        -------
        visit_times_by_band : dict
                Dictionary {filter: sorted numpy array of MJDs}.
        """
        import lsst.sphgeom as sphgeom

        visit_times_by_band = {}
        if mode == "global":
            if None in (ra_deg, dec_deg, degrees):
                raise ValueError("ra_deg, dec_deg, and degrees must be provided for 'global' mode.")

            try:
                str_region = f"CIRCLE {ra_deg} {dec_deg} {degrees}"
                region = sphgeom.Region.from_ivoa_pos(str_region)
            except Exception as e:
                print(f"Error defining region: {e}")
                return {}

            for band in bands:
                try:
                    visit_dimrecs = self.butler.query_dimension_records(
                        "visit",
                        where="band.name = :band AND visit.region OVERLAPS :region",
                        bind={"band": band, "region": region}
                    )

                    mjds = [
                        v.timespan.begin.mjd
                        for v in visit_dimrecs
                        if v.timespan and v.timespan.begin
                    ]
                    if mjds:
                        visit_times_by_band[band] = np.sort(np.asarray(mjds))
                except Exception as e:
                    print(f"Error querying visits for band '{band}': {e}")

        elif mode == "deepCoadd":
            tract, patch = tract_patch(self.butler, ra_deg, dec_deg, sequential_index=True)

            for band in bands:
                coadd_id = {"band": band, "tract": tract, "patch": patch}
                try:
                    deepCoadd = self.butler.get("deep_coadd", dataId=coadd_id)
                    coadd_inputs = deepCoadd.getInfo().getCoaddInputs()
                    visit_ids = coadd_inputs.visits["id"]

                    # Retrieve visit records by ID
                    visit_dimrecs = self.butler.query_dimension_records(
                        "visit", where="band.name = :band", bind={"band": band}
                    )
                    
                    filtered_visits = [v for v in visit_dimrecs if v.id in visit_ids]
                    
                    mjds = [
                        v.timespan.begin.mjd
                        for v in filtered_visits
                        if v.timespan and v.timespan.begin
                    ]
                    if mjds:
                        visit_times_by_band[band] = np.sort(np.asarray(mjds))
                except Exception as e:
                    print(f"Error accessing deepCoadd for band '{band}': {e}")
        else:
            raise ValueError("Unsupported mode. Use 'global' or 'deepCoadd'.")

        return visit_times_by_band

    def visit_date_plot(self, ra_deg, dec_deg, degrees=1.0, bands='ugrizy',
                        mode="global", calendar_dates=False, save=False):
        """
        Plot cumulative number of visits over time by filter.
        
        Parameters
        ----------
        self.butler : lsst.daf.butler.Butler
                LSST Butler instance.
        ra_deg : float
                Right Ascension in degrees.
        dec_deg : float
                Declination in degrees.
        degrees : float, optional
                Radius (in degrees) around (RA, Dec) to include.
        bands : str, optional, default -> ['u', 'g', 'r', 'i', 'z', 'y']
                Filter used to cumulative plot
        mode : str
                Selection mode: 'global' (use sky region) or 'deepCoadd' (use tract & patch).
        calendar_dates : bool, optional
                If True, x-axis is shown in calendar dates (ISO). If False, MJD values are used.
        save : bool or str (path), optional
                If True, save the Fig. with the name give by save

        Based on: https://dp1.lsst.io/tutorials/notebook/104/notebook-104-2.html
        """
        import matplotlib.dates as mdates
        
        # Setup
        filter_colors = get_multiband_plot_colors()
        filter_linestyles = get_multiband_plot_linestyles()
        
        visit_times_by_band = self.get_visit_mjds(bands, ra_deg, dec_deg,
                   degrees=degrees, mode=mode)

        if not visit_times_by_band:
            print("No visit data found for any band.")
            return
        
        # Define bins from all MJDs combined
        all_mjds = np.concatenate(list(visit_times_by_band.values()))
        min_mjd = int(np.floor(np.min(all_mjds))) - 1
        max_mjd = int(np.ceil(np.max(all_mjds))) + 2
        use_bins = np.arange(min_mjd, max_mjd + 1, 1)

        if calendar_dates:
            date_bins = Time(use_bins, format='mjd', scale="tai").to_datetime()
            use_bins = date_bins

        # Plotting
        plt.figure(figsize=(8, 5))
        for band, values in visit_times_by_band.items():
            label = f"{band} ({len(values)})"

            if calendar_dates:
                times = Time(values, format='mjd').to_datetime()
            else:
                times = values

            n, bins, patches = plt.hist(
                times, bins=use_bins,
                cumulative=True, histtype='step',
                linewidth=2, alpha=0.7,
                color=filter_colors[band],
                label=label
            )

            for patch in patches:
                patch.set_linestyle(filter_linestyles[band])

        plt.legend(loc='upper left')
        plt.ylabel(r'Cumulative number of visits')
        plt.title(r'Cumulative Visit Counts by Filter')
        # plt.grid(True)
        plt.tight_layout()

        if calendar_dates:
            plt.xlabel(r"Date")
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
            plt.gcf().autofmt_xdate()
        else:
            plt.xlabel(r'MJD')
        
        if save:
            filename = save if isinstance(save, str) else 'visit_date_output.pdf'
            plt.savefig(
                filename, format='pdf', metadata=None,
                pad_inches=0.1, dpi=1000,
                bbox_inches='tight'
            )
        return
    
    # ------------------------------------------------------------------
    # Plot histogram for choosed visit_table elements and by filter
    # ------------------------------------------------------------------
    def hist_visit_table(self, ra_deg, dec_deg, save=False, selection=['airmass', 'expMidptMJD'], 
                         bands='ugrizy', n_visits=None):
        """
        Make histograms of selected visit-table fields by filter.

        Parameters
        ----------
        ra_deg : float
                Right Ascension in degrees.
        dec_deg : float
                Declination in degrees.
        save : bool or str, optional
                If True, saves the plot as 'visit_hist_output.pdf'.
                If a string, uses it as the output filename.
        selection : list of str
                List of visit table fields to plot (e.g., ['airmass', 'expMidptMJD']).
        bands : str or list of str
                Filters to include in the plot. Default is 'ugrizy'.
        n_visits : int or None
                Limit on number of visits per filter. If None, use all available.
        """
        # Setup
        filter_colors = get_multiband_plot_colors()
        filter_linestyles = get_multiband_plot_linestyles()
        ncols = len(selection)
        loc_data = (ra_deg, dec_deg)

        # Read from Butler the coadded image
        fig, ax = plt.subplots(nrows=1, ncols=ncols, figsize=(5*ncols, 4.))
        if isinstance(ax, plt.Axes):
            ax = [ax]  # Ensure it's always iterable

        for band in bands:  # Choosing the "band"
            visit_instance = VisitSL(loc_data, band, butler=self.butler)
            visit_selection_data = visit_instance.visit_selection(selection=selection, type_coadd='deep_coadd',
                                                                  n_visits=n_visits, flatten=True)
            for i, name in enumerate(selection):
                if name not in visit_selection_data:
                    print(f"Warning: '{name}' not in visit table for band '{band}'.")
                    continue
                
                ax[i].hist(
                    visit_selection_data[name],
                    histtype='step',
                    linewidth=2, alpha=0.7,
                    ls=filter_linestyles[band],
                    color=filter_colors[band],
                    label=band
                )
                ax[i].set_xlabel(name)
                ax[i].legend(loc='upper left')
            
            # Set common y-label
            for a in ax:
                 a.set_ylabel("Number of input exposures")
            plt.tight_layout()

        # Save output
        if save:
            filename = save if isinstance(save, str) else 'visit_hist_output.pdf'
            fig.savefig(
                filename, format='pdf', metadata=None,
                pad_inches=0.1, dpi=1000,
                bbox_inches='tight'
            )

        return