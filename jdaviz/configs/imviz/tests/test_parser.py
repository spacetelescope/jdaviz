import numpy as np
import pytest
from astropy import units as u
from astropy.io import fits
from astropy.nddata import NDData, StdDevUncertainty
from astropy.utils.data import download_file
from astropy.wcs import WCS

from jdaviz.configs.imviz.helper import split_filename_with_fits_ext
from jdaviz.configs.imviz.plugins.parsers import (
    HAS_JWST_ASDF, parse_data, _validate_fits_image2d, _validate_bunit,
    _parse_image)

try:
    import skimage  # noqa
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False


@pytest.mark.parametrize(
    ('filename', 'ans'),
    [('/path/to/cache/contents', ['/path/to/cache/contents', None, 'contents']),
     ('file://path/image.fits[SCI]', ['file://path/image.fits', 'SCI', 'image']),
     ('image.fits[dq,2]', ['image.fits', ('dq', 2), 'image']),
     ('/path/to/image.fits', ['/path/to/image.fits', None, 'image']),
     ('/path/to/image.fits[*]', ['/path/to/image.fits', '*', 'image']),
     ('../image.fits.gz[1]', ['../image.fits.gz', 1, 'image.fits'])])
def test_filename_split(filename, ans):
    filepath, ext, data_label = split_filename_with_fits_ext(filename)
    assert filepath == ans[0]
    if ans[1] is None:
        assert ext is None
    else:
        assert ext == ans[1]
    assert data_label == ans[2]


def test_validate_fits_image2d():
    # Not 2D image
    hdu = fits.ImageHDU([0, 0])
    assert not _validate_fits_image2d(hdu, raise_error=False)
    with pytest.raises(ValueError, match='Imviz cannot load this HDU'):
        _validate_fits_image2d(hdu)

    # 2D Image
    hdu = fits.ImageHDU([[0, 0], [0, 0]])
    assert _validate_fits_image2d(hdu)


def test_validate_bunit():
    with pytest.raises(ValueError):
        _validate_bunit('NOT_A_UNIT')

    assert not _validate_bunit('Mjy-sr', raise_error=False)  # Close but not quite
    assert _validate_bunit('MJy/sr')


class TestParseImage:
    def setup_class(self):
        self.jwst_asdf_url_1 = 'https://data.science.stsci.edu/redirect/JWST/jwst-data_analysis_tools/stellar_photometry/jw01072001001_01101_00001_nrcb1_cal.fits'  # noqa: E501

    def test_no_data_label(self):
        with pytest.raises(NotImplementedError, match='should be set'):
            _parse_image(None, None, None, False)

    def test_hdulist_no_image(self, imviz_app):
        hdulist = fits.HDUList([fits.PrimaryHDU()])
        with pytest.raises(ValueError, match='does not have any FITS image'):
            parse_data(imviz_app.app, hdulist, show_in_viewer=False)

    @pytest.mark.parametrize('some_obj', (WCS(), [[1, 2], [3, 4]]))
    def test_invalid_file_obj(self, imviz_app, some_obj):
        with pytest.raises(NotImplementedError, match='Imviz does not support'):
            parse_data(imviz_app.app, some_obj, show_in_viewer=False)

    def test_parse_numpy_array(self, imviz_app):
        with pytest.raises(ValueError, match='Imviz cannot load this array with ndim=1'):
            parse_data(imviz_app.app, np.zeros(2), show_in_viewer=False)

        parse_data(imviz_app.app, np.zeros((2, 2)), data_label='some_array',
                   show_in_viewer=False)
        data = imviz_app.app.data_collection[0]
        comp = data.get_component('DATA')
        assert data.label == 'some_array'
        assert data.shape == (2, 2)
        assert comp.data.shape == (2, 2)

    def test_parse_nddata_simple(self, imviz_app):
        with pytest.raises(ValueError, match='Imviz cannot load this NDData with ndim=1'):
            parse_data(imviz_app.app, NDData([1, 2, 3, 4]), show_in_viewer=False)

        ndd = NDData([[1, 2], [3, 4]])
        parse_data(imviz_app.app, ndd, data_label='some_data', show_in_viewer=False)
        data = imviz_app.app.data_collection[0]
        comp = data.get_component('DATA')
        assert data.label == 'some_data[DATA]'
        assert data.shape == (2, 2)
        assert comp.data.shape == (2, 2)
        assert len(imviz_app.app.data_collection) == 1

    @pytest.mark.parametrize(
        ('ndd', 'attributes'),
        [(NDData([[1, 2], [3, 4]], mask=[[True, False], [False, False]]),
          ['DATA', 'MASK']),
         (NDData([[1, 2], [3, 4]], uncertainty=StdDevUncertainty([[0.1, 0.2], [0.3, 0.4]])),
          ['DATA', 'UNCERTAINTY'])])
    def test_parse_nddata_with_one_only(self, imviz_app, ndd, attributes):
        parse_data(imviz_app.app, ndd, data_label='some_data', show_in_viewer=False)
        for i, attrib in enumerate(attributes):
            data = imviz_app.app.data_collection[i]
            comp = data.get_component(attrib)
            assert data.label == f'some_data[{attrib}]'
            assert data.shape == (2, 2)
            assert comp.data.shape == (2, 2)
        assert len(imviz_app.app.data_collection) == 2

    def test_parse_nddata_with_everything(self, imviz_app):
        ndd = NDData([[1, 2], [3, 4]], mask=[[True, False], [False, False]],
                     uncertainty=StdDevUncertainty([[0.1, 0.2], [0.3, 0.4]]),
                     unit=u.MJy/u.sr, wcs=WCS(naxis=2))
        parse_data(imviz_app.app, ndd, data_label='some_data', show_in_viewer=False)
        for i, attrib in enumerate(['DATA', 'MASK', 'UNCERTAINTY']):
            data = imviz_app.app.data_collection[i]
            comp = data.get_component(attrib)
            assert data.label == f'some_data[{attrib}]'
            assert data.shape == (2, 2)
            assert isinstance(data.coords, WCS)
            assert comp.data.shape == (2, 2)
            if attrib == 'MASK':
                assert comp.units == ''
            else:
                assert comp.units == 'MJy / sr'
        assert len(imviz_app.app.data_collection) == 3

    @pytest.mark.skipif(not HAS_SKIMAGE, reason='scikit-image is missing')
    @pytest.mark.parametrize('format', ('jpg', 'png'))
    def test_parse_rgba(self, imviz_app, tmp_path, format):
        from skimage.io import imsave

        if format == 'png':  # Cross-test PNG with RGBA
            a = np.zeros((10, 10, 4), dtype='uint8')
        else:  # Cross-test JPG with RGB only
            a = np.zeros((10, 10, 3), dtype='uint8')

        filename = str(tmp_path / f'myimage.{format}')
        imsave(filename, a)

        parse_data(imviz_app.app, filename, show_in_viewer=False)
        data = imviz_app.app.data_collection[0]
        assert data.label == 'myimage'
        assert data.shape == (10, 10)

    def test_filelist(self, imviz_app, tmp_path):
        flist = []

        # Generate some files to parse.
        for i in range(2):
            fpath = tmp_path / f'myfits_{i}.fits'
            flist.append(str(fpath))
            hdu = fits.PrimaryHDU(np.zeros((2, 2)) + i)
            hdu.writeto(fpath, overwrite=True)

        flist = ','.join(flist)
        imviz_app.load_data(flist, show_in_viewer=False)

        for i in range(2):
            data = imviz_app.app.data_collection[i]
            comp = data.get_component('PRIMARY,1')
            assert data.label == f'myfits_{i}[PRIMARY,1]'
            assert data.shape == (2, 2)
            np.testing.assert_allclose(comp.data.mean(), i)

        with pytest.raises(ValueError, match='Do not manually overwrite data_label'):
            imviz_app.load_data(flist, data_label='foo', show_in_viewer=False)

    @pytest.mark.skipif(HAS_JWST_ASDF, reason='jwst is installed')
    @pytest.mark.remote_data
    def test_parse_jwst_nircam_level2_no_jwst(self, imviz_app):
        filename = download_file(self.jwst_asdf_url_1, cache=True)
        with pytest.raises(ImportError, match='jwst package is missing'):
            parse_data(imviz_app.app, filename, data_label='foo',
                       show_in_viewer=False)

    @pytest.mark.skipif(not HAS_JWST_ASDF, reason='jwst not installed')
    @pytest.mark.remote_data
    def test_parse_jwst_nircam_level2(self, imviz_app):
        from gwcs import WCS as GWCS

        filename = download_file(self.jwst_asdf_url_1, cache=True)

        # Default behavior: Science image
        parse_data(imviz_app.app, filename, show_in_viewer=False)
        data = imviz_app.app.data_collection[0]
        comp = data.get_component('DATA')
        assert data.label == 'contents[DATA]'  # download_file returns cache loc
        assert data.shape == (2048, 2048)
        assert isinstance(data.coords, GWCS)
        assert comp.units == 'MJy/sr'
        assert comp.data.shape == (2048, 2048)

        # Request specific extension (name + ver, but ver is not used), use given label
        parse_data(imviz_app.app, filename, ext=('DQ', 42),
                   data_label='jw01072001001_01101_00001_nrcb1_cal',
                   show_in_viewer=False)
        data = imviz_app.app.data_collection[1]
        comp = data.get_component('DQ')
        assert data.label == 'jw01072001001_01101_00001_nrcb1_cal[DQ]'
        assert comp.units == ''

        # Pass in HDUList directly + ext (name only), use given label
        with fits.open(filename) as pf:
            parse_data(imviz_app.app, pf, ext='SCI',
                       data_label='jw01072001001_01101_00001_nrcb1_cal',
                       show_in_viewer=False)
            data = imviz_app.app.data_collection[2]
            comp = data.get_component('DATA')  # SCI = DATA
            assert data.label == 'jw01072001001_01101_00001_nrcb1_cal[DATA]'
            assert isinstance(data.coords, GWCS)
            assert comp.units == 'MJy/sr'

            # Test duplicate label functionality
            imviz_app.app.data_collection.clear()
            parse_data(imviz_app.app, pf, ext='SCI', show_in_viewer=False, data_label='TEST')
            data = imviz_app.app.data_collection[0]
            assert data.label.endswith('[DATA]')

            parse_data(imviz_app.app, pf, ext='SCI', show_in_viewer=False, data_label='TEST')
            data = imviz_app.app.data_collection[1]
            assert data.label.endswith('[DATA]_2')

            # Load all extensions
            imviz_app.app.data_collection.clear()
            parse_data(imviz_app.app, pf, ext='*', show_in_viewer=False)
            data = imviz_app.app.data_collection
            assert len(data.labels) == 7
            assert data.labels[0].endswith('[DATA]')
            assert data.labels[1].endswith('[ERR]')
            assert data.labels[2].endswith('[DQ]')
            assert data.labels[3].endswith('[AREA]')
            assert data.labels[4].endswith('[VAR_POISSON]')
            assert data.labels[5].endswith('[VAR_RNOISE]')
            assert data.labels[6].endswith('[VAR_FLAT]')

        # Invalid ASDF attribute (extension)
        with pytest.raises(AttributeError, match='No attribute'):
            parse_data(imviz_app.app, filename, ext='DOES_NOT_EXIST',
                       data_label='foo', show_in_viewer=False)

    @pytest.mark.remote_data
    def test_parse_hst_drz(self, imviz_app):
        url = 'https://mast.stsci.edu/api/v0.1/Download/file?bundle_name=MAST_2021-04-21T1828.sh&uri=mast:HST/product/jclj01010_drz.fits'  # noqa: E501
        filename = download_file(url, cache=True)

        # Default behavior: Load first image
        parse_data(imviz_app.app, filename, show_in_viewer=False)
        data = imviz_app.app.data_collection[0]
        comp = data.get_component('SCI,1')
        assert data.label == 'contents[SCI,1]'  # download_file returns cache loc
        assert data.shape == (4300, 4219)
        assert isinstance(data.coords, WCS)
        assert comp.units == ''  # "ELECTRONS/S" is not valid
        assert comp.data.shape == (4300, 4219)

        # Request specific extension (name only), use given label
        parse_data(imviz_app.app, filename, ext='CTX',
                   data_label='jclj01010_drz', show_in_viewer=False)
        data = imviz_app.app.data_collection[1]
        comp = data.get_component('CTX,1')
        assert data.label == 'jclj01010_drz[CTX,1]'
        assert comp.units == ''  # BUNIT is not set

        # Request specific extension (name + ver), use given label
        parse_data(imviz_app.app, filename, ext=('WHT', 1),
                   data_label='jclj01010_drz', show_in_viewer=False)
        data = imviz_app.app.data_collection[2]
        comp = data.get_component('WHT,1')
        assert data.label == 'jclj01010_drz[WHT,1]'
        assert comp.units == ''  # BUNIT is not set

        # Pass in file obj directly
        with fits.open(filename) as pf:
            # Default behavior: Load first image
            parse_data(imviz_app.app, pf, show_in_viewer=False)
            data = imviz_app.app.data_collection[3]
            assert data.label.startswith('imviz_data|') and data.label.endswith('[SCI,1]')
            assert 'SCI,1' in data.components

            # Request specific extension (name only), use given label
            parse_data(imviz_app.app, pf, ext='CTX', show_in_viewer=False)
            data = imviz_app.app.data_collection[4]
            assert data.label.startswith('imviz_data|') and data.label.endswith('[CTX,1]')
            assert 'CTX,1' in data.components

            # Pass in HDU directly, use given label
            parse_data(imviz_app.app, pf[2], data_label='foo', show_in_viewer=False)
            data = imviz_app.app.data_collection[5]
            assert data.label == 'foo[WHT,1]'
            assert 'WHT,1' in data.components

            # Load all extensions
            imviz_app.app.data_collection.clear()
            parse_data(imviz_app.app, filename, ext='*', show_in_viewer=False)
            data = imviz_app.app.data_collection
            assert len(data.labels) == 3
            assert data.labels[0].endswith('[SCI,1]')
            assert data.labels[1].endswith('[WHT,1]')
            assert data.labels[2].endswith('[CTX,1]')

        # Cannot load non-image extension
        with pytest.raises(ValueError, match='Imviz cannot load this HDU'):
            parse_data(imviz_app.app, filename, ext='HDRTAB',
                       show_in_viewer=False)

        # Invalid FITS extension
        with pytest.raises(KeyError, match='not found'):
            parse_data(imviz_app.app, filename, ext='DOES_NOT_EXIST',
                       data_label='foo', show_in_viewer=False)
