import numpy as np
import pytest
from astropy import units as u
from astropy.io import fits
from astropy.table import Table
from specutils import Spectrum

from jdaviz.core.loaders.importers.mos.mos import MOSImporter


class TestMOSImporter:
    """
    Tests for the MOS importer that all share a single on-disk MOS directory.
    """

    @pytest.fixture(scope='class')
    def mos_dir(self, tmp_path_factory):
        """
        A MOS directory containing one of each supported product, plus one image
        product that passes the (cheap) header check but fails on import.
        """
        path = tmp_path_factory.mktemp('mos_root') / 'mosdir'
        path.mkdir()

        spectral_axis = np.arange(1, 11) * u.um
        for index in range(2):
            Spectrum(
                flux=(np.arange(1, 11) + index) * u.Jy, spectral_axis=spectral_axis).write(
                path / f'jw0000{index}_x1d.fits', format='tabular-fits'
            )

        # the 2D spectrum carries a spectral WCS matching the 1D spectra, so that
        # an auto-extracted spectrum is compatible with the 1D Spectrum viewer
        hdu = fits.ImageHDU(np.ones((5, 10)), name='SCI')
        hdu.header.update({'CTYPE1': 'WAVE', 'CUNIT1': 'um', 'CRVAL1': 1.0,
                           'CDELT1': 1.0, 'CRPIX1': 1.0,
                           'CTYPE2': 'LINEAR', 'CUNIT2': 'pix', 'CRVAL2': 1.0,
                           'CDELT2': 1.0, 'CRPIX2': 1.0, 'BUNIT': 'Jy'})
        fits.HDUList([fits.PrimaryHDU(), hdu]).writeto(path / 'jw00000_s2d.fits')

        fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(np.ones((8, 8)), name='SCI')]
                     ).writeto(path / 'jw00000_i2d.fits')

        # a 1D array in an image product: valid FITS, but can't be imported as an image
        fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(np.ones(8), name='SCI')]
                     ).writeto(path / 'jw00001_i2d.fits')

        Table({'label': [1, 2], 'ra': [1.0, 2.0], 'dec': [1.0, 2.0]}
              ).write(path / 'jw00000_cat.ecsv')

        return path

    @pytest.fixture(autouse=True)
    def _setup(self, deconfigged_helper, mos_dir):
        self.helper = deconfigged_helper
        self.helper._app.state.dev_mos_loader = True
        self.mos_dir = mos_dir

    def _loader_for_mos_dir(self):
        loader = self.helper.loaders['file']
        loader.filepath = str(self.mos_dir)
        return loader

    def _assert_visible(self, viewer_label, expected):
        """
        Assert which entries the data menu of ``viewer_label`` reports as visible.
        """
        data_menu = self.helper.viewers[viewer_label].data_menu
        assert set(data_menu.data_labels_visible) == set(expected)

    def test_is_valid(self, tmp_path):
        resolver = self.helper.loaders['object']._obj
        importer = MOSImporter(app=self.helper._app,
                               resolver=resolver,
                               parser=None,
                               input=self.mos_dir)

        assert importer._check_is_valid() == ''

        importer._input = self.mos_dir / 'jw00000_x1d.fits'
        assert importer._check_is_valid() == 'MOS importer input must be a directory.'

        # 1D spectra are searched for recursively
        nested_dir = tmp_path / 'nested'
        (nested_dir / 'JWST' / 'product').mkdir(parents=True)
        fits.PrimaryHDU(np.arange(10.)).writeto(
            nested_dir / 'JWST' / 'product' / 'jw00001_x1d.fits')
        importer._input = nested_dir
        assert importer._check_is_valid() == ''

        empty_dir = tmp_path / 'empty'
        empty_dir.mkdir()
        importer._input = empty_dir
        assert (importer._check_is_valid() ==
                'Input directory does not contain any MOS 1D spectra matching *_x1d.fits.')

        # ignored files do not make an otherwise empty directory valid
        (empty_dir / 'MANIFEST.HTML').touch()
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
        assert (importer._check_is_valid() ==
                'Input directory contains unsupported MOS file: notes.txt')

        spectrum_2d_and_image_dir = tmp_path / 'spectrum_2d_and_image'
        spectrum_2d_and_image_dir.mkdir()
        (spectrum_2d_and_image_dir / 'jw00006_s2d.fits').touch()
        (spectrum_2d_and_image_dir / 'jw00006_i2d.fits').touch()
        importer._input = spectrum_2d_and_image_dir
        assert (importer._check_is_valid() ==
                'Input directory does not contain any MOS 1D spectra matching *_x1d.fits.')

    def test_import_all(self):
        loader = self._loader_for_mos_dir()
        assert loader.format.choices == ['MOS']

        importer = loader.importer._obj
        # the data-label defaults to a prefix based on the directory name, with one
        # suffix per file
        assert importer.data_label_is_prefix
        assert importer.data_label_value == 'mosdir'
        # use set to avoid any potential ordering issues
        assert set(importer.data_label_suffices) == {
            '_jw00000_cat', '_jw00000_i2d', '_jw00000_s2d',
            '_jw00000_x1d', '_jw00001_i2d', '_jw00001_x1d'
        }
        assert [item['count'] for item in importer.product_items] == [2, 1, 2, 1]
        assert importer.product_types == ['spectrum1d', 'spectrum2d', 'image', 'catalog']

        # each product type defaults to creating its own (compatible) viewer
        assert importer.viewer.create_new.selected == '1D Spectrum'
        assert importer.viewer_2d.create_new.selected == '2D Spectrum'
        assert importer.viewer_image.create_new.selected == 'Image'
        assert importer.viewer_catalog.create_new.selected == 'Table'

        # MOS directories are expected to provide their own 1D spectra
        assert importer.auto_extract_2d is False

        loader.load()

        assert set((data.label for data in self.helper._app.data_collection)) == {
            'mosdir_jw00000_cat', 'mosdir_jw00000_i2d', 'mosdir_jw00000_s2d',
            'mosdir_jw00000_x1d', 'mosdir_jw00001_x1d'
        }

        viewers = self.helper.viewers
        assert set(viewers.keys()) == {'1D Spectrum', '2D Spectrum', 'Image', 'Table'}
        assert set(viewers['1D Spectrum'].data_menu.data_labels_loaded) == {
            'mosdir_jw00000_x1d', 'mosdir_jw00001_x1d'}
        assert viewers['2D Spectrum'].data_menu.data_labels_loaded == ['mosdir_jw00000_s2d']
        assert viewers['Image'].data_menu.data_labels_loaded == ['mosdir_jw00000_i2d']
        assert viewers['Table'].data_menu.data_labels_loaded == ['mosdir_jw00000_cat']

        # everything is loaded into the viewers,
        # but only one entry per viewer should be visible
        self._assert_visible('1D Spectrum', ['mosdir_jw00000_x1d'])
        self._assert_visible('2D Spectrum', ['mosdir_jw00000_s2d'])
        self._assert_visible('Image', ['mosdir_jw00000_i2d'])

        # the single failing file is reported inline (and in the logger history)
        messages = importer.loader_message_items
        assert [item['color'] for item in messages] == ['error', 'warning']
        assert messages[0]['text'].startswith("Failed to import 'jw00001_i2d.fits': ")
        assert messages[1]['text'] == ('1 of 6 files could not be imported '
                                       '(jw00001_i2d.fits).')

    def test_show_single_layer_per_viewer(self):
        """
        Check that only a single layer is visible in each viewer.
        """
        self._loader_for_mos_dir().load()

        for viewer_label, visible_label in (('1D Spectrum', 'mosdir_jw00000_x1d'),
                                            ('2D Spectrum', 'mosdir_jw00000_s2d'),
                                            ('Image', 'mosdir_jw00000_i2d')):
            self._assert_visible(viewer_label, [visible_label])

            layers = self.helper._app.get_viewer(viewer_label).layers
            assert [layer.layer.label
                    for layer in layers if layer.state.visible] == [visible_label]

            drawn = {layer.layer.label: layer.line_mark.visible
                     for layer in layers if getattr(layer, 'line_mark', None) is not None}
            assert [label for label, visible in drawn.items() if visible] == [
                label for label in [visible_label] if label in drawn]

    def test_reimport_into_existing_viewers(self):
        """
        Re-importing a directory into the viewers created by an earlier import must
        still leave only a single entry visible. Every entry is overwritten by the
        second import, so each one is both already-loaded and newly-imported.
        """
        self._loader_for_mos_dir().load()

        loaded = ['mosdir_jw00000_x1d', 'mosdir_jw00001_x1d']
        assert sorted(self.helper.viewers['1D Spectrum'].data_menu.data_labels_loaded) == loaded
        self._assert_visible('1D Spectrum', ['mosdir_jw00000_x1d'])

        # import the same directory again, this time into the now-existing viewers
        loader = self._loader_for_mos_dir()
        importer = loader.importer._obj
        for viewer_select, viewer_label in ((importer.viewer, '1D Spectrum'),
                                            (importer.viewer_2d, '2D Spectrum'),
                                            (importer.viewer_image, 'Image'),
                                            (importer.viewer_catalog, 'Table')):
            viewer_select.create_new.selected = ''
            viewer_select.selected = [viewer_label]
        loader.load()

        # the entries were overwritten rather than duplicated, and only the first is
        # left visible
        assert sorted(self.helper.viewers['1D Spectrum'].data_menu.data_labels_loaded) == loaded
        self._assert_visible('1D Spectrum', ['mosdir_jw00000_x1d'])
        self._assert_visible('2D Spectrum', ['mosdir_jw00000_s2d'])
        self._assert_visible('Image', ['mosdir_jw00000_i2d'])

    def test_preexisting_data_left_visible(self):
        """
        Data the user loaded before the import isn't touched, even though everything
        the import itself adds (beyond the first entry) is hidden.
        """
        self.helper.load(Spectrum(flux=np.arange(1, 11) * u.Jy,
                                  spectral_axis=np.arange(1, 11) * u.um),
                         format='1D Spectrum', data_label='preexisting')
        self._assert_visible('1D Spectrum', ['preexisting'])

        loader = self._loader_for_mos_dir()
        importer = loader.importer._obj
        importer.viewer.create_new.selected = ''
        importer.viewer.selected = ['1D Spectrum']
        loader.load()

        self._assert_visible('1D Spectrum', ['preexisting', 'mosdir_jw00000_x1d'])

    def test_auto_extract_2d(self):
        loader = self._loader_for_mos_dir()
        importer = loader.importer._obj
        importer.auto_extract_2d = True

        loader.load()

        labels = [data.label for data in self.helper._app.data_collection]
        # the 2D spectrum (and its extraction) are imported after the other
        # products, since auto-extraction can't happen within ``batch_load``
        assert set(labels) == {'mosdir_jw00000_cat', 'mosdir_jw00000_i2d',
                               'mosdir_jw00000_x1d', 'mosdir_jw00001_x1d',
                               'mosdir_jw00000_s2d', 'mosdir_jw00000_s2d (auto-ext)'}

        # the auto-extracted spectrum joins the imported 1D spectra, but isn't visible
        spectrum_1d_menu = self.helper.viewers['1D Spectrum'].data_menu
        assert set(spectrum_1d_menu.data_labels_loaded) == {'mosdir_jw00000_x1d',
                                                            'mosdir_jw00001_x1d',
                                                            'mosdir_jw00000_s2d (auto-ext)'}
        self._assert_visible('1D Spectrum', ['mosdir_jw00000_x1d'])
