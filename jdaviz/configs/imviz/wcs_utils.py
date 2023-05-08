# This is adapted from Ginga (ginga.util.wcs, ginga.trcalc, and ginga.Bindings.ImageViewBindings).
# Please see the file licenses/GINGA_LICENSE.txt for details.
#
"""This module handles calculations based on world coordinate system (WCS)."""

import warnings
import base64
import math
from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
from astropy import units as u
from astropy import coordinates as coord
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.modeling import models
from astropy.nddata import NDDataArray
from astropy.wcs.utils import proj_plane_pixel_scales
from astropy.wcs import WCS as FitsWCS, FITSFixedWarning

from gwcs import coordinate_frames as cf
from gwcs.wcs import WCS as GWCS

from matplotlib.patches import Polygon

__all__ = ['get_compass_info', 'draw_compass_mpl']


def rotate_pt(x_arr, y_arr, theta_deg, xoff=0, yoff=0):
    """
    Rotate an array of points (x_arr, y_arr) by theta_deg offsetted
    from a center point by (xoff, yoff).
    """
    a_arr = x_arr - xoff
    b_arr = y_arr - yoff
    cos_t = np.cos(np.radians(theta_deg))
    sin_t = np.sin(np.radians(theta_deg))
    ap = (a_arr * cos_t) - (b_arr * sin_t)
    bp = (a_arr * sin_t) + (b_arr * cos_t)
    return np.asarray((ap + xoff, bp + yoff))


def add_offset_radec(ra_deg, dec_deg, delta_deg_ra, delta_deg_dec):
    """
    Algorithm to compute RA/Dec from RA/Dec base position plus tangent
    plane offsets.
    """
    # To radians
    x = math.radians(delta_deg_ra)
    y = math.radians(delta_deg_dec)
    raz = math.radians(ra_deg)
    decz = math.radians(dec_deg)

    sdecz = math.sin(decz)
    cdecz = math.cos(decz)

    d = cdecz - y * sdecz

    ra2 = math.atan2(x, d) + raz
    # Normalize ra into the range 0 to 2*pi
    twopi = math.pi * 2
    ra2 = math.fmod(ra2, twopi)
    if ra2 < 0.0:
        ra2 += twopi
    dec2 = math.atan2(sdecz + y * cdecz, math.sqrt(x * x + d * d))

    # back to degrees
    ra2_deg = math.degrees(ra2)
    dec2_deg = math.degrees(dec2)

    return (ra2_deg, dec2_deg)


def add_offset_xy(image_wcs, x, y, delta_deg_x, delta_deg_y):
    # calculate ra/dec of x,y pixel
    c = image_wcs.pixel_to_world(x, y)
    if isinstance(c, SkyCoord):
        ra_deg = c.ra.deg
        dec_deg = c.dec.deg
    else:  # list of Quantity (e.g., from FITS primary header)
        ra_deg = c[0].value
        dec_deg = c[1].value

    # add offsets
    ra2_deg, dec2_deg = add_offset_radec(ra_deg, dec_deg, delta_deg_x, delta_deg_y)

    # then back to new pixel coords
    return image_wcs.world_to_pixel_values(ra2_deg, dec2_deg)  # x2, y2


def calc_compass(image_wcs, x, y, len_deg_e, len_deg_n):

    # Get east and north coordinates
    xe, ye = list(map(float, add_offset_xy(image_wcs, x, y, len_deg_e, 0.0)))
    xn, yn = list(map(float, add_offset_xy(image_wcs, x, y, 0.0, len_deg_n)))

    return (x, y, xn, yn, xe, ye)


def calc_compass_radius(image_wcs, x, y, radius_px):
    xe, ye = add_offset_xy(image_wcs, x, y, 1.0, 0.0)
    xn, yn = add_offset_xy(image_wcs, x, y, 0.0, 1.0)

    # now calculate the length in pixels of those arcs
    # (planar geometry is good enough here)
    px_per_deg_e = math.sqrt(math.fabs(ye - y) ** 2 + math.fabs(xe - x) ** 2)
    px_per_deg_n = math.sqrt(math.fabs(yn - y) ** 2 + math.fabs(xn - x) ** 2)

    # now calculate the arm length in degrees for each arm
    # (this produces same-length arms)
    len_deg_e = radius_px / px_per_deg_e
    len_deg_n = radius_px / px_per_deg_n

    return calc_compass(image_wcs, x, y, len_deg_e, len_deg_n)


def calc_compass_center(image_wcs, image_shape, r_fac=0.5):
    # calculate center of data
    x = image_shape[1] * 0.5
    y = image_shape[0] * 0.5

    # radius we want the arms to be
    radius_px = min(image_shape) * r_fac

    return calc_compass_radius(image_wcs, x, y, radius_px)


def get_compass_info(image_wcs, image_shape, r_fac=0.4):
    """Calculate WCS compass parameters.
    North (N) is up and East (E) is left.

    Parameters
    ----------
    image_wcs : obj
        WCS that is compatible with APE 14.

    image_shape : tuple of int
        Shape of the image in the form of ``(ny, nx)``.

    r_fac : float
        Scale factor for compass arrow length.

    Returns
    -------
    x, y : float
        Pixel positions for the center of the compass.

    xn, yn : float
        Pixel positions for N of the compass.

    xe, ye : float
        Pixel positions for E of the compass.

    degn, dege : float
        Rotation angles for N and E, in degrees, for the compass, respectively.

    xflip : bool
        Should display flip on X?

    """
    x, y, xn, yn, xe, ye = calc_compass_center(image_wcs, image_shape, r_fac=r_fac)
    degn = math.degrees(math.atan2(xn - x, yn - y))

    # rotate east point also by degn
    xe2, ye2 = rotate_pt(xe, ye, degn, xoff=x, yoff=y)
    dege = math.degrees(math.atan2(xe2 - x, ye2 - y))

    # if right-hand image, flip it to make left hand
    xflip = False
    if dege > 0.0:
        xflip = not xflip
    if xflip and not np.isclose(degn, 0):
        degn = -degn

    return x, y, xn, yn, xe, ye, degn, dege, xflip


def draw_compass_mpl(image, orig_shape=None, wcs=None, show=True, zoom_limits=None, **kwargs):
    """Visualize the compass using Matplotlib.

    Parameters
    ----------
    image : ndarray
        2D Numpy array (can be resampled).

    orig_shape : tuple of int or `None`
        The original (non-resampled) array shape in ``(ny, nx)``, if different.

    wcs : obj or `None`
        Associated original image WCS that is compatible with APE 14.
        If `None` given, compass is not drawn.

    show : bool
        Display the plot.

    zoom_limits : ndarray or None
        If not `None`, also draw a rectangle to represent the
        current zoom limits in the form of list of ``(x, y)``
        representing the four corners of the zoom box.

    kwargs : dict
        Keywords for ``matplotlib.pyplot.imshow``.

    Returns
    -------
    image_base64 : str
        Decoded buffer for Compass plugin.

    """
    if orig_shape is None:
        orig_shape = image.shape

    if not show:
        plt.ioff()

    fig, ax = plt.subplots()
    ax.imshow(image, extent=[-0.5, orig_shape[1] - 0.5, -0.5, orig_shape[0] - 0.5],
              origin='lower', cmap='gray', **kwargs)

    if wcs is not None:
        try:
            x, y, xn, yn, xe, ye, degn, dege, xflip = get_compass_info(wcs, orig_shape)
        except Exception:
            wcs = None
        else:
            # TODO: Not sure what xflip really do, ask Eric Jeschke later.
            # if xflip:
            #    plt.imshow(np.fliplr(image), origin='lower')

            # Positive here is counter-clockwise, hence the minus sign in comment.
            ax.plot(x, y, marker='o', color='cyan', markersize=5)
            ax.annotate('N', xy=(x, y), xytext=(xn, yn),
                        arrowprops={'arrowstyle': '<-', 'color': 'cyan', 'lw': 1.5},
                        color='cyan', fontsize=16, va='center', ha='center')  # rotation=-degn
            ax.annotate('E', xy=(x, y), xytext=(xe, ye),
                        arrowprops={'arrowstyle': '<-', 'color': 'cyan', 'lw': 1.5},
                        color='cyan', fontsize=16, va='center', ha='center')  # rotation=-dege
    if wcs is None:
        x = orig_shape[1] * 0.5
        y = orig_shape[0] * 0.5
        ax.plot(x, y, marker='o', color='yellow', markersize=5)

    # Also draw X/Y compass.
    r_xy = float(min(orig_shape)) * 0.25
    ax.annotate('X', xy=(x, y), xytext=(x + r_xy, y),
                arrowprops={'arrowstyle': '<-', 'color': 'yellow', 'lw': 1.5},
                color='yellow', fontsize=16, va='center', ha='center')
    ax.annotate('Y', xy=(x, y), xytext=(x, y + r_xy),
                arrowprops={'arrowstyle': '<-', 'color': 'yellow', 'lw': 1.5},
                color='yellow', fontsize=16, va='center', ha='center')

    if zoom_limits is not None:
        ax.add_patch(Polygon(
            zoom_limits, closed=True, linewidth=1.5, edgecolor='r', facecolor='none'))

    if show:
        plt.draw()
        plt.show()

    buff = BytesIO()
    plt.savefig(buff)
    plt.style.use('default')
    plt.close()

    return base64.b64encode(buff.getvalue()).decode('utf-8')


def data_outside_gwcs_bounding_box(data, x, y):
    """This is for internal use by Imviz coordinates transformation only."""
    outside_bounding_box = False
    if hasattr(data.coords, '_orig_bounding_box'):
        # then coords is a GWCS object and had its bounding box cleared
        # by the Imviz parser
        ints = data.coords._orig_bounding_box.intervals
        if isinstance(ints[0].lower, u.Quantity):
            bb_xmin = ints[0].lower.value
            bb_xmax = ints[0].upper.value
            bb_ymin = ints[1].lower.value
            bb_ymax = ints[1].upper.value
        else:  # pragma: no cover
            bb_xmin = ints[0].lower
            bb_xmax = ints[0].upper
            bb_ymin = ints[1].lower
            bb_ymax = ints[1].upper
        if not (bb_xmin <= x <= bb_xmax and bb_ymin <= y <= bb_ymax):
            outside_bounding_box = True  # Has to be Python bool, not Numpy bool_
    return outside_bounding_box


def _get_fits_wcs_from_file(filename):
    header = fits.getheader(filename)
    with warnings.catch_warnings():
        # Ignore a warning on using DATE-OBS in place of MJD-OBS
        warnings.filterwarnings('ignore', message="'datfix' made the change",
                                category=FITSFixedWarning)
        wcs = FitsWCS(header)

    return wcs


def rotated_gwcs(
    center_world_coord,
    rotation_angle,
    pixel_scales,
    cdelt_signs,
    refdata_shape=(2, 2)
):
    # based on ``gwcs_simple_imaging_units`` in gwcs:
    #   https://github.com/spacetelescope/gwcs/blob/
    #   eec9a2b6de8356495f405de3dc6531538589ce5d/gwcs/tests/conftest.py#L165
    rho = rotation_angle
    sin_rho = np.sin(rho.to_value(u.rad))
    cos_rho = np.cos(rho.to_value(u.rad))
    rotation_matrix = np.array([[cos_rho, -sin_rho],
                                [sin_rho, cos_rho]])

    # "rescale" the pixel scales. Scaling constant was tuned so that the
    # synthetic image is about the same size on the sky as the input image
    rescale_pixel_scale = np.array(refdata_shape) / 1000

    shift_by_crpix = (
        models.Shift(-refdata_shape[0] / 2 * u.pixel) &
        models.Shift(-refdata_shape[1] / 2 * u.pixel)
    )

    # multiplying by +/-1 can flip north/south or east/west
    flip_axes = models.Multiply(cdelt_signs[0]) & models.Multiply(cdelt_signs[1])
    rotation = models.AffineTransformation2D(
        rotation_matrix * u.deg, translation=[0, 0] * u.deg
    )
    rotation.input_units_equivalencies = {
        "x": u.pixel_scale(pixel_scales[0] * rescale_pixel_scale[0]),
        "y": u.pixel_scale(pixel_scales[1] * rescale_pixel_scale[1])
    }
    rotation.inverse = models.AffineTransformation2D(
        np.linalg.inv(rotation_matrix) * u.pix, translation=[0, 0] * u.pix
    )
    rotation.inverse.input_units_equivalencies = {
        "x": u.pixel_scale(1 / (pixel_scales[0] * rescale_pixel_scale[0])),
        "y": u.pixel_scale(1 / (pixel_scales[1] * rescale_pixel_scale[1]))
    }
    tan = models.Pix2Sky_TAN()
    celestial_rotation = models.RotateNative2Celestial(
        center_world_coord.ra, center_world_coord.dec, 180 * u.deg
    )

    det2sky = (
        flip_axes | shift_by_crpix | rotation |
        tan | celestial_rotation
    )
    det2sky.name = "linear_transform"

    detector_frame = cf.Frame2D(
        name="detector",
        axes_names=("x", "y"),
        unit=(u.pix, u.pix)
    )
    sky_frame = cf.CelestialFrame(
        reference_frame=coord.ICRS(),
        name='icrs',
        unit=(u.deg, u.deg)
    )
    pipeline = [
        (detector_frame, det2sky),
        (sky_frame, None)
    ]

    return GWCS(pipeline)


def _prepare_rotated_nddata(wcs, rotation_angle, refdata_shape):
    # get the world coordinates of the central pixel
    real_image_shape = np.array(wcs.array_shape)
    central_pixel_coord = real_image_shape / 2 * u.pix
    central_world_coord = wcs.pixel_to_world(*central_pixel_coord)
    rotation_angle = coord.Angle(rotation_angle).wrap_at(360 * u.deg)

    # compute the x/y plate scales from the WCS:
    pixel_scales = [
        value * unit / u.pix
        for value, unit in zip(
            proj_plane_pixel_scales(wcs), wcs.wcs.cunit
        )
    ]

    # flip e.g. RA or Dec axes?
    cdelt_signs = np.sign(wcs.wcs.cdelt)

    # create a GWCS centered on ``filename``,
    # and rotated by ``rotation_angle``:
    new_rotated_gwcs = rotated_gwcs(
        central_world_coord, rotation_angle, pixel_scales, cdelt_signs
    )

    # create an all-nan NDDataArray with the rotated GWCS:
    ndd = NDDataArray(
        data=np.nan * np.ones(refdata_shape),
        wcs=new_rotated_gwcs,
    )
    return ndd


def _get_rotated_nddata_from_fits(filename, rotation_angle, refdata_shape=(2, 2)):
    """
    Create a synthetic NDDataArray which stores GWCS that approximate
    the FITS WCS in ``filename`` rotated by ``rotation_angle``.

    This method is useful for ensuring that future datasets are loaded
    in the correct orientation.

    Parameters
    ----------
    filename : path-like, str
        FITS file to use as reference
    rotation_angle : `~astropy.units.Quantity`
        Angle to rotate the image counter-clockwise from its
        original orientation
    refdata_shape : tuple
        Shape of the reference data array

    Returns
    -------
    ndd : `~astropy.nddata.NDDataArray`
        Data are all NaNs, wcs are rotated.
    """
    # get the FITS WCS from the file:
    wcs = _get_fits_wcs_from_file(filename)

    return _prepare_rotated_nddata(wcs, rotation_angle, refdata_shape)


def _get_rotated_nddata_from_label(app, data_label, rotation_angle, refdata_shape=(2, 2)):
    """
    Create a synthetic NDDataArray which stores GWCS that approximate
    the WCS in the coords attr of the Data object with label ``data_label``
    loaded into ``app``.

    This method is useful for rotating pre-loaded datasets when
    combined with ``app._change_reference_data(data_label)``.

    Parameters
    ----------
    app : `~jdaviz.Application`
        App instance containing ``data_label``
    data_label : str
        Data label for the Data to rotate
    rotation_angle : `~astropy.units.Quantity`
        Angle to rotate the image counter-clockwise from its
        original orientation
    refdata_shape : tuple
        Shape of the reference data array

    Returns
    -------
    ndd : `~astropy.nddata.NDDataArray`
        Data are all NaNs, wcs are rotated.
    """
    # get the WCS from the Data object's coords attribute:
    [wcs] = [
        data.coords for data in app.data_collection
        if data.label == data_label
    ]

    return _prepare_rotated_nddata(wcs, rotation_angle, refdata_shape)
