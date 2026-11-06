import pytest
import numpy as np
import astropy.units as u
from astropy.nddata import NDData, StdDevUncertainty
from astropy.io import fits
from specutils import Spectrum

from jdaviz.core.loaders.importers.image.image import ImageImporter
from jdaviz.configs.imviz.plugins.parsers import HAS_ROMAN_DATAMODELS


def test_image_importer_is_valid(deconfigged_helper):
    """Test _check_is_valid for ImageImporter: success and failure cases."""
    resolver = deconfigged_helper.loaders['object']._obj

    def _create_importer(input_data=None):
        return ImageImporter(app=deconfigged_helper._app,
                             resolver=resolver, parser=None,
                             input=input_data)

    # Success: plain 2D numpy array
    importer = _create_importer(input_data=np.ones((10, 10)))
    assert importer._check_is_valid() == ''

    # Failure: Spectrum object (subclasses NDData, which has spectral WCS path,
    # but fails the type check before that)
    spec = Spectrum(flux=np.ones(10) * u.Jy, spectral_axis=np.arange(10) * u.um)
    importer = _create_importer(input_data=np.ones((10, 10)))
    importer._input = spec
    assert importer._check_is_valid() == 'Input is not a supported image data type.'

    # Failure: HDUList with no valid image extensions
    # Can't hotswap with ._input, need to update the extensions attribute (this is
    # the case for several below as well)
    hdul = fits.HDUList([fits.PrimaryHDU(),
                         fits.ImageHDU(data=np.ones((10, 10)))])
    importer = _create_importer(input_data=hdul)
    importer.extension.items = []
    assert importer._check_is_valid() == 'No extensions available.'

    # Failure: 3D array with no extension choices
    importer = _create_importer(input_data=np.ones((3, 10, 10)))
    importer.input_has_extensions = False
    importer.extension.items = []
    assert importer._check_is_valid() == 'No extensions available for 3D array.'

    # Failure: NDData with spectral GWCS
    s = Spectrum(flux=np.ones((5, 10)) * u.Jy,
                 spectral_axis=np.arange(10) * u.um)
    nddata = NDData(data=np.ones((5, 10)),
                    mask=np.zeros((5, 10), dtype=bool),
                    uncertainty=StdDevUncertainty(np.ones((5, 10)) * 0.1),
                    wcs=s.wcs)
    importer = _create_importer(input_data=nddata)
    assert importer._check_is_valid() == 'Input has spectral WCS coordinates.'


def test_distinct_nddata_inputs_get_unique_default_labels(deconfigged_helper):
    y, x = np.mgrid[:50, :50]
    source = np.exp(-((x - 25)**2 + (y - 25)**2) / (2 * 4**2))

    image_jy = NDData(1 + 10 * source, unit=u.Jy)
    image_counts_per_sr = NDData(5 + 100 * source, unit=u.count / u.sr)

    loader = deconfigged_helper.loaders['object']
    loader.object = image_jy
    loader.format = 'Image'
    assert loader.importer.data_label.value == 'Image'
    loader.load()

    loader.object = image_counts_per_sr
    loader.format = 'Image'
    assert loader.importer.data_label.value == 'Image (1)'
    loader.load()

    labels = deconfigged_helper._app.data_collection.labels
    assert labels == ['Image[DATA]', 'Image (1)[DATA]']


@pytest.mark.skipif(not HAS_ROMAN_DATAMODELS, reason="roman_datamodels is not installed")
def test_roman_level_3(deconfigged_helper, roman_level_3_mosaic):
    resolver = deconfigged_helper.loaders['object']._obj

    def _create_importer(input_data=None):
        return ImageImporter(app=deconfigged_helper._app,
                             resolver=resolver, parser=None,
                             input=input_data)

    # check that the importer works on Roman L3s
    importer = _create_importer(input_data=roman_level_3_mosaic)
    assert importer._check_is_valid() == ''
