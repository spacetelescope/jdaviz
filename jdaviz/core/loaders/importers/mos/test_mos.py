import numpy as np
from astropy.io import fits

from jdaviz.core.loaders.importers.mos.mos import MOSImporter


def test_mos_importer_is_valid(deconfigged_helper, tmp_path):
    deconfigged_helper._app.state.dev_mos_loader = True
    resolver = deconfigged_helper.loaders['object']._obj
    valid_dir = tmp_path / 'valid'
    valid_dir.mkdir()

    importer = MOSImporter(app=deconfigged_helper._app,
                           resolver=resolver,
                           parser=None,
                           input=valid_dir)

    assert (importer._check_is_valid() ==
            'Input directory does not contain any MOS 1D spectra matching *_x1d.fits.')

    nested_dir = valid_dir / 'JWST' / 'product'
    nested_dir.mkdir(parents=True)
    fits.PrimaryHDU(np.arange(10.)).writeto(nested_dir / 'jw00001_x1d.fits')
    importer._input = valid_dir
    assert importer._check_is_valid() == ''

    importer._input = nested_dir / 'jw00001_x1d.fits'
    assert importer._check_is_valid() == 'MOS importer input must be a directory.'

    importer._input = tmp_path / 'empty'
    importer._input.mkdir()
    assert (importer._check_is_valid() ==
            'Input directory does not contain any MOS 1D spectra matching *_x1d.fits.')

    (importer._input / 'MANIFEST.HTML').touch()
    assert (importer._check_is_valid() ==
            'Input directory does not contain any MOS 1D spectra matching *_x1d.fits.')

    hidden_dir = tmp_path / 'hidden'
    hidden_dir.mkdir()
    (hidden_dir / '.jw00004_x1d.fits').touch()
    importer._input = hidden_dir
    assert (importer._check_is_valid() ==
            'Input directory does not contain any MOS 1D spectra matching *_x1d.fits.')

    unsupported_file_dir = tmp_path / 'unsupported_file'
    unsupported_file_dir.mkdir()
    (unsupported_file_dir / 'jw00005_x1d.fits').touch()
    (unsupported_file_dir / 'notes.txt').touch()
    importer._input = unsupported_file_dir
    assert importer._check_is_valid() == 'Input directory contains unsupported MOS file: notes.txt'

    spectrum_2d_and_image_dir = tmp_path / 'spectrum_2d_and_image'
    spectrum_2d_and_image_dir.mkdir()
    (spectrum_2d_and_image_dir / 'jw00006_s2d.fits').touch()
    (spectrum_2d_and_image_dir / 'jw00006_i2d.fits').touch()
    importer._input = spectrum_2d_and_image_dir
    assert (importer._check_is_valid() ==
            'Input directory does not contain any MOS 1D spectra matching *_x1d.fits.')
