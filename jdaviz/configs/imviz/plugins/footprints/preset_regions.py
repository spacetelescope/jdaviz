# adapted from https://github.com/spacetelescope/jwst_novt/blob/main/jwst_novt/footprints.py

import numpy as np
import regions
from astropy import coordinates

try:
    import pysiaf
except ImportError:
    _has_pysiaf = False
else:
    _has_pysiaf = True

__all__ = [
    "_has_pysiaf",
    "_instruments",
    "_full_apertures",
    "_all_apertures",
    "jwst_footprint"
]

_instruments = {'NIRSpec': 'NIRSpec',
                'NIRCam:short': 'NIRCam',
                'NIRCam:long': 'NIRCam',
                'NIRISS': 'NIRISS',
                'MIRI': 'MIRI',
                'FGS': 'FGS'
                }

_full_apertures = {'NIRSpec': 'NRS_FULL_MSA',
                   'NIRCam:short': 'NRCALL_FULL',
                   'NIRCam:long': 'NRCALL_FULL',
                   'NIRISS': 'NIS_AMIFULL',
                   'MIRI': 'MIRIM_FULL',
                   'FGS': 'FGS1_FULL'
                   }

_all_apertures = {'NIRSpec': ["NRS_FULL_MSA1",
                              "NRS_FULL_MSA2",
                              "NRS_FULL_MSA3",
                              "NRS_FULL_MSA4",
                              "NRS_FULL_IFU",
                              "NRS_S200A1_SLIT",
                              "NRS_S200A2_SLIT",
                              "NRS_S400A1_SLIT",
                              "NRS_S1600A1_SLIT",
                              "NRS_S200B1_SLIT"],
                  'NIRCam:short': ["NRCA1_FULL",
                                   "NRCA2_FULL",
                                   "NRCA3_FULL",
                                   "NRCA4_FULL",
                                   "NRCB1_FULL",
                                   "NRCB2_FULL",
                                   "NRCB3_FULL",
                                   "NRCB4_FULL"],
                  'NIRCam:long': ["NRCA5_FULL", "NRCB5_FULL"],
                  'NIRISS': ['NIS_AMIFULL'],
                  'MIRI': ['MIRIM_FULL'],
                  'FGS': ['FGS1_FULL', 'FGS2_FULL']
                  }


def jwst_footprint(instrument, ra, dec, pa, v2_offset=0.0, v3_offset=0.0, apertures=None):
    """
    Create footprint regions in sky coordinates from a jwst instrument.

    Parameters
    ----------
    instrument : string
        Instrument, one of 'nirspec', 'nircam:short', 'nircam:long'.
    ra : float
        RA of NIRCam center, in degrees.
    dec : float
        Dec of NIRCam center, in degrees.
    pa : float
        Position angle, in degrees measured from North
        to central vertical axis in North to East direction.
    v2_offset : float, optional
        Additional V2 offset in telescope coordinates to apply to instrument
        center, as from a dither pattern.
    v3_offset : float, optional
        Additional V3 offset in telescope coordinates to apply to instrument
        center, as from a dither pattern.
    apertures : list of str, optional
        If set, only the specified apertures are returned.

    Returns
    -------
    footprint : regions.Regions
        Footprint regions as Polygon regions in sky coordinates.
    """
    if not _has_pysiaf:
        raise ImportError('jwst_footprint requires pysiaf to be installed')

    if instrument not in _instruments:  # pragma: no cover
        raise ValueError(f"instrument must be one of {', '.join(_instruments.keys())}")

    siaf_interface = pysiaf.Siaf(_instruments.get(instrument))

    # Get center and PA offset from full aperture
    full = siaf_interface.apertures[_full_apertures.get(instrument)]
    corners = full.corners("tel", rederive=False)
    v2 = np.mean(corners[0]) - v2_offset
    v3 = np.mean(corners[1]) + v3_offset
    pa_offset = full.V3IdlYAngle

    # Attitude matrix for sky coordinates
    attmat = pysiaf.utils.rotations.attitude(v2, v3, ra, dec, pa - pa_offset)

    if apertures is None:
        apertures = _all_apertures.get(instrument)

    # Aperture regions
    ap_regions = []
    for aperture_name in apertures:
        aperture = siaf_interface.apertures[aperture_name]
        aperture.set_attitude_matrix(attmat)
        poly_points = aperture.closed_polygon_points("sky")

        sky_coord = coordinates.SkyCoord(*poly_points, unit="deg")
        reg = regions.PolygonSkyRegion(sky_coord)
        ap_regions.append(reg)

    return regions.Regions(ap_regions)
