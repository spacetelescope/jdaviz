"""The ``region_translators`` module houses translations of
:ref:`regions:shapes` to :ref:`photutils:photutils-aperture` apertures.
"""
from astropy import units as u
from astropy.coordinates import Angle
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
                     RectangleAnnulusPixelRegion, RectangleAnnulusSkyRegion, PixCoord)

__all__ = ['regions2roi', 'regions2aperture', 'aperture2regions']


def _get_region_from_spatial_subset(plugin_obj, subset_state, dataset=None):
    """Convert the given ``glue`` ROI subset state to ``regions`` shape.

    .. note:: This is for internal use only in Imviz plugins.

    Parameters
    ----------
    plugin_obj : obj
        Plugin instance that needs this translation.
        The plugin is assumed to have a special setup that gives
        it access to these attributes: ``app`` and ``dataset_selected``.
        The ``app._jdaviz_helper.get_link_type`` method must also
        exist.

    subset_state : obj
        ROI subset state to translate.

    dataset : string, optional
        Name of the dataset.  If not provided, will look for ``plugin_obj.dataset_selected``.

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

    if dataset is None:
        dataset = plugin_obj.dataset_selected

    # See https://github.com/spacetelescope/jdaviz/issues/2230
    link_type = plugin_obj.app._jdaviz_helper.get_link_type(
        subset_state.xatt.parent.label, dataset)

    return roi_subset_state_to_region(subset_state, to_sky=(link_type == 'wcs'))


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
        aperture = EllipticalAperture(
            region_shape.center.xy, region_shape.width * 0.5, region_shape.height * 0.5,
            theta=region_shape.angle.to_value(u.radian))

    elif isinstance(region_shape, EllipseSkyRegion):
        aperture = SkyEllipticalAperture(
            region_shape.center, region_shape.width * 0.5, region_shape.height * 0.5,
            theta=(region_shape.angle - (90 * u.deg)))

    elif isinstance(region_shape, RectanglePixelRegion):
        aperture = RectangularAperture(
            region_shape.center.xy, region_shape.width, region_shape.height,
            theta=region_shape.angle.to_value(u.radian))

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
        aperture = EllipticalAnnulus(
            region_shape.center.xy, region_shape.inner_width * 0.5, region_shape.outer_width * 0.5,
            region_shape.outer_height * 0.5, b_in=region_shape.inner_height * 0.5,
            theta=region_shape.angle.to_value(u.radian))

    elif isinstance(region_shape, EllipseAnnulusSkyRegion):
        aperture = SkyEllipticalAnnulus(
            region_shape.center, region_shape.inner_width * 0.5, region_shape.outer_width * 0.5,
            region_shape.outer_height * 0.5, b_in=region_shape.inner_height * 0.5,
            theta=(region_shape.angle - (90 * u.deg)))

    elif isinstance(region_shape, RectangleAnnulusPixelRegion):
        aperture = RectangularAnnulus(
            region_shape.center.xy, region_shape.inner_width, region_shape.outer_width,
            region_shape.outer_height, h_in=region_shape.inner_height,
            theta=region_shape.angle.to_value(u.radian))

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
    return Angle(theta, u.radian)
