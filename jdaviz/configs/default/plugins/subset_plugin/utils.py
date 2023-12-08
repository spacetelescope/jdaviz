"""
Utility functions for subset plugin these don't belong in
glue.core.region_translators, as they deal with conversions that
only happen within this plugin (e.g between region/'subset defintion')
"""

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from regions import CircleAnnulusSkyRegion, CircleSkyRegion, EllipseSkyRegion, RectangleSkyRegion

from jdaviz.core.region_translators import regions2roi

__all__ = []


def _subset_def_to_region(subset_type, sub, val='value', name='name'):
    """Subset definitions are carried through the plugin in a list of dictionaries,
    one entry for each ROI attribute of that subset along with its value,
    its previous value, and the name to display for that attribute in the UI.
    (see _unpack_get_subsets_for_ui for how these are constructed).

    This function takes one of those dictionary lists describing a subset,
    and converts it to a Regions object.

    Parameters
    ----------
    subset_type : str
        Name of ROI class (CircularROI/TrueCircularROI, EllipticalROI,
        CircularAnnulusROI, or RectangularROI)
    sub : list of dict
        List of dictionaries defining the subset, with one dict for each
        subset attribute (see _unpack_get_subsets_for_ui for how these
        are defined)
    val : str
        Key to get subset attribute (e.g radius, xc, yc) value. Will
        normally be 'value' or 'orig' within plugin to get the new and
        previous values of the attribute, respectivley.
    name : str
        Key to get subset attribute name. Will normally be 'name'.

    Returns
    -------
    reg : `SkyRegion` or `PixelRegion`
        A SkyRegion or PixelRegion object (depending on what
        `region_type` is) of the subset that the dictionary `sub`
        represents.
    """

    if "CircularROI" in subset_type:  # TrueCircular or Circular
        reg = CircleSkyRegion(center=SkyCoord(*[x[val] for x in sub if 'Center' in x[name]]*u.deg),
                              radius=[x[val] for x in sub if 'Radius' in x[name]][0]*u.deg)
    elif subset_type == "EllipticalROI":
        rads = [x[val] for x in sub if 'Radius' in x[name]]
        reg = EllipseSkyRegion(SkyCoord(*[x[val] for x in sub if 'Center' in x[name]]*u.deg),
                               width=2.*rads[0]*u.deg,
                               height=2.*rads[1]*u.deg,
                               angle=[x[val] for x in sub if 'Angle' in x[name]][0]*u.deg)

    elif subset_type == "CircularAnnulusROI":
        rads = [x[val] for x in sub if 'Radius' in x['name']]
        reg = CircleAnnulusSkyRegion(SkyCoord(*[x[val] for x in sub if 'Center' in x[name]]*u.deg),
                                     inner_radius=rads[0]*u.deg,
                                     outer_radius=rads[1]*u.deg)

    elif subset_type == "RectangularROI":
        xmin, ymin = [x[val] for x in sub if 'min' in x[name]]
        xmax, ymax = [x[val] for x in sub if 'max' in x[name]]
        angle = [x[val] for x in sub if 'Angle' in x[name]][0]
        width = xmax - xmin
        height = ymax - ymin
        center = ((xmin+xmax) / 2, (ymin+ymax) / 2)
        reg = RectangleSkyRegion(center=SkyCoord(*center*u.deg),
                                 width=width*u.deg,
                                 height=height*u.deg,
                                 angle=angle*u.deg)

    else:  # pragma: no cover
        raise NotImplementedError(f"Failed to convert {subset_type} to region.")

    return reg


def _sky_region_to_subset_def(sky_region, _around_decimals=6):
    """Generates a 'subset_definition' list of dictionaries from a
    `regions.SkyRegion`object.

    Parameters
    ----------
    sky_region : `regions.SkyRegion`
        Name of ROI class (CircularROI/TrueCircularROI, EllipticalROI,
        CircularAnnulusROI, or RectangularROI).
    _around_decimals : int
        Rounding for 'theta', if present.

    Returns
    -------
    deff : list of dict
        List of dictionaries, each sub-dictionary describing a
        subset attribute.
    """

    if isinstance(sky_region, CircleSkyRegion):
        x = sky_region.center.ra.deg
        y = sky_region.center.dec.deg
        r = sky_region.radius.deg
        deff = [{"name": 'RA Center (degrees)', "att": "xc", "value": x, "orig": x},
                {"name": 'Dec Center (degrees)', "att": "yc", "value": y, "orig": y},
                {"name": 'Radius (degrees)', "att": "radius", "value": r, "orig": r}]

    elif isinstance(sky_region, EllipseSkyRegion):
        xc = sky_region.center.ra.deg
        yc = sky_region.center.dec.deg
        rx = sky_region.width.to_value(u.deg) * 0.5
        ry = sky_region.height.to_value(u.deg) * 0.5
        ang = sky_region.angle.to_value(u.deg)
        theta = np.around(ang, decimals=_around_decimals)
        deff = [{"name": "RA Center (degrees)", "att": "xc", "value": xc, "orig": xc},
                {"name": "Dec Center (degrees)", "att": "yc", "value": yc, "orig": yc},
                {"name": "RA Radius (degrees)", "att": "radius_x", "value": rx, "orig": rx},
                {"name": "Dec Radius (degrees)", "att": "radius_y", "value": ry, "orig": ry},
                {"name": "Angle", "att": "theta", "value": theta, "orig": theta}]

    elif isinstance(sky_region, CircleAnnulusSkyRegion):
        xc = sky_region.center.ra.deg
        yc = sky_region.center.dec.deg
        inner_r = sky_region.inner_radius.to_value(u.deg)
        outer_r = sky_region.outer_radius.to_value(u.deg)
        deff = [{"name": "RA Center (degrees)", "att": "xc", "value": xc, "orig": xc},
                {"name": "Dec Center (degrees)", "att": "yc", "value": yc, "orig": yc},
                {"name": "Inner Radius (degrees)", "att": "inner_radius",
                 "value": inner_r, "orig": inner_r},
                {"name": "Outer Radius (degrees)", "att": "outer_radius",
                 "value": outer_r, "orig": outer_r}]

    elif isinstance(sky_region, RectangleSkyRegion):
        deff = []
        dsky_ra = (sky_region.width).to_value(u.deg) * 0.5
        dsky_dec = (sky_region.height).to_value(u.deg) * 0.5
        mins_maxs = {'xmin': sky_region.center.ra.deg - dsky_ra,
                     'xmax': sky_region.center.ra.deg + dsky_ra,
                     'ymin': sky_region.center.dec.deg - dsky_dec,
                     'ymax': sky_region.center.dec.deg + dsky_dec}
        for att in ("Xmin", "Xmax", "Ymin", "Ymax"):
            val = mins_maxs[att.lower()]
            name = att.replace('X', 'RA ').replace('Y', 'Dec ')
            deff.append({"name": f"{name} (degrees)", "att": att.lower(),
                         "value": val, "orig": val})
        theta = sky_region.angle.to_value(u.deg)
        deff.append({"name": "Angle", "att": "theta", "value": theta, "orig": theta})

    else:  # pragma: no cover
        raise NotImplementedError(f"Failed to convert {sky_region} to subset definition.")

    return deff


def _get_pixregion_params_in_dict(region):
    """Given a Region, returns a dictionary with the attribute names
    of the corresponding ROI type (i.e., CirclePixelRegion and CircularROI).

    This makes use of `jdaviz.core.region_translators.regions2roi`, but instead
    of returning an ROI object it returns a dictionary of parameters that
    would be used to create that same ROI object. This involves changing some
    keys and deleting some, which is why that `regions2roi` can't be
    called directly.
    """

    roi = regions2roi(region)
    region_dict = roi.__dict__.copy()

    if 'center' in region_dict.keys():
        region_dict['xc'] = region_dict['center'].x
        region_dict['yc'] = region_dict['center'].y
        del region_dict['center']

    region_dict.pop('meta', None)
    region_dict.pop('visual', None)

    return region_dict
