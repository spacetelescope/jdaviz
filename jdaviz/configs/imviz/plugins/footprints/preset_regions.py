# adapted from https://github.com/spacetelescope/jwst_novt/blob/main/jwst_novt/footprints.py

import numpy as np
import pysiaf
import regions
from astropy import coordinates

__all__ = [
    "nirspec_footprint",
    "nircam_short_footprint",
    "nircam_long_footprint",
    "nircam_dither_footprint",
]


# see JDox article, Table 1:
# https://jwst-docs.stsci.edu/jwst-near-infrared-spectrograph/
#    nirspec-operations/nirspec-mos-operations/
#    nirspec-mos-operations-pre-imaging-using-nircam
NIRCAM_DITHER_OFFSETS = {
    "NONE": [(0.0, 0.0)],
    "FULL3": [(-58.0, -23.5), (0.0, 0.0), (58.0, 23.5)],
    "FULL3TIGHT": [(-58.0, -7.5), (0.0, 0.0), (58.0, 7.5)],
    "FULL6": [
        (-72.0, -30.0),
        (-43.0, -18.0),
        (-14.0, -6.0),
        (15.0, 6.0),
        (44.0, 18.0),
        (73.0, 30.0),
    ],
    "8NIRSPEC": [
        (-24.6, -64.1),
        (-24.4, -89.0),
        (24.6, -88.8),
        (24.4, -63.9),
        (24.6, 64.1),
        (24.4, 89.0),
        (-24.6, 88.8),
        (-24.4, 63.9),
    ],
}
"""dict : Dither offset values by pattern name, in telescope coordinates.

V2 offsets are subtracted; V3 offsets are added.
"""


NO_MOSAIC = {"8NIRSPEC"}
"""set : Dither pattern values for which mosaic is not enabled."""


def nirspec_footprint(ra, dec, pa, *, include_center=True, apertures=None):
    """
    Create NIRSpec footprint regions in sky coordinates.

    The MSA center and PA offset angle are determined from the
    NRS_FULL_MSA aperture.  Apertures appearing in the footprint are,
    by default:

        - NRS_FULL_MSA1
        - NRS_FULL_MSA2
        - NRS_FULL_MSA3
        - NRS_FULL_MSA4
        - NRS_FULL_IFU
        - NRS_S200A1_SLIT
        - NRS_S200A2_SLIT
        - NRS_S400A1_SLIT
        - NRS_S1600A1_SLIT
        - NRS_S200B1_SLIT


    Parameters
    ----------
    ra : float
        RA of NIRSpec MSA center, in degrees.
    dec : float
        Dec of NIRSpec MSA center, in degrees.
    pa : float
        Position angle for NIRSpec, in degrees measured from North
        to central MSA vertical axis in North to East direction.
    include_center : bool, optional
        If set, the center is marked with a Point region. If not,
        only the apertures are included in the output.
    apertures : list of str, optional
        If set, only the specified apertures are returned.

    Returns
    -------
    footprint : regions.Regions
        NIRSpec footprint regions.  MSA center is marked with a Point
        region; all other apertures are marked with Polygon regions.
        Output regions are in sky coordinates.
    """
    if apertures is None:
        apertures = [
            "NRS_FULL_MSA1",
            "NRS_FULL_MSA2",
            "NRS_FULL_MSA3",
            "NRS_FULL_MSA4",
            "NRS_FULL_IFU",
            "NRS_S200A1_SLIT",
            "NRS_S200A2_SLIT",
            "NRS_S400A1_SLIT",
            "NRS_S1600A1_SLIT",
            "NRS_S200B1_SLIT",
        ]

    # Siaf interface for NIRSpec
    nirspec = pysiaf.Siaf("NIRSpec")

    # Get center and PA offset from MSA full aperture
    msa_full = nirspec.apertures["NRS_FULL_MSA"]
    msa_corners = msa_full.corners("tel")
    msa_v2 = np.mean(msa_corners[0])
    msa_v3 = np.mean(msa_corners[1])
    pa_offset = msa_full.V3IdlYAngle

    # Attitude matrix for sky coordinates
    attmat = pysiaf.utils.rotations.attitude(msa_v2, msa_v3, ra, dec, pa - pa_offset)

    # Aperture regions
    nrs_regions = []
    if include_center:
        nrs_regions.append(
            regions.PointSkyRegion(coordinates.SkyCoord(ra, dec, unit="deg"))
        )
    for aperture_name in apertures:
        aperture = nirspec.apertures[aperture_name]
        aperture.set_attitude_matrix(attmat)
        poly_points = aperture.closed_polygon_points("sky")

        sky_coord = coordinates.SkyCoord(*poly_points, unit="deg")
        reg = regions.PolygonSkyRegion(sky_coord)
        nrs_regions.append(reg)

    return regions.Regions(nrs_regions)


def nircam_short_footprint(
    ra, dec, pa, *, v2_offset=0.0, v3_offset=0.0, include_center=True, apertures=None
):
    """
    Create NIRCam short channel footprint regions in sky coordinates.

    The NIRCam center and PA offset angle are determined from the
    NRCALL_FULL aperture.  Apertures appearing in the footprint are,
    by default:

        - NRCA1_FULL
        - NRCA2_FULL
        - NRCA3_FULL
        - NRCA4_FULL
        - NRCB1_FULL
        - NRCB2_FULL
        - NRCB3_FULL
        - NRCB4_FULL

    Parameters
    ----------
    ra : float
        RA of NIRCam center, in degrees.
    dec : float
        Dec of NIRCam center, in degrees.
    pa : float
        Position angle for NIRCam, in degrees measured from North
        to central vertical axis in North to East direction.
    v2_offset : float, optional
        Additional V2 offset in telescope coordinates to apply to instrument
        center, as from a dither pattern.
    v3_offset : float, optional
        Additional V3 offset in telescope coordinates to apply to instrument
        center, as from a dither pattern.
    include_center : bool, optional
        If set, the center is marked with a Point region. If not,
        only the apertures are included in the output.
    apertures : list of str, optional
        If set, only the specified apertures are returned.

    Returns
    -------
    footprint : regions.Regions
        NIRCam footprint regions.  NIRCam center is marked with a Point
        region; all other apertures are marked with Polygon regions.
        Output regions are in sky coordinates.
    """
    if apertures is None:
        apertures = [
            "NRCA1_FULL",
            "NRCA2_FULL",
            "NRCA3_FULL",
            "NRCA4_FULL",
            "NRCB1_FULL",
            "NRCB2_FULL",
            "NRCB3_FULL",
            "NRCB4_FULL",
        ]

    # Siaf interface for NIRCam
    nircam = pysiaf.Siaf("NIRCam")

    # Get center and PA offset from full aperture
    nrc_full = nircam.apertures["NRCALL_FULL"]
    nrc_corners = nrc_full.corners("tel", rederive=False)
    nrc_v2 = np.mean(nrc_corners[0]) - v2_offset
    nrc_v3 = np.mean(nrc_corners[1]) + v3_offset
    pa_offset = nrc_full.V3IdlYAngle

    # Attitude matrix for sky coordinates
    attmat = pysiaf.utils.rotations.attitude(nrc_v2, nrc_v3, ra, dec, pa - pa_offset)

    # Aperture regions
    nrc_regions = []
    if include_center:
        nrc_regions.append(
            regions.PointSkyRegion(coordinates.SkyCoord(ra, dec, unit="deg"))
        )

    for aperture_name in apertures:
        aperture = nircam.apertures[aperture_name]
        aperture.set_attitude_matrix(attmat)
        poly_points = aperture.closed_polygon_points("sky")

        sky_coord = coordinates.SkyCoord(*poly_points, unit="deg")
        reg = regions.PolygonSkyRegion(sky_coord)
        nrc_regions.append(reg)

    return regions.Regions(nrc_regions)


def nircam_long_footprint(
    ra, dec, pa, *, v2_offset=0.0, v3_offset=0.0, include_center=True, apertures=None
):
    """
    Create NIRCam long channel footprint regions in sky coordinates.

    The NIRCam center and PA offset angle are determined from the
    NRCALL_FULL aperture.  Apertures appearing in the footprint are:

        - NRCA5_FULL
        - NRCB5_FULL

    Parameters
    ----------
    ra : float
        RA of NIRCam center, in degrees.
    dec : float
        Dec of NIRCam center, in degrees.
    pa : float
        Position angle for NIRCam, in degrees measured from North
        to central vertical axis in North to East direction.
    v2_offset : float, optional
        Additional V2 offset in telescope coordinates to apply to instrument
        center, as from a dither pattern.
    v3_offset : float, optional
        Additional V3 offset in telescope coordinates to apply to instrument
        center, as from a dither pattern.
    include_center : bool, optional
        If set, the center is marked with a Point region. If not,
        only the apertures are included in the output.
    apertures : list of str, optional
        If set, only the specified apertures are returned.

    Returns
    -------
    footprint : regions.Regions
        NIRCam footprint regions.  NIRCam center is marked with a Point
        region; all other apertures are marked with Polygon regions.
        Output regions are in sky coordinates.
    """
    if apertures is None:
        apertures = ["NRCA5_FULL", "NRCB5_FULL"]

    # Siaf interface for NIRCam
    nircam = pysiaf.Siaf("NIRCam")

    # Get center and PA offset from full aperture
    nrc_full = nircam.apertures["NRCALL_FULL"]
    nrc_corners = nrc_full.corners("tel", rederive=False)
    nrc_v2 = np.mean(nrc_corners[0]) - v2_offset
    nrc_v3 = np.mean(nrc_corners[1]) + v3_offset
    pa_offset = nrc_full.V3IdlYAngle

    # Attitude matrix for sky coordinates
    attmat = pysiaf.utils.rotations.attitude(nrc_v2, nrc_v3, ra, dec, pa - pa_offset)

    # Aperture regions
    nrc_regions = []
    if include_center:
        nrc_regions.append(
            regions.PointSkyRegion(coordinates.SkyCoord(ra, dec, unit="deg"))
        )
    for aperture_name in apertures:
        aperture = nircam.apertures[aperture_name]
        aperture.set_attitude_matrix(attmat)
        poly_points = aperture.closed_polygon_points("sky")

        sky_coord = coordinates.SkyCoord(*poly_points, unit="deg")
        reg = regions.PolygonSkyRegion(sky_coord)
        nrc_regions.append(reg)

    return regions.Regions(nrc_regions)


def nircam_dither_footprint(
    ra,
    dec,
    pa,
    *,
    dither_pattern="NONE",
    channel="long",
    add_mosaic=False,
    mosaic_offset=None,
    include_center=True,
    apertures=None,
):
    """
    Dither and/or mosaic the NIRCam aperture footprint.

    Parameters
    ----------
    ra : float
        RA of NIRCam center, in degrees.
    dec : float
        Dec of NIRCam center, in degrees.
    pa : float
        Position angle for NIRCam, in degrees measured from North
        to central vertical axis in North to East direction.
    dither_pattern : str, optional
        Name of the dither pattern to apply.  Options are: NONE, FULL3,
        FULL3TIGHT, FULL6, 8NIRSPEC.
    channel : {'short', 'long'}, optional
        The NIRCam channel to generate aperture footprints for.
    add_mosaic : bool, optional
        If False, mosaic offsets are ignored. Otherwise, a two-tile
        mosaic is computed with window width specified in `mosaic_offset`.
    mosaic_offset : tuple or list, optional
        (V2, V3) offset in telescope coordinates to apply as a two-tile
        mosaic offset.  The offset is specified as a window width around
        the pointing center: the mosaic position will be at the center +/-
        offset / 2. Ignored if `dither_pattern` is 8NIRSPEC or `instrument`
        is NIRSpec or `add_mosaic` is not set.
    include_center : bool, optional
        If set, the center is marked with a Point region. If not,
        only the apertures are included in the output.
    apertures : list of str, optional
        If set, only the specified apertures are returned.

    Returns
    -------
    footprint : regions.Regions
        NIRCam footprint regions.  NIRCam center is marked with a Point
        region; all other apertures are marked with Polygon regions.
        Output regions are in sky coordinates.
    """
    pattern = dither_pattern.strip().upper()
    if pattern not in NIRCAM_DITHER_OFFSETS:
        msg = (
            f"Dither pattern {dither_pattern} not recognized. "
            f"Options are: {list(NIRCAM_DITHER_OFFSETS.keys())}."
        )
        raise ValueError(msg)
    dither_offsets = NIRCAM_DITHER_OFFSETS[pattern]

    if channel.strip().lower() == "short":
        footprint_func = nircam_short_footprint
    else:
        footprint_func = nircam_long_footprint

    if pattern in NO_MOSAIC:
        add_mosaic = False
    if mosaic_offset is None:
        mosaic_offset = (0.0, 0.0)

    # note: if offsets are 0 but add_mosaic is set, two
    # footprint tiles are still created
    if add_mosaic:
        center_offset = [
            (mosaic_offset[0] / 2, -mosaic_offset[1] / 2),
            (-mosaic_offset[0] / 2, mosaic_offset[1] / 2),
        ]
    else:
        center_offset = [(0, 0)]

    dithers = []
    for mosaic_position in center_offset:
        for offset in dither_offsets:
            v2 = offset[0] + mosaic_position[0]
            v3 = offset[1] + mosaic_position[1]
            reg_list = footprint_func(
                ra,
                dec,
                pa,
                v2_offset=v2,
                v3_offset=v3,
                include_center=include_center,
                apertures=apertures,
            )
            # include center only once
            include_center = False

            for reg in reg_list:
                dithers.append(reg)

    return regions.Regions(dithers)
