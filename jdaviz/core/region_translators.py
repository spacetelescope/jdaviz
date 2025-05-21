"""The ``region_translators`` module houses translations of
:ref:`regions:shapes` to :ref:`photutils:photutils-aperture` apertures.
"""
import re
from astropy import units as u
from astropy.coordinates import SkyCoord
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
        th = region_shape.angle
        aperture = EllipticalAperture(
            region_shape.center.xy, region_shape.width * 0.5, region_shape.height * 0.5,
            theta=th)

    elif isinstance(region_shape, EllipseSkyRegion):
        aperture = SkyEllipticalAperture(
            region_shape.center, region_shape.width * 0.5, region_shape.height * 0.5,
            theta=(region_shape.angle - (90 * u.deg)))

    elif isinstance(region_shape, RectanglePixelRegion):
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
            height=aperture.b * 2, angle=aperture.theta)

    elif isinstance(aperture, SkyEllipticalAperture):
        region_shape = EllipseSkyRegion(
            center=aperture.positions, width=aperture.a * 2, height=aperture.b * 2,
            angle=(aperture.theta + (90 * u.deg)))

    elif isinstance(aperture, RectangularAperture):
        region_shape = RectanglePixelRegion(
            center=positions2pixcoord(aperture.positions), width=aperture.w, height=aperture.h,
            angle=aperture.theta)

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
            outer_height=aperture.b_out * 2, angle=aperture.theta)

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
            angle=aperture.theta)

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

    >>> from jdaviz.core.region_translators import _create_polygon_skyregion_from_coords
    >>> coords = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
    >>> _create_polygon_skyregion_from_coords(coords)
    <PolygonSkyRegion(vertices=<SkyCoord (ICRS): (ra, dec) in deg
        [(10., 20.), (30., 40.), (50., 60.)]>)>

    """
    ra, dec = coords[::2], coords[1::2]
    sky_coordinates = SkyCoord(ra, dec, frame=frame, unit=unit)
    sky_region = PolygonSkyRegion(sky_coordinates)

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

    >>> from jdaviz.core.region_translators import _create_circle_skyregion_from_coords
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

    >>> from jdaviz.core.region_translators import _create_ellipse_skyregion_from_coords
    >>> coords = [10.0, 20.0, 5.0, 3.0, 45.0]
    >>> _create_ellipse_skyregion_from_coords(coords)
    <EllipseSkyRegion(center=<SkyCoord (ICRS): (ra, dec) in deg
        (10., 20.)>, width=5.0 deg, height=3.0 deg, angle=45.0 deg)>

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
    r"(?P<coordinates>(\s+-?\d+\.\d+){2,}$)",
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

    try:
        return bool(SUPPORTED_STCS_PATTERN.match(stcs_string))
    except Exception:
        return False


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
    ValueError
        Invalid inputs.

    Examples
    --------
    Translate an STC-S region to `regions.PolygonSkyRegion`:

    >>> from jdaviz.core.region_translators import stcs_string2region
    >>> stcs_string = 'POLYGON ICRS 10.0 20.0 30.0 40.0 50.0 60.0'
    >>> stcs_string2region(stcs_string)
    <PolygonSkyRegion(vertices=<SkyCoord (ICRS): (ra, dec) in deg
        [(10., 20.), (30., 40.), (50., 60.)]>)>

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


def region2stcs_string(region):
    """Convert a `regions.Region` object to an STC-S string.

    Currently supports only `CircleSkyRegion` and `EllipseSkyRegion`.

    Parameters
    ----------
    region : `regions.Region`

    Returns
    -------
    stcs_str : str
        STC-S string representing the region, using the format:
        - `CIRCLE <FRAME> <RA> <DEC> <RADIUS>`
        - `ELLIPSE <FRAME> <RA> <DEC> <WIDTH> <HEIGHT> <ANGLE>`
    """
    if isinstance(region, CircleSkyRegion):
        shape = "CIRCLE"
        coords = [region.center.ra.deg, region.center.dec.deg, region.radius.to_value(u.deg)]
    elif isinstance(region, EllipseSkyRegion):
        shape = "ELLIPSE"
        coords = [region.center.ra.deg, region.center.dec.deg,
                  region.width.to_value(u.deg),
                  region.height.to_value(u.deg),
                  region.angle.to_value(u.deg)]
    else:
        raise NotImplementedError(f"{type(region).__name__} is not supported for STC-S export")

    frame = region.center.frame.name.upper()
    if frame not in SUPPORTED_STCS_FRAME_VALUES:
        raise ValueError(f"Frame '{frame}' is not supported for STC-S export."
                         f"Supported: {SUPPORTED_STCS_FRAME_VALUES}")

    coord_parts = [f"{x:.6f}" for x in coords]

    return f"{shape} {frame} {' '.join(coord_parts)}"


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
