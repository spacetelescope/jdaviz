from astropy.io import fits
from spectral_cube import SpectralCube
from spectral_cube.io.fits import FITSReadError
import logging
import numpy as np
import os
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
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    """
    file_name = os.path.basename(file_path)

    with fits.open(file_path) as hdulist:
        wcs = None

        for hdu in hdulist:
            data_label = f"{file_name}[{hdu.name}]"

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

            app.data_collection[data_label] = sc

            # If the data type is some kind of integer, assume it's the mask/dq
            if hdu.data.dtype in (np.int, np.uint, np.uint32) or \
                    any(x in hdu.name.lower() for x in EXT_TYPES['mask']):
                app.add_data_to_viewer('mask-viewer', data_label)

            if 'errtype' in [x.lower() for x in hdu.header.keys()] or \
                    any(x in hdu.name.lower() for x in EXT_TYPES['uncert']):
                app.add_data_to_viewer('uncert-viewer', data_label)

            if any(x in hdu.name.lower() for x in EXT_TYPES['flux']):
                app.add_data_to_viewer('flux-viewer', data_label)
                app.add_data_to_viewer('spectrum-viewer', data_label)
