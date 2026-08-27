# vera rubin v1.0
# fits/fits.py

import lsst.geom as geom
import numpy as np

from lsst.afw.image import ImageF, ExposureF, Mask, MaskedImageF
from lsst.afw.geom import makeSkyWcs

##################################################################

# Low-level helpers
# ---------------------------------------------------------------------
def fits_to_exposure(data, hdr, variance_init=1.0):
    """
    Convert a NumPy array + FITS header into an LSST ExposureF,
    initializing variance and mask planes.
    
    Parameters
    ----------
    data : np.ndarray
        Image data (2D array).
    hdr : astropy.io.fits.Header
        FITS header with WCS keywords.
    variance_init : float, optional
        Default variance value to assign to all pixels.
    
    Returns
    -------
    exposure : lsst.afw.image.ExposureF
        LSST Exposure with WCS, mask, and variance.
    """

    # Create image plane
    image = ImageF(data.astype(np.float32, order="C"), deep=False)

    # Initialize mask (all zeros = good pixels)
    mask = Mask(image.getDimensions())
    mask.set(0)

    # Initialize variance plane (constant value, 1.0)
    variance = ImageF(image.getDimensions())
    variance.set(variance_init)

    # Build masked image (image, mask, variance)
    masked = MaskedImageF(image, mask, variance)

    # Wrap into an ExposureF
    exposure = ExposureF(masked)

    # Build LSST SkyWcs from FITS header keywords
    crpix = geom.Point2D(hdr["CRPIX1"], hdr["CRPIX2"])
    crval = geom.SpherePoint(hdr["CRVAL1"] * geom.degrees,
                             hdr["CRVAL2"] * geom.degrees)
    cd_matrix = np.array([[hdr["CD1_1"], hdr["CD1_2"]],
                          [hdr["CD2_1"], hdr["CD2_2"]]])

    skyWcs = makeSkyWcs(crpix, crval, cd_matrix)
    exposure.setWcs(skyWcs)

    return exposure

def cutout_fits(data, hdr, center_coord, radius_pixels, info=True, ext=0, center_pixels=True):
    """
    Cut out a FITS image centered on a celestial position with a given radius.
    If the cutout exceeds the image boundaries, missing regions are filled with zeros.
    Updates the WCS of the cutout to remain consistent.

    Parameters
    ----------
    data : 2D numpy.ndarray
        Input FITS image data.
    hdr : astropy.io.fits.Header
        FITS header associated with the image.
    center_coord : astropy.coordinates.SkyCoord or tuple(float, float)
        Cutout center in celestial coordinates (if center_pixels=False)
        or in pixel coordinates (if center_pixels=True).
    radius_pixels : float
        Radius of the cutout in pixels.
    info : bool, optional
        If True, print debugging information.
    ext : int, optional
        FITS extension (default: 0).
    center_pixels : bool, optional
        If True, `center_coord` is interpreted as pixel coordinates.
        Otherwise, it is assumed to be a `SkyCoord`.

    Returns
    -------
    cutout_data : 2D numpy.ndarray
        Cutout image data with missing regions filled with zeros.
    cutout_hdr : astropy.io.fits.Header
        FITS header updated with the cutout WCS.
    """
    from astropy.wcs import WCS
    
    wcs = WCS(hdr)

    if center_pixels:
        # Center given directly in pixels
        center_x, center_y = center_coord
    else:
        # Convert sky coordinate to pixel position
        center_x, center_y = wcs.world_to_pixel(center_coord)

    # Desired cutout bbox
    size = int(2 * radius_pixels)
    min_x = int(center_x - radius_pixels)
    min_y = int(center_y - radius_pixels)
    max_x = min_x + size
    max_y = min_y + size

    # Initialize empty cutout
    cutout_data = np.zeros((size, size), dtype=data.dtype)

    # Intersection with original image bounds
    src_x0 = max(0, min_x)
    src_y0 = max(0, min_y)
    src_x1 = min(data.shape[1], max_x)
    src_y1 = min(data.shape[0], max_y)

    # Destination indices in cutout
    dest_x0 = src_x0 - min_x
    dest_y0 = src_y0 - min_y
    dest_x1 = dest_x0 + (src_x1 - src_x0)
    dest_y1 = dest_y0 + (src_y1 - src_y0)

    # Copy valid region into cutout
    cutout_data[dest_y0:dest_y1, dest_x0:dest_x1] = \
        data[src_y0:src_y1, src_x0:src_x1]

    # Adjust WCS: shift reference pixel
    cutout_wcs = wcs.deepcopy()
    cutout_wcs.wcs.crpix[0] -= min_x
    cutout_wcs.wcs.crpix[1] -= min_y

    # Create new header with updated WCS
    cutout_hdr = hdr.copy()
    cutout_hdr.update(cutout_wcs.to_header())

    if info:
        print("Original shape:", data.shape)
        print("Cutout shape:", cutout_data.shape)
        print("Center in original (px):", (center_x, center_y))
        print("BBox: x[%d:%d], y[%d:%d]" % (min_x, max_x, min_y, max_y))
        print("Intersection source region:", (src_x0, src_x1, src_y0, src_y1))
        print("Intersection destination region:", (dest_x0, dest_x1, dest_y0, dest_y1))

    return cutout_data, cutout_hdr
