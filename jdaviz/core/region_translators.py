"""The ``region_translators`` module houses translations of
:ref:`regions:shapes` to :ref:`photutils:photutils-aperture` apertures.
"""
import re
import numpy as np
import photutils
from astropy import units as u
from astropy.coordinates import Angle, SkyCoord
from astropy.utils import minversion
from glue.core.roi import CircularROI, EllipticalROI, RectangularROI, CircularAnnulusROI
from photutils.aperture import (CircularAperture, SkyCircularAperture,
                                EllipticalAperture, SkyEllipticalAperture,
                                RectangularAperture, SkyRectangularAperture,
                                CircularAnnulus, SkyCircularAnnulus,
                                EllipticalAnnulus, SkyEllipticalAnnulus,
                                RectangularAnnulus, SkyRectangularAnnulus)
from regions import (CirclePixelRegion, CircleSkyRegion,
                     EllipsePixelRegion, EllipseSkyRegion,
                     RectanglePixelRegion, RectangleSkyRegion,
                     CircleAnnulusPixelRegion, CircleAnnulusSkyRegion,
                     EllipseAnnulusPixelRegion, EllipseAnnulusSkyRegion,
                     RectangleAnnulusPixelRegion, RectangleAnnulusSkyRegion,
                     PixCoord, PolygonSkyRegion)

__all__ = ['regions2roi', 'regions2aperture', 'aperture2regions']

PHOTUTILS_LT_2_2 = not minversion(photutils, "2.1.1.dev60")  # no 2.2.dev tag


def _get_region_from_spatial_subset(plugin_obj, subset_state):
    """Convert the given ``glue`` ROI subset state to ``regions`` shape.

    .. note:: This is for internal use only in Imviz plugins.

    Parameters
    ----------
    plugin_obj : obj
        Plugin instance that needs this translation.
        The plugin is assumed to have a special setup that gives
        it access to these attributes: ``app`` and ``app._align_by``.

    subset_state : obj
        ROI subset state to translate.

    Returns
    -------
    reg : `regions.Region`
        An equivalent ``regions`` shape. This can be a pixel or sky
        region, so the plugin needs to be able to deal with both.

    See Also
    --------
    regions2roi

    """
    from glue_astronomy.translators.regions import roi_subset_state_to_region

    # Subset is defined against its parent. This is not necessarily
    # the current viewer reference data, which can be changed.

    # Mixed link types no longer allowed, so just check app setting.
    align_by = plugin_obj.app._align_by

    return roi_subset_state_to_region(subset_state, to_sky=(align_by == 'wcs'))


def regions2roi(region_shape, wcs=None):
    """Convert a given ``regions`` shape to ``glue`` ROI.

    This is the opposite of what is offered by
    ``glue_astronomy.translators.regions.AstropyRegionsHandler.to_object``
    but does not cover all the same shapes exactly.

    Parameters
    ----------
    region_shape : `regions.Region`
        A supported ``regions`` shape.

    wcs : `~astropy.wcs.WCS` or `None`
        A compatible WCS object, if required.
        **This is only used for sky aperture.**

    Returns
    -------
    roi : `glue.core.roi.Roi`
        An equivalent ``glue`` ROI.

    Raises
    ------
    ValueError
        WCS is required but not provided.

    NotImplementedError
        The given ``regions`` shape is not supported.

    Examples
    --------
    Translate a `regions.CirclePixelRegion` to `glue.core.roi.CircularROI`:

    >>> from regions import CirclePixelRegion, PixCoord
    >>> from jdaviz.core.region_translators import regions2roi
    >>> region_shape = CirclePixelRegion(center=PixCoord(x=42, y=43), radius=4.2)
    >>> regions2roi(region_shape)  # doctest: +ELLIPSIS
    <glue.core.roi.CircularROI object at ...>

    """
    if isinstance(region_shape, (CircleSkyRegion, EllipseSkyRegion, RectangleSkyRegion,
                                 CircleAnnulusSkyRegion)):
        if wcs is None:
            raise ValueError(f'WCS must be provided for {region_shape}')

        # Convert sky to pixel region first, if necessary.
        region_shape = region_shape.to_pixel(wcs)

    if isinstance(region_shape, CirclePixelRegion):
        roi = CircularROI(
            xc=region_shape.center.x, yc=region_shape.center.y, radius=region_shape.radius)
    elif isinstance(region_shape, EllipsePixelRegion):
        roi = EllipticalROI(
            xc=region_shape.center.x, yc=region_shape.center.y,
            radius_x=region_shape.width * 0.5, radius_y=region_shape.height * 0.5,
            theta=region_shape.angle.to_value(u.radian))
    elif isinstance(region_shape, RectanglePixelRegion):
        half_w = region_shape.width * 0.5
        half_h = region_shape.height * 0.5
        xmin = region_shape.center.x - half_w
        xmax = region_shape.center.x + half_w
        ymin = region_shape.center.y - half_h
        ymax = region_shape.center.y + half_h
        roi = RectangularROI(
            xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax,
            theta=region_shape.angle.to_value(u.radian))
    elif isinstance(region_shape, CircleAnnulusPixelRegion):
        roi = CircularAnnulusROI(
            xc=region_shape.center.x, yc=region_shape.center.y,
            inner_radius=region_shape.inner_radius, outer_radius=region_shape.outer_radius)
    else:
        raise NotImplementedError(f'{region_shape.__class__.__name__} is not supported')

    return roi


def regions2aperture(region_shape):
    """Convert a given ``regions`` shape to ``photutils`` aperture.

    Parameters
    ----------
    region_shape : `regions.Region`
        A supported ``regions`` shape.

    Returns
    -------
    aperture : `photutils.aperture.Aperture`
        An equivalent ``photutils`` aperture.

    Raises
    ------
    NotImplementedError
        The given ``regions`` shape is not supported.

    Examples
    --------
    Translate a `regions.CirclePixelRegion` to `photutils.aperture.CircularAperture`:

    >>> from regions import CirclePixelRegion, PixCoord
    >>> from jdaviz.core.region_translators import regions2aperture
    >>> region_shape = CirclePixelRegion(center=PixCoord(x=42, y=43), radius=4.2)
    >>> regions2aperture(region_shape)
    <CircularAperture([42., 43.], r=4.2)>

    See Also
    --------
    aperture2regions

    """
    if isinstance(region_shape, CirclePixelRegion):
        aperture = CircularAperture(region_shape.center.xy, region_shape.radius)

    elif isinstance(region_shape, CircleSkyRegion):
        aperture = SkyCircularAperture(region_shape.center, region_shape.radius)

    elif isinstance(region_shape, EllipsePixelRegion):
        if PHOTUTILS_LT_2_2:
            th = region_shape.angle.to_value(u.radian)
        else:
            th = region_shape.angle
        aperture = EllipticalAperture(
            region_shape.center.xy, region_shape.width * 0.5, region_shape.height * 0.5,
            theta=th)

    elif isinstance(region_shape, EllipseSkyRegion):
        aperture = SkyEllipticalAperture(
            region_shape.center, region_shape.width * 0.5, region_shape.height * 0.5,
            theta=(region_shape.angle - (90 * u.deg)))

    elif isinstance(region_shape, RectanglePixelRegion):
        if PHOTUTILS_LT_2_2:
            th = region_shape.angle.to_value(u.radian)
        else:
            th = region_shape.angle
        aperture = RectangularAperture(
            region_shape.center.xy, region_shape.width, region_shape.height,
            theta=th)

    elif isinstance(region_shape, RectangleSkyRegion):
        aperture = SkyRectangularAperture(
            region_shape.center, region_shape.width, region_shape.height,
            theta=(region_shape.angle - (90 * u.deg)))

    elif isinstance(region_shape, CircleAnnulusPixelRegion):
        aperture = CircularAnnulus(
            region_shape.center.xy, region_shape.inner_radius, region_shape.outer_radius)

    elif isinstance(region_shape, CircleAnnulusSkyRegion):
        aperture = SkyCircularAnnulus(
            region_shape.center, region_shape.inner_radius, region_shape.outer_radius)

    elif isinstance(region_shape, EllipseAnnulusPixelRegion):
        if PHOTUTILS_LT_2_2:
            th = region_shape.angle.to_value(u.radian)
        else:
            th = region_shape.angle
        aperture = EllipticalAnnulus(
            region_shape.center.xy, region_shape.inner_width * 0.5, region_shape.outer_width * 0.5,
            region_shape.outer_height * 0.5, b_in=region_shape.inner_height * 0.5,
            theta=th)

    elif isinstance(region_shape, EllipseAnnulusSkyRegion):
        aperture = SkyEllipticalAnnulus(
            region_shape.center, region_shape.inner_width * 0.5, region_shape.outer_width * 0.5,
            region_shape.outer_height * 0.5, b_in=region_shape.inner_height * 0.5,
            theta=(region_shape.angle - (90 * u.deg)))

    elif isinstance(region_shape, RectangleAnnulusPixelRegion):
        if PHOTUTILS_LT_2_2:
            th = region_shape.angle.to_value(u.radian)
        else:
            th = region_shape.angle
        aperture = RectangularAnnulus(
            region_shape.center.xy, region_shape.inner_width, region_shape.outer_width,
            region_shape.outer_height, h_in=region_shape.inner_height,
            theta=th)

    elif isinstance(region_shape, RectangleAnnulusSkyRegion):
        aperture = SkyRectangularAnnulus(
            region_shape.center, region_shape.inner_width, region_shape.outer_width,
            region_shape.outer_height, h_in=region_shape.inner_height,
            theta=(region_shape.angle - (90 * u.deg)))

    else:
        raise NotImplementedError(f'{region_shape.__class__.__name__} is not supported')

    return aperture


def aperture2regions(aperture):
    """Convert a given ``photutils`` aperture to ``regions`` shape.

    Parameters
    ----------
    aperture : `photutils.aperture.Aperture`
        An equivalent ``photutils`` aperture.

    Returns
    -------
    region_shape : `regions.Region`
        A supported ``regions`` shape.

    Raises
    ------
    NotImplementedError
        The given ``photutils`` aperture is not supported.

    ValueError
        Invalid inputs.

    Examples
    --------
    Translate a `photutils.aperture.CircularAperture` to `regions.CirclePixelRegion`:

    >>> from photutils.aperture import CircularAperture
    >>> from jdaviz.core.region_translators import aperture2regions
    >>> aperture = CircularAperture((42, 43), 4.2)
    >>> aperture2regions(aperture)
    <CirclePixelRegion(center=PixCoord(x=42.0, y=43.0), radius=4.2)>

    See Also
    --------
    regions2aperture

    """
    if isinstance(aperture, CircularAperture):
        region_shape = CirclePixelRegion(
            center=positions2pixcoord(aperture.positions), radius=aperture.r)

    elif isinstance(aperture, SkyCircularAperture):
        region_shape = CircleSkyRegion(center=aperture.positions, radius=aperture.r)

    elif isinstance(aperture, EllipticalAperture):
        region_shape = EllipsePixelRegion(
            center=positions2pixcoord(aperture.positions), width=aperture.a * 2,
            height=aperture.b * 2, angle=theta2angle(aperture.theta))

    elif isinstance(aperture, SkyEllipticalAperture):
        region_shape = EllipseSkyRegion(
            center=aperture.positions, width=aperture.a * 2, height=aperture.b * 2,
            angle=(aperture.theta + (90 * u.deg)))

    elif isinstance(aperture, RectangularAperture):
        region_shape = RectanglePixelRegion(
            center=positions2pixcoord(aperture.positions), width=aperture.w, height=aperture.h,
            angle=theta2angle(aperture.theta))

    elif isinstance(aperture, SkyRectangularAperture):
        region_shape = RectangleSkyRegion(
            center=aperture.positions, width=aperture.w, height=aperture.h,
            angle=(aperture.theta + (90 * u.deg)))

    elif isinstance(aperture, CircularAnnulus):
        region_shape = CircleAnnulusPixelRegion(
            center=positions2pixcoord(aperture.positions), inner_radius=aperture.r_in,
            outer_radius=aperture.r_out)

    elif isinstance(aperture, SkyCircularAnnulus):
        region_shape = CircleAnnulusSkyRegion(
            center=aperture.positions, inner_radius=aperture.r_in, outer_radius=aperture.r_out)

    elif isinstance(aperture, EllipticalAnnulus):
        region_shape = EllipseAnnulusPixelRegion(
            center=positions2pixcoord(aperture.positions), inner_width=aperture.a_in * 2,
            inner_height=aperture.b_in * 2, outer_width=aperture.a_out * 2,
            outer_height=aperture.b_out * 2, angle=theta2angle(aperture.theta))

    elif isinstance(aperture, SkyEllipticalAnnulus):
        region_shape = EllipseAnnulusSkyRegion(
            center=aperture.positions, inner_width=aperture.a_in * 2,
            inner_height=aperture.b_in * 2, outer_width=aperture.a_out * 2,
            outer_height=aperture.b_out * 2,
            angle=(aperture.theta + (90 * u.deg)))

    elif isinstance(aperture, RectangularAnnulus):
        region_shape = RectangleAnnulusPixelRegion(
            center=positions2pixcoord(aperture.positions), inner_width=aperture.w_in,
            inner_height=aperture.h_in, outer_width=aperture.w_out, outer_height=aperture.h_out,
            angle=theta2angle(aperture.theta))

    elif isinstance(aperture, SkyRectangularAnnulus):
        region_shape = RectangleAnnulusSkyRegion(
            center=aperture.positions, inner_width=aperture.w_in, inner_height=aperture.h_in,
            outer_width=aperture.w_out, outer_height=aperture.h_out,
            angle=(aperture.theta + (90 * u.deg)))

    else:  # pragma: no cover
        raise NotImplementedError(f'{aperture.__class__.__name__} is not supported')

    return region_shape


def _create_polygon_skyregion_from_coords(coords, frame='icrs', unit=u.deg):
    """Create a `regions.PolygonSkyRegion` from given coordinates.

    Parameters
    ----------
    coords : list
        List of coordinates in the form of [ra1, dec1, ra2, dec2, ...].

    frame : str, optional
        Coordinate frame. Default is 'icrs'.

    unit : `~astropy.units.Unit`, optional
        Unit of the coordinates. Default is `~astropy.units.deg`.

    Returns
    -------
    sky_region : `regions.PolygonSkyRegion`
        A polygon sky region.

    Examples
    --------
    Create a `regions.PolygonSkyRegion` from given coordinates:

    >>> from jdaviz.core.region_translators import create_polygon_skyregion_from_coords
    >>> coords = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
    >>> _create_polygon_skyregion_from_coords(coords)
    <PolygonSkyRegion(vertices=[<SkyCoord (ICRS): (ra, dec) in deg
        (10., 20.), (30., 40.), (50., 60.)>])>

    """
    ra = np.array(coords[::2], dtype=float)
    dec = np.array(coords[1::2], dtype=float)
    sky_coordinates = SkyCoord(ra, dec, frame=frame, unit=unit)
    sky_region = PolygonSkyRegion(sky_coordinates)

    # Need these for zooming
    length = sky_coordinates[0].separation(sky_coordinates[1])
    width = sky_coordinates[1].separation(sky_coordinates[2])
    sky_region.height = Angle(max(length, width), unit)
    sky_region.center = SkyCoord(ra.mean(), dec.mean(), unit=unit)

    return sky_region


def _create_circle_skyregion_from_coords(coords, frame='icrs', unit=u.deg):
    """Create a `regions.CircleSkyRegion` from given coordinates.

    Parameters
    ----------
    coords : list
        List of coordinates in the form of [ra, dec, radius].

    frame : str, optional
        Coordinate frame. Default is 'icrs'.

    unit : `~astropy.units.Unit`, optional
        Unit of the coordinates. Default is `~astropy.units.deg`.

    Returns
    -------
    sky_region : `regions.CircleSkyRegion`
        A circle sky region.

    Examples
    --------
    Create a `regions.CircleSkyRegion` from given coordinates:

    >>> from jdaviz.core.region_translators import create_circle_skyregion_from_coords
    >>> coords = [10.0, 20.0, 5.0]
    >>> _create_circle_skyregion_from_coords(coords)
    <CircleSkyRegion(center=<SkyCoord (ICRS): (ra, dec) in deg (10., 20.)>, radius=5.0 deg)>

    """
    sky_coordinates = SkyCoord(coords[0], coords[1], frame=frame, unit=unit)
    sky_region = CircleSkyRegion(center=sky_coordinates, radius=coords[2] * unit)

    return sky_region


def _create_ellipse_skyregion_from_coords(coords, frame='icrs', unit=u.deg):
    """Create a `regions.EllipseSkyRegion` from given coordinates.

    Parameters
    ----------
    coords : list
        List of coordinates in the form of [ra, dec, width, height, angle].

    frame : str, optional
        Coordinate frame. Default is 'icrs'.

    unit : `~astropy.units.Unit`, optional
        Unit of the coordinates. Default is `~astropy.units.deg`.

    Returns
    -------
    sky_region : `regions.EllipseSkyRegion`
        An ellipse sky region.

    Examples
    --------
    Create a `regions.EllipseSkyRegion` from given coordinates:

    >>> from jdaviz.core.region_translators import create_ellipse_skyregion_from_coords
    >>> coords = [10.0, 20.0, 5.0, 3.0, 45.0]
    >>> _create_ellipse_skyregion_from_coords(coords)
    <EllipseSkyRegion(center=<SkyCoord (ICRS): (ra, dec) in deg (10., 20.)>,
        width=5.0 deg, height=3.0 deg, angle=45.0 deg)>

    """
    sky_coordinates = SkyCoord(coords[0], coords[1], frame=frame, unit=unit)
    sky_region = EllipseSkyRegion(center=sky_coordinates, width=coords[2] * unit,
                                  height=coords[3] * unit, angle=coords[4] * unit)

    return sky_region


SUPPORTED_STCS_SHAPE_VALUES = ('POLYGON', 'CIRCLE', 'ELLIPSE', )
SUPPORTED_STCS_FRAME_VALUES = ('ICRS', 'J2000', 'FK5', )
STCS_SHAPE_PATTERN = '|'.join(SUPPORTED_STCS_SHAPE_VALUES)
STCS_FRAME_PATTERN = '|'.join(SUPPORTED_STCS_FRAME_VALUES)
SUPPORTED_STCS_PATTERN = re.compile(
    fr"^(?P<shape>({'|'.join(SUPPORTED_STCS_SHAPE_VALUES)}))"
    fr"(?P<frame>(\s+({'|'.join(SUPPORTED_STCS_FRAME_VALUES)})))*"
    r"(?P<coordinates>(\s+-?\d+\.\d+)+$)",
    re.IGNORECASE)
SKY_REGION_FROM_COORDS_FACTORY = {
    'polygon': _create_polygon_skyregion_from_coords,
    'circle': _create_circle_skyregion_from_coords,
    'ellipse': _create_ellipse_skyregion_from_coords,
}


def is_stcs_string(stcs_string):
    """Check if the given string is a valid STC-S string.

    Parameters
    ----------
    stcs_string : str
        A string to check.

    Returns
    -------
    is_stcs : bool
        `True` if the given string is a valid STC-S string, otherwise `False`.

    Examples
    --------
    Check if a given string is a valid STC-S string:

    >>> from jdaviz.core.region_translators import is_stcs_string
    >>> stcs_string = 'POLYGON ICRS 10.0 20.0 30.0 40.0 50.0 60.0'
    >>> is_stcs_string(stcs_string)
    True

    """
    return bool(SUPPORTED_STCS_PATTERN.match(stcs_string))


def stcs_string2region(stcs_string):
    """Convert a given STC-S string to ``regions`` shape.

    Parameters
    ----------
    stcs_string : str
        A valid STC-S string.

    Returns
    -------
    sky_region : `regions.Region`
        A supported ``regions`` shape.

    Raises
    ------
    NotImplementedError
        The given STC-S string is not supported.

    ValueError
        Invalid inputs.

    Examples
    --------
    Translate an STC-S region to `regions.PolygonSkyRegion`:

    >>> from jdaviz.core.region_translators import stcs_string2region
    >>> stcs_string = 'POLYGON ICRS 10.0 20.0 30.0 40.0 50.0 60.0'
    >>> stcs_string2region(stcs_string)
    <PolygonSkyRegion(vertices=[<SkyCoord (ICRS): (ra, dec) in deg
        (10., 20.), (30., 40.), (50., 60.)>])>

    """

    if not isinstance(stcs_string, str):
        raise ValueError('STC-S string must be a string.')

    _match = SUPPORTED_STCS_PATTERN.match(stcs_string)

    # Check if the STC-S string is valid, otherwise raise an error
    if not _match:
        raise ValueError(f'Invalid STC-S string: {stcs_string}')

    # Extract the shape, frame, and coordinates from the STC-S string
    shape = _match.group('shape').strip().lower()
    frame = _match.group('frame').strip().lower() if _match.group('frame') else 'icrs'
    coordinates = list(map(float, _match.group('coordinates').strip().split()))

    return SKY_REGION_FROM_COORDS_FACTORY[shape](coordinates, frame=frame)


def positions2pixcoord(positions):
    """Convert ``photutils`` aperture positions to `~regions.PixCoord`
    that is acceptable by ``regions`` shape.
    """
    if positions.shape != (2, ):
        raise ValueError('regions shape only accepts scalar x and y positions')
    if isinstance(positions, u.Quantity):
        pixcoord = PixCoord(x=positions[0].value, y=positions[1].value)
    else:
        pixcoord = PixCoord(x=positions[0], y=positions[1])
    return pixcoord


def theta2angle(theta):
    """Convert ``photutils`` theta to ``regions`` angle for pixel regions."""
    if PHOTUTILS_LT_2_2:
        return Angle(theta, u.radian)
    return theta  # This whole function can be deleted when we remove PHOTUTILS_LT_2_2
