import numpy as np
import pytest
from astropy import units as u
from astropy.io import fits
from astropy.nddata import NDData, StdDevUncertainty
from astropy.tests.helper import assert_quantity_allclose
from astropy.utils.data import download_file
from astropy.wcs import WCS
from gwcs import WCS as GWCS
from numpy.testing import assert_allclose, assert_array_equal
from regions import CirclePixelRegion
from skimage.io import imsave

from jdaviz.configs.imviz.helper import split_filename_with_fits_ext
from jdaviz.configs.imviz.plugins.aper_phot_simple.aper_phot_simple import SimpleAperturePhotometry
from jdaviz.configs.imviz.plugins.parsers import (
    parse_data, _validate_fits_image2d, _validate_bunit, _parse_image)


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
    assert _validate_bunit('MJy/sr') == 'MJy/sr'
    assert _validate_bunit('ELECTRONS/S') == 'electron/s'
    assert _validate_bunit('ELECTRONS') == 'electron'


class TestParseImage:
    def setup_class(self):
        self.jwst_asdf_url_1 = 'https://data.science.stsci.edu/redirect/JWST/jwst-data_analysis_tools/imviz_test_data/jw00042001001_01101_00001_nrcb5_cal.fits'  # noqa: E501
        self.jwst_asdf_url_2 = 'https://stsci.box.com/shared/static/d5k9z5j05dgfv6ljgie483w21kmpevni.fits'  # noqa: E501

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
                     unit=u.MJy/u.sr, wcs=WCS(naxis=2), meta={'name': 'my_ndd'})
        parse_data(imviz_app.app, ndd, data_label='some_data', show_in_viewer=False)
        for i, attrib in enumerate(['DATA', 'MASK', 'UNCERTAINTY']):
            data = imviz_app.app.data_collection[i]
            comp = data.get_component(attrib)
            assert data.label == f'some_data[{attrib}]'
            assert data.shape == (2, 2)
            assert data.meta['name'] == 'my_ndd'
            assert isinstance(data.coords, WCS)
            assert comp.data.shape == (2, 2)
            if attrib == 'MASK':
                assert comp.units == ''
            else:
                assert comp.units == 'MJy / sr'
        assert len(imviz_app.app.data_collection) == 3

    @pytest.mark.filterwarnings('ignore:.* is a low contrast image')
    @pytest.mark.parametrize('format', ('jpg', 'png'))
    def test_parse_rgba(self, imviz_app, tmp_path, format):
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
            hdu.header['foo'] = 'bar'
            hdu.writeto(fpath, overwrite=True)

        flist = ','.join(flist)
        imviz_app.load_data(flist, show_in_viewer=False)

        for i in range(2):
            data = imviz_app.app.data_collection[i]
            comp = data.get_component('PRIMARY,1')
            assert data.label == f'myfits_{i}[PRIMARY,1]'
            assert data.shape == (2, 2)
            assert data.meta['FOO'] == 'bar'
            np.testing.assert_allclose(comp.data.mean(), i)

        with pytest.raises(ValueError, match='Do not manually overwrite data_label'):
            imviz_app.load_data(flist, data_label='foo', show_in_viewer=False)

    @pytest.mark.remote_data
    def test_parse_jwst_nircam_level2(self, imviz_app):
        filename = download_file(self.jwst_asdf_url_1, cache=True)

        # Default behavior: Science image
        parse_data(imviz_app.app, filename, show_in_viewer=True)
        data = imviz_app.app.data_collection[0]
        comp = data.get_component('DATA')
        assert data.label == 'contents[DATA]'  # download_file returns cache loc
        assert data.shape == (2048, 2048)
        assert isinstance(data.coords, GWCS)
        assert comp.units == 'MJy/sr'
        assert comp.data.shape == (2048, 2048)

        # --- Since download is expensive, we attach GWCS-specific tests here. ---

        # Ensure interactive region supports GWCS. Also see test_regions.py
        imviz_app._apply_interactive_region('bqplot:circle', (965, 1122), (976.9, 1110.1))  # Star
        subsets = imviz_app.get_interactive_regions()
        assert list(subsets.keys()) == ['Subset 1'], subsets
        assert isinstance(subsets['Subset 1'], CirclePixelRegion)

        # Test simple aperture photometry plugin.
        phot_plugin = SimpleAperturePhotometry(app=imviz_app.app)
        phot_plugin._on_viewer_data_changed()
        phot_plugin.vue_data_selected('contents[DATA]')
        phot_plugin.vue_subset_selected('Subset 1')
        phot_plugin.background_value = 0.22  # Median on whole array
        # NOTE: jwst.datamodels.find_fits_keyword("PHOTMJSR")
        phot_plugin.counts_factor = (data.meta['photometry']['conversion_megajanskys'] /
                                     data.meta['exposure']['exposure_time'])
        assert_allclose(phot_plugin.counts_factor, 0.0036385915646798953)
        phot_plugin.flux_scaling = 1  # Simple mag, no zeropoint
        phot_plugin.vue_do_aper_phot()
        tbl = imviz_app.get_aperture_photometry_results()
        assert_quantity_allclose(tbl[0]['xcenter'], 970.95 * u.pix)
        assert_quantity_allclose(tbl[0]['ycenter'], 1116.05 * u.pix)
        sky = tbl[0]['sky_center']
        assert_allclose(sky.ra.deg, 80.48419863)
        assert_allclose(sky.dec.deg, -69.49460838)
        data_unit = u.MJy / u.sr
        assert_quantity_allclose(tbl[0]['background'], 0.22 * data_unit)
        assert_quantity_allclose(tbl[0]['npix'], 111.22023392 * u.pix)
        assert_quantity_allclose(tbl[0]['aperture_sum'], 4.93689560e-09 * u.MJy)
        assert_quantity_allclose(tbl[0]['pixarea_tot'], 1.0384377922763469e-11 * u.sr)
        assert_quantity_allclose(tbl[0]['aperture_sum_counts'], 130659.2466386 * u.count)
        assert_quantity_allclose(tbl[0]['aperture_sum_counts_err'], 361.46818205562715 * u.count)
        assert_quantity_allclose(tbl[0]['counts_fac'], 0.0036385915646798953 * (data_unit / u.ct))
        assert_quantity_allclose(tbl[0]['aperture_sum_mag'], -6.692683645358997 * u.mag)
        assert_quantity_allclose(tbl[0]['flux_scaling'], 1 * data_unit)
        assert_quantity_allclose(tbl[0]['mean'], 4.34584047 * data_unit)
        assert_quantity_allclose(tbl[0]['stddev'], 15.61862628 * data_unit)
        assert_quantity_allclose(tbl[0]['median'], 0.43709442 * data_unit)
        assert_quantity_allclose(tbl[0]['min'], -0.00485992 * data_unit, rtol=1e-5)
        assert_quantity_allclose(tbl[0]['max'], 138.87786865 * data_unit, rtol=1e-5)

        # --- Back to parser testing below. ---

        # Request specific extension (name + ver, but ver is not used), use given label
        parse_data(imviz_app.app, filename, ext=('DQ', 42),
                   data_label='jw01072001001_01101_00001_nrcb1_cal',
                   show_in_viewer=False)
        data = imviz_app.app.data_collection[1]
        comp = data.get_component('DQ')
        assert data.label == 'jw01072001001_01101_00001_nrcb1_cal[DQ]'
        assert data.meta['aperture']['name'] == 'NRCB5_FULL'
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
        with pytest.raises(KeyError, match='does_not_exist'):
            parse_data(imviz_app.app, filename, ext='DOES_NOT_EXIST',
                       data_label='foo', show_in_viewer=False)

    @pytest.mark.remote_data
    def test_parse_jwst_niriss_grism(self, imviz_app):
        """No valid image GWCS for Imviz, will fall back to FITS loading without WCS."""
        filename = download_file(self.jwst_asdf_url_2, cache=True)

        parse_data(imviz_app.app, filename, show_in_viewer=False)
        data = imviz_app.app.data_collection[0]
        comp = data.get_component('SCI,1')
        assert data.label == 'contents[SCI,1]'  # download_file returns cache loc
        assert data.shape == (2048, 2048)
        assert data.coords is None
        assert data.meta['RADESYS'] == 'ICRS'
        assert comp.units == 'DN/s'
        assert comp.data.shape == (2048, 2048)

    @pytest.mark.remote_data
    def test_parse_hst_drz(self, imviz_app):
        url = 'https://mast.stsci.edu/api/v0.1/Download/file?bundle_name=MAST_2021-04-21T1828.sh&uri=mast:HST/product/jclj01010_drz.fits'  # noqa: E501
        filename = download_file(url, cache=True)

        # Default behavior: Load first image
        parse_data(imviz_app.app, filename, show_in_viewer=True)
        data = imviz_app.app.data_collection[0]
        comp = data.get_component('SCI,1')
        assert data.label == 'contents[SCI,1]'  # download_file returns cache loc
        assert data.shape == (4300, 4219)
        assert_allclose(data.meta['PHOTFLAM'], 7.8711728E-20)
        assert isinstance(data.coords, WCS)
        assert comp.units == 'electron/s'
        assert comp.data.shape == (4300, 4219)

        # --- Since download is expensive, we attach FITS WCS-specific tests here. ---

        # Test simple aperture photometry plugin.
        imviz_app._apply_interactive_region('bqplot:ellipse', (1465, 2541), (1512, 2611))  # Galaxy
        phot_plugin = SimpleAperturePhotometry(app=imviz_app.app)
        phot_plugin._on_viewer_data_changed()
        phot_plugin.vue_data_selected('contents[SCI,1]')
        phot_plugin.vue_subset_selected('Subset 1')
        phot_plugin.background_value = 0.0014  # Median on whole array
        assert_allclose(phot_plugin.pixel_area, 0.0025)  # Not used but still auto-populated
        phot_plugin.vue_do_aper_phot()
        tbl = imviz_app.get_aperture_photometry_results()
        assert_quantity_allclose(tbl[0]['xcenter'], 1488.5 * u.pix)
        assert_quantity_allclose(tbl[0]['ycenter'], 2576 * u.pix)
        sky = tbl[0]['sky_center']
        assert_allclose(sky.ra.deg, 3.6840882015888323)
        assert_allclose(sky.dec.deg, 10.802065746813046)
        data_unit = u.electron / u.s
        assert_quantity_allclose(tbl[0]['background'], 0.0014 * data_unit)
        assert_quantity_allclose(tbl[0]['npix'], 645.98998939 * u.pix)
        assert_quantity_allclose(tbl[0]['aperture_sum'], 81.01186025 * data_unit)
        assert_array_equal(tbl[0]['pixarea_tot'], None)
        assert_array_equal(tbl[0]['aperture_sum_counts'], None)
        assert_array_equal(tbl[0]['aperture_sum_counts_err'], None)
        assert_array_equal(tbl[0]['counts_fac'], None)
        assert_array_equal(tbl[0]['aperture_sum_mag'], None)
        assert_array_equal(tbl[0]['flux_scaling'], None)
        assert_quantity_allclose(tbl[0]['mean'], 0.12466364 * data_unit)
        assert_quantity_allclose(tbl[0]['stddev'], 0.1784373 * data_unit)
        assert_quantity_allclose(tbl[0]['median'], 0.06988327 * data_unit)
        assert_quantity_allclose(tbl[0]['min'], 0.0013524 * data_unit, rtol=1e-5)
        assert_quantity_allclose(tbl[0]['max'], 1.5221194 * data_unit, rtol=1e-5)

        # Request specific extension (name only), use given label
        parse_data(imviz_app.app, filename, ext='CTX',
                   data_label='jclj01010_drz', show_in_viewer=False)
        data = imviz_app.app.data_collection[1]
        comp = data.get_component('CTX,1')
        assert data.label == 'jclj01010_drz[CTX,1]'
        assert data.meta['EXTNAME'] == 'CTX'
        assert comp.units == ''  # BUNIT is not set

        # Request specific extension (name + ver), use given label
        parse_data(imviz_app.app, filename, ext=('WHT', 1),
                   data_label='jclj01010_drz', show_in_viewer=False)
        data = imviz_app.app.data_collection[2]
        comp = data.get_component('WHT,1')
        assert data.label == 'jclj01010_drz[WHT,1]'
        assert data.meta['EXTNAME'] == 'WHT'
        assert comp.units == ''  # BUNIT is not set

        # Pass in file obj directly
        with fits.open(filename) as pf:
            # Default behavior: Load first image
            parse_data(imviz_app.app, pf, show_in_viewer=False)
            data = imviz_app.app.data_collection[3]
            assert data.label.startswith('imviz_data|') and data.label.endswith('[SCI,1]')
            assert_allclose(data.meta['PHOTFLAM'], 7.8711728E-20)
            assert 'SCI,1' in data.components

            # Request specific extension (name only), use given label
            parse_data(imviz_app.app, pf, ext='CTX', show_in_viewer=False)
            data = imviz_app.app.data_collection[4]
            assert data.label.startswith('imviz_data|') and data.label.endswith('[CTX,1]')
            assert data.meta['EXTNAME'] == 'CTX'
            assert 'CTX,1' in data.components

            # Pass in HDU directly, use given label
            parse_data(imviz_app.app, pf[2], data_label='foo', show_in_viewer=False)
            data = imviz_app.app.data_collection[5]
            assert data.label == 'foo[WHT,1]'
            assert data.meta['EXTNAME'] == 'WHT'
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


def test_load_valid_not_valid(imviz_app):
    # Load something valid.
    arr = np.ones((5, 5))
    imviz_app.load_data(arr, data_label='valid', show_in_viewer=False)

    # Load something invalid.
    with pytest.raises(ValueError, match='Imviz cannot load this array with ndim=1'):
        imviz_app.load_data(np.zeros(2), show_in_viewer=False)

    # Make sure valid data is still there.
    assert (len(imviz_app.app.data_collection) == 1
            and imviz_app.app.data_collection.labels == ['valid'])
    assert_allclose(imviz_app.app.data_collection[0].get_component('DATA').data, 1)
