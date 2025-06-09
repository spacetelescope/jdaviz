import os
import asdf

import numpy as np
from astropy.io import fits
from glue.core.data import Component, Data


from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection

from jdaviz.utils import (
    standardize_metadata, standardize_roman_metadata,
    PRIHDR_KEY, _wcs_only_label, download_uri_to_path, get_cloud_fits
)

try:
    from roman_datamodels import datamodels as rdd
except ImportError:
    HAS_ROMAN_DATAMODELS = False
else:
    HAS_ROMAN_DATAMODELS = True


__all__ = ['ImageImporter']


@loader_importer_registry('Image')
class ImageImporter(BaseImporterToDataCollection):
    template_file = __file__, "../to_dc_with_label.vue"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.app.config == 'imviz':
            self.data_label_default = 'Image'

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'imviz', 'cubeviz'):
            # cubeviz allowed for cubeviz.specviz.load_data support
            # NOTE: temporary during deconfig process
            return False
        # return isinstance(self.input, Spectrum1D) and self.input.flux.ndim == 1
        return True

    @property
    def default_viewer_reference(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'imviz-0'

    @property
    def output(self):
        file_obj = self.input
        data_label = self.app.return_data_label(file_obj, alt_name="image_data")

        data = Data(label=data_label)

        ext = 'sci'
        parent = None
        cache = None
        local_path = None
        timeout = None
        print(type(file_obj))
        if isinstance(file_obj, str):
            with fits.open(file_obj) as pf:
                available_extensions = [hdu.name for hdu in pf]
                print(pf[0], dir(pf[0]))
                if ext == 'data':
                    ext = 'sci'
                hdu = file_obj[ext]

                hdulist = pf[0]
                if hdulist is not None and hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
                    data.meta[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)
                data.meta.update(standardize_metadata(hdu.header))

        return hdulist
