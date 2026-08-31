# v1.0
# sky file

import lsst.geom
from astropy.wcs import WCS

#################### SkyMap ##################################################
def skywcs_to_astropy(lsst_wcs):
    """Convert LSST SkyWcs to Astropy WCS."""
    md = lsst_wcs.getFitsMetadata()  # returns PropertyList with FITS WCS keywords
    header = {}
    for key in md.names():
        try:
            header[key] = md.getScalar(key)
        except Exception:
            continue
    return WCS(header)

def tract_patch(butler, ra_deg, dec_deg, sequential_index=True):
    """
    From sky coordinates (RA, Dec in degrees), identify the tract and patch
    that cover the desired region using the SkyMap.

    Parameters
    ----------
    butler : lsst.daf.butler.Butler
        An initialized Butler instance.
    ra_deg : float
        Right ascension in degrees.
    dec_deg : float
        Declination in degrees.
    sequential_index : bool, optional
        If True, return patch as sequential integer index. If False, return "x,y" string.

    Returns
    -------
    tract : int
        ID of the tract containing the point.
    patch : str
        Patch ID, either as integer (string) or "x,y" format depending on sequential_index.

    See also:
    https://dp1.lsst.io/tutorials/notebook/104/notebook-104-2.html
    """
    # with the sky coordinates, we identify the tract and patch that cover the desired region
    point_sky = lsst.geom.SpherePoint(ra_deg, dec_deg, lsst.geom.degrees)
    try:
        skymap = butler.get("skyMap")
    except:
        skymap = butler.get("skyMap", collections=butler.registry.queryCollections())

    tract_info = skymap.findTract(point_sky)
    tract = tract_info.getId()

    patch_info = tract_info.findPatch(point_sky)

    if sequential_index:
        patch_index = patch_info.getSequentialIndex()
        patch_str = patch_index
    else:
        x, y = patch_info.getIndex()
        patch_str = f"{x},{y}"

    return tract, patch_str

def patch_center(butler, tract, patch_str, sequential_index=True):
    """
    Given a tract and patch, return the sky coordinates (RA, Dec) of the patch center.

    Parameters
    ----------
    butler : lsst.daf.butler.Butler
        Butler instance.
    tract : int
        Tract ID.
    patch_str : str or int
        Patch in "x,y" format (string), or an integer index if sequential_index=True.
    sequential_index : bool, optional
        Whether patch_str is a sequential patch index (default: True).

    Returns
    -------
    ra_deg : float
        Right Ascension of the patch center, in degrees.
    dec_deg : float
        Declination of the patch center, in degrees.
    """
    skymap = butler.get("skyMap")
    tract_info = skymap[tract]

    if sequential_index:
        patch_info = tract_info.getPatchInfo(int(patch_str))
    else:
        try:
            x_str, y_str = patch_str.split(",")
            patch_index = (int(x_str), int(y_str))
            patch_info = tract_info.getPatchInfo(patch_index)
        except Exception as e:
            raise ValueError(f"Invalid patch format '{patch_str}': {e}")

    centroid_vec = patch_info.getInnerSkyPolygon().getCentroid()
    sky_center = lsst.geom.SpherePoint(centroid_vec)

    ra_deg = sky_center.getLongitude().asDegrees()
    dec_deg = sky_center.getLatitude().asDegrees()

    return ra_deg, dec_deg

def get_patch_center_radius(butler, ra_deg, dec_deg):
    """
    Returns the center and approximate radius of a patch containing a given RA/Dec.

    Parameters
    ----------
    butler : lsst.daf.persistence.Butler
        LSST Butler used to access the skymap.
    ra_deg : float
        Right ascension of the point in degrees.
    dec_deg : float
        Declination of the point in degrees.

    Returns
    -------
    center_coord : lsst.geom.SpherePoint
        Center of the patch.
    radius_deg : float
        Circumscribed radius of the patch in degrees (approximation using the farthest corner).
    """
    import numpy as np
    
    # 1. Construct the point in spherical coordinates
    point = lsst.geom.SpherePoint(ra_deg, dec_deg, units=lsst.geom.degrees)

    # 2. Get the skymap
    skymap = butler.get("skyMap")

    # 3. Find the tract containing the point
    tract = skymap.findTract(point)  # TractInfo object

    # 4. Find the patch containing the point within the tract
    patch = tract.findPatch(point)  # PatchInfo object

    # 5. Get the WCS and bounding box of the patch
    patch_wcs = patch.getWcs()
    bbox = patch.getOuterBBox()

    # 6. Define the corners of the patch in pixel coordinates
    corners_px = [
        lsst.geom.Point2D(bbox.getMin().x, bbox.getMin().y),  # bottom-left
        lsst.geom.Point2D(bbox.getMax().x, bbox.getMin().y),  # bottom-right
        lsst.geom.Point2D(bbox.getMax().x, bbox.getMax().y),  # top-right
        lsst.geom.Point2D(bbox.getMin().x, bbox.getMax().y),  # top-left
    ]

    # 7. Convert pixel corners to sky coordinates
    corners_sky = patch_wcs.pixelToSky(corners_px)  # returns list of SpherePoint

    # 8. Compute the average center of the patch
    ra_list = np.array([p.getRa().asDegrees() for p in corners_sky])
    dec_list = np.array([p.getDec().asDegrees() for p in corners_sky])
    center_ra = ra_list.mean()
    center_dec = dec_list.mean()
    center_coord = lsst.geom.SpherePoint(center_ra, center_dec, units=lsst.geom.degrees)

    # 9. Compute approximate circumscribed radius (maximum distance to any corner)
    radius_deg = max(center_coord.separation(p).asDegrees() for p in corners_sky)

    return center_coord, radius_deg

def RA_to_degree(hours, minutes=None, seconds=None):
    """
    Convert Right Ascension (RA) to degrees.
    
    Accepts:
        - Three numeric arguments (hours, minutes, seconds)
        - A string like "1h3m4s" or "01:03:04"
    """
    import re

    # If input is a string, parse it
    if isinstance(hours, str):
        match = re.match(r'(\d+)[h:](\d+)[m:](\d+)', hours.strip())
        if not match:
            raise ValueError("RA string must be in 'hhhmms' or 'hh:mm:ss' format.")
        hours, minutes, seconds = map(int, match.groups())
    
    return (hours + minutes/60 + seconds/3600) * 15


def Dec_to_degree(degrees, minutes=None, seconds=None):
    """
    Convert Declination (Dec) to degrees.
    
    Accepts:
        - Three numeric arguments (degrees, minutes, seconds)
        - A string like "-12d30m0s" or "-12:30:00"
    """
    import re
    # If input is a string, parse it
    if isinstance(degrees, str):
        match = re.match(r'(-?\d+)[d:](\d+)[m:](\d+)', degrees.strip())
        if not match:
            raise ValueError("Dec string must be in 'ddmmss' or 'dd:mm:ss' format.")
        degrees, minutes, seconds = map(int, match.groups())
    
    sign = 1 if degrees >= 0 else -1
    degrees_abs = abs(degrees) + minutes/60 + seconds/3600
    return sign * degrees_abs