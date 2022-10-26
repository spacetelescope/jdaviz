import numpy as np
import pytest
from asdf.fits_embed import AsdfInFits
from astropy import units as u
from astropy.io import fits
from astropy.nddata import NDData, StdDevUncertainty
from astropy.tests.helper import assert_quantity_allclose
from astropy.utils.data import download_file
from astropy.wcs import WCS
from gwcs import WCS as GWCS
from numpy.testing import assert_allclose, assert_array_equal
from regions import CirclePixelRegion, RectanglePixelRegion
from skimage.io import imsave

from jdaviz.configs.imviz.helper import split_filename_with_fits_ext
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
        with pytest.raises(ValueError, match='app is None'):
            _parse_image(None, None, None, False)

    def test_hdulist_no_image(self, imviz_helper):
        hdulist = fits.HDUList([fits.PrimaryHDU()])
        with pytest.raises(ValueError, match='does not have any FITS image'):
            parse_data(imviz_helper.app, hdulist)

    @pytest.mark.parametrize('some_obj', (WCS(), [[1, 2], [3, 4]]))
    def test_invalid_file_obj(self, imviz_helper, some_obj):
        with pytest.raises(NotImplementedError, match='Imviz does not support'):
            parse_data(imviz_helper.app, some_obj)

    def test_parse_numpy_array_1d_2d(self, imviz_helper):
        with pytest.raises(ValueError, match='Imviz cannot load this array with ndim=1'):
            parse_data(imviz_helper.app, np.zeros(2))

        # Passing in data_label keyword as posarg.
        imviz_helper.load_data(np.zeros((2, 2)), 'some_array', show_in_viewer=False)
        data = imviz_helper.app.data_collection[0]
        comp = data.get_component('DATA')
        assert data.label == 'some_array'
        assert data.shape == (2, 2)
        assert comp.data.shape == (2, 2)

    @pytest.mark.parametrize('manual_loop', [False, True])
    def test_parse_numpy_array_3d(self, imviz_helper, manual_loop):
        # This data has values in axis=0 that correspond to axis num.
        n_slices = 5
        slice_shape = (2, 3)
        arr = np.stack([np.zeros(slice_shape) + i for i in range(n_slices)])
        data_label = 'my_slices'

        if not manual_loop:
            # We use higher level load_data() here to make sure linking does not crash.
            imviz_helper.load_data(arr, data_label=data_label)
        else:
            with imviz_helper.batch_load():
                for i in range(n_slices):
                    imviz_helper.load_data(arr[i, :, :], data_label=data_label)

        assert len(imviz_helper.app.data_collection) == n_slices
        assert len(imviz_helper.app.data_collection.links) == 8

        for i in range(n_slices):
            data = imviz_helper.app.data_collection[i]
            comp = data.get_component('DATA')
            assert data.label == (f'my_slices ({i})' if i > 0 else 'my_slices')
            assert data.shape == slice_shape
            assert_array_equal(comp.data, i)

    def test_parse_numpy_array_3d_too_many(self, imviz_helper):
        with pytest.warns(UserWarning, match='16 or more 3D slices found'):
            imviz_helper.load_data(np.ones((17, 5, 5)))

        assert len(imviz_helper.app.data_collection) == 16
        assert imviz_helper.app.data_collection[0].shape == (5, 5)
        assert imviz_helper.app.data_collection[15].shape == (5, 5)

    def test_parse_numpy_array_4d(self, imviz_helper):
        # Check logic is in higher level method.
        imviz_helper.load_data(np.ones((1, 2, 5, 5)))
        assert len(imviz_helper.app.data_collection) == 2
        assert imviz_helper.app.data_collection[0].shape == (5, 5)
        assert imviz_helper.app.data_collection[1].shape == (5, 5)

        with pytest.raises(ValueError, match='cannot load this array with ndim'):
            imviz_helper.load_data(np.ones((2, 2, 5, 5)))

    def test_parse_nddata_simple(self, imviz_helper):
        with pytest.raises(ValueError, match='Imviz cannot load this NDData with ndim=1'):
            parse_data(imviz_helper.app, NDData([1, 2, 3, 4]))

        ndd = NDData([[1, 2], [3, 4]])
        imviz_helper.load_data(ndd, data_label='some_data', show_in_viewer=False)
        data = imviz_helper.app.data_collection[0]
        comp = data.get_component('DATA')
        assert data.label == 'some_data[DATA]'
        assert data.shape == (2, 2)
        assert comp.data.shape == (2, 2)
        assert len(imviz_helper.app.data_collection) == 1

    @pytest.mark.parametrize(
        ('ndd', 'attributes'),
        [(NDData([[1, 2], [3, 4]], mask=[[True, False], [False, False]]),
          ['DATA', 'MASK']),
         (NDData([[1, 2], [3, 4]], uncertainty=StdDevUncertainty([[0.1, 0.2], [0.3, 0.4]])),
          ['DATA', 'UNCERTAINTY'])])
    def test_parse_nddata_with_one_only(self, imviz_helper, ndd, attributes):
        imviz_helper.load_data(ndd, data_label='some_data', show_in_viewer=False)
        for i, attrib in enumerate(attributes):
            data = imviz_helper.app.data_collection[i]
            comp = data.get_component(attrib)
            assert data.label == f'some_data[{attrib}]'
            assert data.shape == (2, 2)
            assert comp.data.shape == (2, 2)
        assert len(imviz_helper.app.data_collection) == 2

    def test_parse_nddata_with_everything(self, imviz_helper):
        ndd = NDData([[1, 2], [3, 4]], mask=[[True, False], [False, False]],
                     uncertainty=StdDevUncertainty([[0.1, 0.2], [0.3, 0.4]]),
                     unit=u.MJy/u.sr, wcs=WCS(naxis=2), meta={'name': 'my_ndd'})
        imviz_helper.load_data(ndd, data_label='some_data', show_in_viewer=False)
        for i, attrib in enumerate(['DATA', 'MASK', 'UNCERTAINTY']):
            data = imviz_helper.app.data_collection[i]
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
        assert len(imviz_helper.app.data_collection) == 3

    @pytest.mark.filterwarnings('ignore:.* is a low contrast image')
    @pytest.mark.parametrize('format', ('jpg', 'png'))
    def test_parse_rgba(self, imviz_helper, tmp_path, format):
        if format == 'png':  # Cross-test PNG with RGBA
            a = np.zeros((10, 10, 4), dtype='uint8')
        else:  # Cross-test JPG with RGB only
            a = np.zeros((10, 10, 3), dtype='uint8')

        filename = str(tmp_path / f'myimage.{format}')
        imsave(filename, a)

        imviz_helper.load_data(filename, show_in_viewer=False)
        data = imviz_helper.app.data_collection[0]
        assert data.label == 'myimage'
        assert data.shape == (10, 10)

    def test_filelist(self, imviz_helper, tmp_path):
        flist = []

        # Generate some files to parse.
        for i in range(2):
            fpath = tmp_path / f'myfits_{i}.fits'
            flist.append(str(fpath))
            hdu = fits.PrimaryHDU(np.zeros((2, 2)) + i)
            hdu.header['foo'] = 'bar'
            hdu.writeto(fpath, overwrite=True)

        flist = ','.join(flist)
        imviz_helper.load_data(flist, show_in_viewer=False)

        for i in range(2):
            data = imviz_helper.app.data_collection[i]
            comp = data.get_component('PRIMARY,1')
            assert data.label == f'myfits_{i}[PRIMARY,1]'
            assert data.shape == (2, 2)
            assert data.meta['FOO'] == 'bar'
            np.testing.assert_allclose(comp.data.mean(), i)

        with pytest.raises(ValueError, match='Do not manually overwrite data_label'):
            imviz_helper.load_data(flist, data_label='foo', show_in_viewer=False)

    def test_parse_asdf_in_fits_4d(self, imviz_helper, tmpdir):
        hdulist = fits.HDUList([
            fits.PrimaryHDU(),
            fits.ImageHDU(np.zeros((1, 2, 5, 5)), name='SCI')])
        tree = {'data': {'data': hdulist['SCI'].data}}
        filename = str(tmpdir.join('myasdf.fits'))
        ff = AsdfInFits(hdulist, tree)
        ff.write_to(filename, overwrite=True)

        with pytest.raises(ValueError, match='Imviz cannot load this HDU'):
            parse_data(imviz_helper.app, filename)

    @pytest.mark.remote_data
    def test_parse_jwst_nircam_level2(self, imviz_helper):
        filename = download_file(self.jwst_asdf_url_1, cache=True)

        # Default behavior: Science image
        imviz_helper.load_data(filename)
        data = imviz_helper.app.data_collection[0]
        comp = data.get_component('DATA')
        assert data.label == 'contents[DATA]'  # download_file returns cache loc
        assert data.shape == (2048, 2048)
        assert isinstance(data.coords, GWCS)
        assert comp.units == 'MJy/sr'
        assert comp.data.shape == (2048, 2048)

        # --- Since download is expensive, we attach GWCS-specific tests here. ---

        # Ensure interactive region supports GWCS. Also see test_regions.py
        imviz_helper._apply_interactive_region('bqplot:circle',
                                               (965, 1122),
                                               (976.9, 1110.1))  # Star
        imviz_helper._apply_interactive_region('bqplot:rectangle',
                                               (982, 1088),
                                               (1008, 1077))  # Background
        subsets = imviz_helper.get_interactive_regions()
        assert list(subsets.keys()) == ['Subset 1', 'Subset 2'], subsets
        assert isinstance(subsets['Subset 1'], CirclePixelRegion)
        assert isinstance(subsets['Subset 2'], RectanglePixelRegion)

        # Test simple aperture photometry plugin.
        phot_plugin = imviz_helper.app.get_tray_item_from_name('imviz-aper-phot-simple')
        phot_plugin.data_selected = 'contents[DATA]'
        phot_plugin.subset_selected = 'Subset 1'
        assert_allclose(phot_plugin.background_value, 0)
        phot_plugin.bg_subset_selected = 'Subset 2'
        assert_allclose(phot_plugin.background_value, 0.1741226315498352)  # Subset 2 median
        # NOTE: jwst.datamodels.find_fits_keyword("PHOTMJSR")
        phot_plugin.counts_factor = (data.meta['photometry']['conversion_megajanskys'] /
                                     data.meta['exposure']['exposure_time'])
        assert_allclose(phot_plugin.counts_factor, 0.0036385915646798953)
        assert_allclose(phot_plugin.flux_scaling, 0.003631)
        phot_plugin.vue_do_aper_phot()
        tbl = imviz_helper.get_aperture_photometry_results()
        assert_quantity_allclose(tbl[0]['xcentroid'], 970.935492 * u.pix)
        assert_quantity_allclose(tbl[0]['ycentroid'], 1116.967619 * u.pix)
        sky = tbl[0]['sky_centroid']
        assert_allclose(sky.ra.deg, 80.48419863)
        assert_allclose(sky.dec.deg, -69.494592)
        data_unit = u.MJy / u.sr
        assert_quantity_allclose(tbl[0]['background'], 0.1741226315498352 * data_unit)
        assert_quantity_allclose(tbl[0]['sum'], 4.486487e-11 * u.MJy, rtol=1e-6)
        assert_quantity_allclose(tbl[0]['sum_aper_area'], 111.220234 * (u.pix * u.pix))
        assert_quantity_allclose(tbl[0]['pixarea_tot'], 9.33677e-14 * u.sr, rtol=1e-6)
        assert_quantity_allclose(tbl[0]['aperture_sum_counts'], 132061.576643 * u.count, rtol=1e-6)
        assert_quantity_allclose(tbl[0]['aperture_sum_counts_err'], 363.402775 * u.count)
        assert_quantity_allclose(tbl[0]['counts_fac'], 0.0036385915646798953 * (data_unit / u.ct))
        assert_quantity_allclose(tbl[0]['aperture_sum_mag'], 19.770299 * u.mag)
        assert_quantity_allclose(tbl[0]['flux_scaling'], 3631 * u.Jy)
        assert_quantity_allclose(tbl[0]['min'], 0.041017 * data_unit, atol=1e-5 * data_unit)
        assert_quantity_allclose(tbl[0]['max'], 138.923752 * data_unit, rtol=1e-5)
        assert_quantity_allclose(tbl[0]['mean'], 4.391718 * data_unit)
        assert_quantity_allclose(tbl[0]['median'], 0.482972 * data_unit, rtol=1e-5)
        assert_quantity_allclose(tbl[0]['mode'], -7.33452046 * data_unit)
        assert_quantity_allclose(tbl[0]['std'], 15.618626488031158 * data_unit)
        assert_quantity_allclose(tbl[0]['mad_std'], 0.47892631 * data_unit)
        assert_quantity_allclose(tbl[0]['var'], 243.9415 * (data_unit * data_unit))
        assert_quantity_allclose(tbl[0]['biweight_location'], 0.40664572 * data_unit)
        assert_quantity_allclose(tbl[0]['biweight_midvariance'], 0.27319583 * (data_unit * data_unit))  # noqa
        assert_quantity_allclose(tbl[0]['fwhm'], 2.8691718 * u.pix)
        assert_quantity_allclose(tbl[0]['semimajor_sigma'], 1.22308648 * u.pix)
        assert_quantity_allclose(tbl[0]['semiminor_sigma'], 1.21374578 * u.pix)
        assert_quantity_allclose(tbl[0]['orientation'], -27.220559 * u.deg)
        assert_quantity_allclose(tbl[0]['eccentricity'], 0.12335181)

        # --- Back to parser testing below. ---

        # Request specific extension (name + ver, but ver is not used), use given label
        imviz_helper.load_data(filename, ext=('DQ', 42),
                               data_label='jw01072001001_01101_00001_nrcb1_cal',
                               show_in_viewer=False)
        data = imviz_helper.app.data_collection[1]
        comp = data.get_component('DQ')
        assert data.label == 'jw01072001001_01101_00001_nrcb1_cal[DQ]'
        assert data.meta['aperture']['name'] == 'NRCB5_FULL'
        assert comp.units == ''

        # Pass in HDUList directly + ext (name only), use given label
        with fits.open(filename) as pf:
            imviz_helper.load_data(pf, ext='SCI',
                                   data_label='jw01072001001_01101_00001_nrcb1_cal',
                                   show_in_viewer=False)
            data = imviz_helper.app.data_collection[2]
            comp = data.get_component('DATA')  # SCI = DATA
            assert data.label == 'jw01072001001_01101_00001_nrcb1_cal[DATA]'
            assert isinstance(data.coords, GWCS)
            assert comp.units == 'MJy/sr'

            # Test duplicate label functionality
            imviz_helper.app.data_collection.clear()
            imviz_helper.load_data(pf, ext='SCI', data_label='TEST', show_in_viewer=False)
            data = imviz_helper.app.data_collection[0]
            assert data.label.endswith('[DATA]')

            imviz_helper.load_data(pf, ext='SCI', data_label='TEST', show_in_viewer=False)
            data = imviz_helper.app.data_collection[1]
            assert data.label.endswith('[DATA] (1)')

            # Load all extensions
            imviz_helper.app.data_collection.clear()
            imviz_helper.load_data(pf, ext='*', show_in_viewer=False)
            data = imviz_helper.app.data_collection
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
            parse_data(imviz_helper.app, filename, ext='DOES_NOT_EXIST', data_label='foo')

    @pytest.mark.remote_data
    def test_parse_jwst_niriss_grism(self, imviz_helper):
        """No valid image GWCS for Imviz, will fall back to FITS loading without WCS."""
        filename = download_file(self.jwst_asdf_url_2, cache=True)

        imviz_helper.load_data(filename, show_in_viewer=False)
        data = imviz_helper.app.data_collection[0]
        comp = data.get_component('SCI,1')
        assert data.label == 'contents[SCI,1]'  # download_file returns cache loc
        assert data.shape == (2048, 2048)
        assert data.coords is None
        assert data.meta['RADESYS'] == 'ICRS'
        assert comp.units == 'DN/s'
        assert comp.data.shape == (2048, 2048)

    @pytest.mark.remote_data
    def test_parse_hst_drz(self, imviz_helper):
        url = 'https://mast.stsci.edu/api/v0.1/Download/file?bundle_name=MAST_2021-04-21T1828.sh&uri=mast:HST/product/jclj01010_drz.fits'  # noqa: E501
        filename = download_file(url, cache=True)

        # Default behavior: Load first image
        imviz_helper.load_data(filename)
        data = imviz_helper.app.data_collection[0]
        comp = data.get_component('SCI,1')
        assert data.label == 'contents[SCI,1]'  # download_file returns cache loc
        assert data.shape == (4299, 4220)
        assert_allclose(data.meta['PHOTFLAM'], 7.8711728E-20)
        assert isinstance(data.coords, WCS)
        assert comp.units == 'electron/s'
        assert comp.data.shape == (4299, 4220)

        # --- Since download is expensive, we attach FITS WCS-specific tests here. ---

        # Test simple aperture photometry plugin.
        imviz_helper._apply_interactive_region('bqplot:ellipse',
                                               (1465, 2541),
                                               (1512, 2611))  # Galaxy
        phot_plugin = imviz_helper.app.get_tray_item_from_name('imviz-aper-phot-simple')
        phot_plugin.data_selected = 'contents[SCI,1]'
        phot_plugin.subset_selected = 'Subset 1'
        phot_plugin.background_value = 0.0014  # Manual entry: Median on whole array
        assert_allclose(phot_plugin.pixel_area, 0.0025)  # Not used but still auto-populated
        phot_plugin.vue_do_aper_phot()
        tbl = imviz_helper.get_aperture_photometry_results()
        assert_quantity_allclose(tbl[0]['xcentroid'], 1487.60825422 * u.pix, atol=2 * u.pix)
        assert_quantity_allclose(tbl[0]['ycentroid'], 2573.83983184 * u.pix, atol=2 * u.pix)
        sky = tbl[0]['sky_centroid']
        assert_allclose(sky.ra.deg, 3.684062989070131, rtol=1e-3)
        assert_allclose(sky.dec.deg, 10.802045612042956, rtol=1e-3)
        data_unit = u.electron / u.s
        assert_quantity_allclose(tbl[0]['background'], 0.0014 * data_unit)
        assert_quantity_allclose(tbl[0]['sum'], 126.219763 * data_unit, rtol=1e-3)
        assert_quantity_allclose(tbl[0]['sum_aper_area'], 2583.959958 * (u.pix * u.pix), rtol=1e-3)
        assert_array_equal(tbl[0]['pixarea_tot'], None)
        assert_array_equal(tbl[0]['aperture_sum_counts'], None)
        assert_array_equal(tbl[0]['aperture_sum_counts_err'], None)
        assert_array_equal(tbl[0]['counts_fac'], None)
        assert_array_equal(tbl[0]['aperture_sum_mag'], None)
        assert_array_equal(tbl[0]['flux_scaling'], None)
        assert_quantity_allclose(tbl[0]['min'], -0.032984 * data_unit, rtol=1e-3)
        assert_quantity_allclose(tbl[0]['max'], 4.905623 * data_unit, rtol=1e-3)
        assert_quantity_allclose(tbl[0]['mean'], 0.048932 * data_unit, rtol=1e-3)
        assert_quantity_allclose(tbl[0]['median'], 0.021932 * data_unit, rtol=1e-3)
        assert_quantity_allclose(tbl[0]['mode'], -0.032068 * data_unit, rtol=1e-3)
        assert_quantity_allclose(tbl[0]['std'], 0.152998 * data_unit, rtol=1e-3)
        assert_quantity_allclose(tbl[0]['mad_std'], 0.023284 * data_unit, rtol=1e-3)
        assert_quantity_allclose(tbl[0]['var'], 0.023408 * (data_unit * data_unit), rtol=1e-3)
        assert_quantity_allclose(tbl[0]['biweight_location'], 0.02106674 * data_unit, rtol=1e-3)
        assert_quantity_allclose(tbl[0]['biweight_midvariance'], 0.00062667 * (data_unit * data_unit), rtol=1e-3)  # noqa
        assert_quantity_allclose(tbl[0]['fwhm'], 25.311096 * u.pix, rtol=1e-3)
        assert_quantity_allclose(tbl[0]['semimajor_sigma'], 13.018475 * u.pix, rtol=1e-3)
        assert_quantity_allclose(tbl[0]['semiminor_sigma'], 7.847643 * u.pix, rtol=1e-3)
        assert_quantity_allclose(tbl[0]['orientation'], 88.874367 * u.deg, rtol=1e-3)
        assert_quantity_allclose(tbl[0]['eccentricity'], 0.797886, rtol=1e-3)

        # Request specific extension (name only), use given label
        imviz_helper.load_data(filename, ext='CTX', data_label='jclj01010_drz',
                               show_in_viewer=False)
        data = imviz_helper.app.data_collection[1]
        comp = data.get_component('CTX,1')
        assert data.label == 'jclj01010_drz[CTX,1]'
        assert data.meta['EXTNAME'] == 'CTX'
        assert comp.units == ''  # BUNIT is not set

        # Request specific extension (name + ver), use given label
        imviz_helper.load_data(filename, ext=('WHT', 1), data_label='jclj01010_drz',
                               show_in_viewer=False)
        data = imviz_helper.app.data_collection[2]
        comp = data.get_component('WHT,1')
        assert data.label == 'jclj01010_drz[WHT,1]'
        assert data.meta['EXTNAME'] == 'WHT'
        assert comp.units == ''  # BUNIT is not set

        # Pass in file obj directly
        with fits.open(filename) as pf:
            # Default behavior: Load first image
            imviz_helper.load_data(pf, show_in_viewer=False)
            data = imviz_helper.app.data_collection[3]
            assert data.label.startswith('Unknown HDU object') and data.label.endswith('[SCI,1]')
            assert_allclose(data.meta['PHOTFLAM'], 7.8711728E-20)
            assert 'SCI,1' in data.components

            # Request specific extension (name only), use given label
            imviz_helper.load_data(pf, ext='CTX', show_in_viewer=False)
            data = imviz_helper.app.data_collection[4]
            assert data.label.startswith('Unknown HDU object') and data.label.endswith('[CTX,1]')
            assert data.meta['EXTNAME'] == 'CTX'
            assert 'CTX,1' in data.components

            # Pass in HDU directly, use given label
            imviz_helper.load_data(pf[2], data_label='foo', show_in_viewer=False)
            data = imviz_helper.app.data_collection[5]
            assert data.label == 'foo[WHT,1]'
            assert data.meta['EXTNAME'] == 'WHT'
            assert 'WHT,1' in data.components

            # Load all extensions
            imviz_helper.app.data_collection.clear()
            imviz_helper.load_data(filename, ext='*', show_in_viewer=False)
            data = imviz_helper.app.data_collection
            assert len(data.labels) == 3
            assert data.labels[0].endswith('[SCI,1]')
            assert data.labels[1].endswith('[WHT,1]')
            assert data.labels[2].endswith('[CTX,1]')

        # Cannot load non-image extension
        with pytest.raises(ValueError, match='Imviz cannot load this HDU'):
            parse_data(imviz_helper.app, filename, ext='HDRTAB')

        # Invalid FITS extension
        with pytest.raises(KeyError, match='not found'):
            parse_data(imviz_helper.app, filename, ext='DOES_NOT_EXIST', data_label='foo')


def test_load_valid_not_valid(imviz_helper):
    # Load something valid.
    arr = np.ones((5, 5))
    imviz_helper.load_data(arr, data_label='valid', show_in_viewer=False)

    # Load something invalid.
    with pytest.raises(ValueError, match='Imviz cannot load this array with ndim=1'):
        imviz_helper.load_data(np.zeros(2), show_in_viewer=False)

    # Make sure valid data is still there.
    assert (len(imviz_helper.app.data_collection) == 1
            and imviz_helper.app.data_collection.labels == ['valid'])
    assert_allclose(imviz_helper.app.data_collection[0].get_component('DATA').data, 1)
