# This is adapted from Ginga (ginga.util.wcs, ginga.trcalc, and ginga.Bindings.ImageViewBindings).
# Please see the file licenses/GINGA_LICENSE.txt for details.
#
"""This module handles calculations based on world coordinate system (WCS)."""

import base64
import math
from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
from astropy import units as u
from astropy import coordinates as coord
from astropy.coordinates import SkyCoord
from astropy.nddata import NDData
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales

from gwcs.wcs import WCS as GWCS

from matplotlib.patches import Polygon
from jdaviz.utils import _wcs_only_label

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

    # Define an angular length we can use to determine the pixel scale
    # along east and north - we want to make sure we use a small length so
    # that the offset points still fall inside the image in case they have
    # a bounding box set.

    delta = 0.1 / 3600  # 0.1 arcsec

    xe, ye = add_offset_xy(image_wcs, x, y, delta, 0.0)
    xn, yn = add_offset_xy(image_wcs, x, y, 0.0, delta)

    # now calculate the length in pixels of those arcs
    # (planar geometry is good enough here)
    px_per_delta_e = math.sqrt(math.fabs(ye - y) ** 2 + math.fabs(xe - x) ** 2)
    px_per_delta_n = math.sqrt(math.fabs(yn - y) ** 2 + math.fabs(xn - x) ** 2)

    # now calculate the arm length in degrees for each arm
    # (this produces same-length arms)
    len_deg_e = radius_px / px_per_delta_e * delta
    len_deg_n = radius_px / px_per_delta_n * delta

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
    if getattr(data.coords, 'bounding_box', None) is not None:
        # then coords is a GWCS object
        ints = data.coords.bounding_box.intervals
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


def _rotated_wcs(
    center_world_coord,
    rotation_angle,
    pixel_scales,
    cdelt_signs,
    refdata_shape=(10, 10),
    image_shape=None
):
    image_extent = u.Quantity(image_shape, u.pix) * u.Quantity(pixel_scales)
    refdata_extent = image_extent.max()
    pixel_scales = refdata_extent / u.Quantity(refdata_shape, u.pix)

    wcs_keywords = dict(
        wcsaxes=2,
        ctype1='RA---TAN',
        ctype2='DEC--TAN',
        crpix1=refdata_shape[0] / 2 + 0.75,
        crpix2=refdata_shape[1] / 2 + 0.75,
        crval1=center_world_coord.ra.deg,
        crval2=center_world_coord.dec.deg,
        cdelt1=cdelt_signs[0] * pixel_scales[0].to_value(u.deg/u.pix),
        cdelt2=cdelt_signs[1] * pixel_scales[1].to_value(u.deg/u.pix),
        lonpole=180 - rotation_angle.to_value(u.deg),
        cname1='lon',
        cname2='lat',
    )
    wcs = WCS(wcs_keywords)
    return wcs


def _prepare_rotated_nddata(real_image_shape, wcs, rotation_angle, refdata_shape,
                            wcs_only_key="_WCS_ONLY", data=None,
                            cdelt_signs=None):
    cdelt = None
    # compute the x/y pixel scales from the WCS:
    if hasattr(wcs, 'pixel_scale_matrix'):
        pixel_scales = u.Quantity([
            value * (unit / u.pix)
            for value, unit in zip(
                proj_plane_pixel_scales(wcs), wcs.wcs.cunit
            )
        ])
        if getattr(wcs.wcs, 'cd', None) is not None:
            cdelt = np.diag(wcs.wcs.cd)
        else:
            cdelt = wcs.wcs.cdelt

    elif data.meta.get(wcs_only_key, False):
        # WCS-only layers have pixel scales in meta:
        pixel_scales = u.Quantity(data.meta['_pixel_scales'])

    elif 'wcsinfo' in data.meta and 'wcs' in data.meta and 'ra_ref' in data.meta['wcsinfo']:
        # GWCS doesn't yet have a pixel scale attr, so approximate
        # its behavior using the pixel scale method from jwst:
        pixel_scales = (2 * [compute_scale(
            data.meta['wcs'],
            (data.meta['wcsinfo']['ra_ref'],
             data.meta['wcsinfo']['dec_ref']),
            1
        )]) * u.deg / u.pix
    else:
        # fall back on CRVAL cards if they're available
        wcsinfo = (
            data.meta.get('_primary_header', None) or
            data.meta.get('wcsinfo', None) or
            data.meta.get('wcs', None)
        )
        if wcsinfo is not None and not isinstance(wcsinfo, GWCS):
            crval1 = float(wcsinfo.get('CRVAL1', wcsinfo.get('crval1')))
            crval2 = float(wcsinfo.get('CRVAL2', wcsinfo.get('crval2')))
            cdelt = [
                float(wcsinfo.get('CDELT1', wcsinfo.get('cdelt1'))),
                float(wcsinfo.get('CDELT2', wcsinfo.get('cdelt2')))
            ]
            unit = u.Unit(wcsinfo.get('CUNIT1', wcsinfo.get('cunit1')))
            fiducial = [crval1, crval2] * unit
            pixel_scales = (2 * [compute_scale(
                WCS(data.meta['_primary_header'])
                if 'wcs' not in data.meta else data.meta['wcs'],
                fiducial, None, 1
            )]) * u.deg / u.pix
        else:
            # fall back on simple approximation:
            compare_pixel_coords = [[0, 0], [0, 1]] * u.pix
            compare_sky_coords = data.coords.pixel_to_world(*compare_pixel_coords)
            separation = compare_sky_coords[0].separation(compare_sky_coords[1])
            pixel_scales = u.Quantity([separation, separation]) / u.pix

    # flip e.g. RA or Dec axes?
    if cdelt_signs is None and cdelt is not None:
        cdelt_signs = np.sign(cdelt)

    # get the world coordinates of the pixel origin
    center_pixel_coord = np.array(real_image_shape) / 2 * u.pix
    center_world_coord = wcs.pixel_to_world(*center_pixel_coord[::-1])
    rotation_angle = coord.Angle(rotation_angle).wrap_at(360 * u.deg)

    # create a WCS centered on ``filename``,
    # and rotated by ``rotation_angle``:
    new_rotated_wcs = _rotated_wcs(
        center_world_coord,
        rotation_angle,
        pixel_scales,
        cdelt_signs,
        refdata_shape=refdata_shape,
        image_shape=real_image_shape
    )

    # create a fake NDData (we use arange so data boundaries show up in Imviz
    # if it ever is accidentally exposed) with the rotated WCS:
    placeholder_data = np.nan * np.ones(refdata_shape)

    ndd = NDData(
        data=placeholder_data,
        wcs=new_rotated_wcs,
        meta={wcs_only_key: True, '_pixel_scales': pixel_scales}
    )
    return ndd


def _get_rotated_nddata_from_label(
    app, data_label, rotation_angle, refdata_shape=(10, 10),
    cdelt_signs=None, target_wcs_east_left=True, target_wcs_north_up=True
):
    """
    Create a synthetic NDData which stores WCS that approximate
    the WCS in the coords attr of the Data object with label ``data_label``
    loaded into ``app``.

    This method is useful for rotating pre-loaded datasets when
    combined with ``app._change_reference_data(data_label)``.

    Parameters
    ----------
    app : `~jdaviz.Application`
        App instance containing ``data_label``.
    data_label : str
        Data label for the Data to rotate.
    rotation_angle : `~astropy.units.Quantity`
        Angle to rotate the image counter-clockwise from its
        original orientation.
    refdata_shape : tuple
        Shape of the reference data array.

    Returns
    -------
    ndd : `~astropy.nddata.NDData`
        Contains rotated WCS and meaningless data.

    Raises
    ------
    ValueError
        Data has no WCS.
    """
    data = app.data_collection[data_label]
    if data.coords is None:
        raise ValueError(f"{data_label} has no WCS for rotation.")

    # transform WCS relative to the first loaded data entry:
    wcs = data.coords
    degn, dege, flip = get_compass_info(data.coords, data.shape)[-3:]
    has_east_left = flip
    has_north_up = True  # assumed

    if isinstance(wcs, GWCS):
        lat_axis = wcs.world_axis_names.index("lat")
        lon_axis = wcs.world_axis_names.index("lon")
    else:  # FITS WCS
        lat_axis = wcs.wcs.lat
        lon_axis = wcs.wcs.lng

    if (
        not has_east_left and target_wcs_east_left and
        'imviz-compass' in [item['name'] for item in app.state.tray_items]
    ):
        # if an east/west flip is necessary, pass that along to the compass:
        compass_plugin = app.get_tray_item_from_name('imviz-compass')
        compass_plugin.flip_horizontal = not compass_plugin.flip_horizontal

    if cdelt_signs is None:
        cdelt_signs = [None, None]
        cdelt_signs[lon_axis] = (
            1 if ((has_east_left and target_wcs_east_left) or
                  (not has_east_left and not target_wcs_east_left)) else -1
        )
        cdelt_signs[lat_axis] = (
            1 if ((has_north_up and target_wcs_north_up) or
                  (not has_north_up and not target_wcs_north_up)) else -1
        )
    else:
        if has_east_left != target_wcs_east_left:
            cdelt_signs[lon_axis] = -1
        if has_north_up != target_wcs_north_up:
            cdelt_signs[lat_axis] = -1

    return _prepare_rotated_nddata(
        data.shape,
        data.coords,
        rotation_angle,
        refdata_shape,
        wcs_only_key=_wcs_only_label,
        data=data,
        cdelt_signs=cdelt_signs
    )


# This method comes from the jwst package:
# https://github.com/spacetelescope/jwst/blob/95467186aca9784ece9451b33d437d80d550a795/jwst/assign_wcs/util.py#L103
def compute_scale(wcs, fiducial, disp_axis, pscale_ratio=1):
    """Compute scaling transform.

    Parameters
    ----------
    wcs : `~gwcs.wcs.WCS`
        Reference WCS object from which to compute a scaling factor.

    fiducial : tuple
        Input fiducial of (RA, DEC) or (RA, DEC, Wavelength) used in calculating reference points.

    disp_axis : int
        Dispersion axis integer. Assumes the same convention as `wcsinfo.dispersion_direction`

    pscale_ratio : int
        Ratio of input to output pixel scale

    Returns
    -------
    scale : float
        Scaling factor for x and y or cross-dispersion direction.

    """
    spectral = 'SPECTRAL' in wcs.output_frame.axes_type

    if spectral and disp_axis is None:  # pragma: no cover
        raise ValueError('If input WCS is spectral, a disp_axis must be given')

    crpix = np.array(wcs.invert(*fiducial))

    delta = np.zeros_like(crpix)
    spatial_idx = np.where(np.array(wcs.output_frame.axes_type) == 'SPATIAL')[0]
    delta[spatial_idx[0]] = 1

    crpix_with_offsets = np.vstack((crpix, crpix + delta, crpix + np.roll(delta, 1))).T
    crval_with_offsets = wcs(*crpix_with_offsets, with_bounding_box=False)

    coords = SkyCoord(
        ra=crval_with_offsets[spatial_idx[0]],
        dec=crval_with_offsets[spatial_idx[1]],
        unit="deg"
    )
    xscale = np.abs(coords[0].separation(coords[1]).value)
    yscale = np.abs(coords[0].separation(coords[2]).value)

    if pscale_ratio is not None:
        xscale *= pscale_ratio
        yscale *= pscale_ratio

    if spectral:  # pragma: no cover
        # Assuming scale doesn't change with wavelength
        # Assuming disp_axis is consistent with DataModel.meta.wcsinfo.dispersion.direction
        return yscale if disp_axis == 1 else xscale

    return np.sqrt(xscale * yscale)
