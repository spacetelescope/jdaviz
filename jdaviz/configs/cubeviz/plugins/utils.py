from astropy.io import fits
from spectral_cube import SpectralCube
from spectral_cube.io.fits import FITSReadError
import logging
import numpy as np
from jdaviz.core.registries import data_parser_registry

EXT_TYPES = dict(flux=['flux', 'sci'],
                 uncert=['ivar', 'err', 'var', 'uncert'],
                 mask=['mask', 'dq'])


@data_parser_registry("cubeviz-data-parser")
def parse_data(file_path, app):
    """
    Attempts to parse a data file and auto-populate available viewers in
    cubeviz.

    Parameters
    ----------
    file_path : str
        The path to a cube-like data file.
    data_collection : `~glue.core.DataCollection`
        The application-level data collection into which the parsed data will
        be placed.

    Returns
    -------
    ext_mapping : dict
        A mapping of the three necessary components of the cubeviz viewers to
        the data component labels in glue.
    """
    ext_mapping = {'flux': None,
                   'uncert': None,
                   'mask': None}

    with fits.open(file_path) as hdulist:
        wcs = None

        for hdu in hdulist:
            if hdu.data is None:
                continue

            # This will fail on attempting to load anything that
            # isn't cube-shaped
            try:
                sc = SpectralCube.read(hdu)
                wcs = sc.wcs
            except ValueError:
                # This will fail if the parsing of the wcs does not provide
                # proper celestial axes
                try:
                    hdu.header.update(wcs.to_header())
                    sc = SpectralCube.read(hdu)
                except ValueError as e:
                    logging.error(e)
                    continue
            except FITSReadError as e:
                logging.error(e)
                continue

            app.data_collection[hdu.name] = sc

            # If the data type is some kind of integer, assume it's the mask/dq
            if hdu.data.dtype in (np.int, np.uint, np.uint32) or \
                    any(x in hdu.name.lower() for x in EXT_TYPES['mask']):
                ext_mapping['mask'] = hdu.name
                app.add_data_to_viewer('mask-viewer', hdu.name)

            if 'errtype' in [x.lower() for x in hdu.header.keys()] or \
                    any(x in hdu.name.lower() for x in EXT_TYPES['uncert']):
                ext_mapping['uncert'] = hdu.name
                app.add_data_to_viewer('uncert-viewer', hdu.name)

            if any(x in hdu.name.lower() for x in EXT_TYPES['flux']):
                ext_mapping['flux'] = hdu.name
                app.add_data_to_viewer('flux-viewer', hdu.name)
                app.add_data_to_viewer('spectrum-viewer', hdu.name)

    return ext_mapping
