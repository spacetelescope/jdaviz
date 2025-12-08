# This file is used to configure the behavior of pytest when using the Astropy
# test infrastructure. It needs to live inside the package in order for it to
# get picked up when running the tests inside an interpreter using
# packagename.test

import os
import psutil
import warnings

import numpy as np
import pytest
from astropy import units as u
from astropy.io import fits
from astropy.nddata import CCDData, StdDevUncertainty
from astropy.table import Table
from astropy.wcs import WCS
from specutils import Spectrum, SpectrumCollection, SpectrumList
from astropy.utils.masked import Masked

from jdaviz import __version__, Cubeviz, Imviz, Mosviz, Specviz, Specviz2d, Rampviz, App
from jdaviz.configs.imviz.tests.utils import (create_wfi_image_model,
                                              _image_hdu_nowcs,
                                              _image_hdu_wcs,
                                              _image_nddata_wcs)
from jdaviz.configs.imviz.plugins.parsers import HAS_ROMAN_DATAMODELS
from jdaviz.utils import NUMPY_LT_2_0
from jdaviz.core.loaders.importers.spectrum_list.spectrum_list import (
    SpectrumListImporter,
    SpectrumListConcatenatedImporter
)
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.template_mixin import PluginTemplateMixin
from jdaviz.core.registries import tray_registry

if not NUMPY_LT_2_0:
    np.set_printoptions(legacy="1.25")

SPECTRUM_SIZE = 10  # length of spectrum


@pytest.fixture
def fake_classes_in_registries():
    """
    This fixture is meant to be used in cases where a test
    needs to check items in the registry. It provides a
    list of fake items in the various registries that could
    potentially throw off those tests if not accounted for.
    """
    return ('Test Fake Plugin',
            'Test Fake 1D Spectrum List',
            'Test Fake 1D Spectrum List Concatenated')


@tray_registry('test-fake-plugin', label='Test Fake Plugin', category='core')
class FakePlugin(PluginTemplateMixin):
    template = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@loader_importer_registry('Test Fake 1D Spectrum List')
class FakeSpectrumListImporter(SpectrumListImporter):
    """A fake importer for testing/convenience purposes only.
    Mostly used to hot-update input for clean code/speed purposes.

    Usage Example:
    x = FakeSpectrumListImporter(app=deconfigged_helper.app,
                                 resolver=deconfigged_helper.loaders['object']._obj,
                                 input=premade_spectrum_list)
    """
    template = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_default_data_label = None

    @property
    def input(self):
        return super().input

    @input.setter
    def input(self, value):
        self._input = value

    @property
    def default_data_label_from_resolver(self):
        if hasattr(self, 'new_default_data_label'):
            return self.new_default_data_label
        return None


@loader_importer_registry('Test Fake 1D Spectrum List Concatenated')
class FakeSpectrumListConcatenatedImporter(SpectrumListConcatenatedImporter):
    """A fake importer for testing/convenience purposes only.
    Mostly used to hot-update input for clean code/speed purposes."""
    template = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_default_data_label = None

    @property
    def input(self):
        return super().input

    @input.setter
    def input(self, value):
        self._input = value

    @property
    def default_data_label_from_resolver(self):
        if hasattr(self, 'new_default_data_label'):
            return self.new_default_data_label
        return None


def _catch_validate_known_exceptions(exceptions_to_catch,
                                     stdout_text_to_check=''):
    """
    Context manager to catch known exceptions in CI tests. Validates the exception
    by checking for specific text in stdout. If matched, the test is skipped. If
    no text is provided, any occurrence of the exception will trigger the skip. If
    the match fails, the exception is re-raised.

    Use as:
    with _catch_known_exception(Exceptions):  # or via fixture catch_known_exceptions
        catalog_plg.search(error_on_fail=True)

    Parameters
    ----------
    exceptions_to_catch : Exception or tuple of Exceptions to catch.
    stdout_text_to_check : str, optional
        Text to match in stdout via substring matching.
        Default is '' (matches any string).
    """
    import contextlib
    import io

    @contextlib.contextmanager
    def _cm():
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                yield buf
        except exceptions_to_catch as etc:
            stdout_text = buf.getvalue()
            if stdout_text_to_check in stdout_text or isinstance(etc, TimeoutError):
                pytest.skip(str(etc))
            else:
                raise

    return _cm()


@pytest.fixture(scope='function')
def catch_validate_known_exceptions():
    """Context manager fixture to catch and validate known exceptions in testing."""
    return _catch_validate_known_exceptions


@pytest.fixture
def cubeviz_helper():
    return Cubeviz()


@pytest.fixture
def imviz_helper():
    return Imviz()


@pytest.fixture
def mosviz_helper():
    return Mosviz()


@pytest.fixture
def specviz_helper():
    return Specviz()


@pytest.fixture
def specviz2d_helper():
    return Specviz2d()


@pytest.fixture
def rampviz_helper():
    return Rampviz()


@pytest.fixture
def deconfigged_helper():
    return App()


@pytest.fixture
def roman_level_1_ramp():
    from roman_datamodels.datamodels import RampModel
    rng = np.random.default_rng(seed=42)

    shape = (10, 25, 25)
    data_model = RampModel.create_fake_data(shape=shape)

    data_model.data = 100 + 3 * np.cumsum(rng.uniform(size=shape), axis=0)
    return data_model


def _make_jwst_ramp(shape=(1, 10, 25, 25)):
    from stdatamodels.jwst.datamodels import Level1bModel

    rng = np.random.default_rng(seed=42)

    # JWST Level 1b ramp files have an additional preceding dimension
    # compared with Roman. This dimension is the integration number
    # in a sequence (if there's more than one in the visit).
    data_model = Level1bModel(shape)
    data_model.data = 100 + 3 * np.cumsum(rng.uniform(size=shape), axis=0)

    return data_model


@pytest.fixture
def jwst_level_1b_ramp():
    return _make_jwst_ramp()


@pytest.fixture
def jwst_level_1b_rectangular_ramp():
    return _make_jwst_ramp(shape=(1, 10, 32, 25))


@pytest.fixture
def jwst_level_2c_rate_image():
    flux_hdu = fits.ImageHDU(np.ones((32, 25)))
    flux_hdu.name = 'FLUX'
    return fits.HDUList([fits.PrimaryHDU(), flux_hdu])


@pytest.fixture
def image_2d_wcs():
    return WCS({'CTYPE1': 'RA---TAN', 'CUNIT1': 'deg', 'CDELT1': -0.0002777777778,
                'CRPIX1': 1, 'CRVAL1': 337.5202808,
                'CTYPE2': 'DEC--TAN', 'CUNIT2': 'deg', 'CDELT2': 0.0002777777778,
                'CRPIX2': 1, 'CRVAL2': -20.833333059999998})


@pytest.fixture
def sky_coord_only_source_catalog():
    """
    Create a sample source catalog with sources positioned within the
    coordinate range of the image_2d_wcs fixture.

    The catalog contains 5 sources spread across a 128x128 pixel image field,
    one roughly in the center and others towards the edges. In addition to RA
    and Dec, the catalog includes magnitude, flux, and a unique source ID.
    """

    # Create the catalog table
    catalog = Table()

    # ra and dec columns, which are required to be loaded as a source catalog
    catalog['ra'] = [337.50293, 337.52763, 337.52844, 337.47438, 337.47432] * u.deg
    catalog['dec'] = [-20.81483, -20.80438, -20.82707, -20.82683, -20.80342] * u.deg

    # additional columns
    catalog['magnitude'] = [12.5, 14.2, 13.8, 15.1, 16.3] * u.mag
    catalog['flux'] = [1.23e-12, 8.45e-13, 9.87e-13, 6.12e-13, 4.33e-13] * u.erg / (u.cm**2 * u.s)
    catalog['source_id'] = ['src_001', 'src_002', 'src_003', 'src_004', 'src_005']

    return catalog


@pytest.fixture
def spectral_cube_wcs():
    # A simple spectral cube WCS used by some tests
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = 'FREQ', 'DEC--TAN', 'RA---TAN'
    wcs.wcs.set()
    return wcs


@pytest.fixture
def image_cube_hdu_obj():
    flux_hdu = fits.ImageHDU(np.ones((10, 10, 10)))
    flux_hdu.name = 'FLUX'

    mask_hdu = fits.ImageHDU(np.zeros((10, 10, 10)))
    mask_hdu.name = 'MASK'

    uncert_hdu = fits.ImageHDU(np.ones((10, 10, 10)))
    uncert_hdu.name = 'ERR'

    wcs = {
        'WCSAXES': 3, 'CRPIX1': 38.0, 'CRPIX2': 38.0, 'CRPIX3': 1.0,
        'PC1_1 ': -0.000138889, 'PC2_2 ': 0.000138889,
        'PC3_3 ': 8.33903304339E-11, 'CDELT1': 1.0, 'CDELT2': 1.0,
        'CDELT3': 1.0, 'CUNIT1': 'deg', 'CUNIT2': 'deg', 'CUNIT3': 'm',
        'CTYPE1': 'RA---TAN', 'CTYPE2': 'DEC--TAN', 'CTYPE3': 'WAVE-LOG',
        'CRVAL1': 205.4384, 'CRVAL2': 27.004754, 'CRVAL3': 3.62159598486E-07,
        'LONPOLE': 180.0, 'LATPOLE': 27.004754, 'MJDREFI': 0.0,
        'MJDREFF': 0.0, 'DATE-OBS': '2014-03-30',
        'RADESYS': 'FK5', 'EQUINOX': 2000.0
    }

    flux_hdu.header.update(wcs)
    flux_hdu.header['BUNIT'] = '1E-17 erg*s^-1*cm^-2*Angstrom^-1'

    uncert_hdu.header['BUNIT'] = '1E-17 erg*s^-1*cm^-2*Angstrom^-1'

    return fits.HDUList([fits.PrimaryHDU(), flux_hdu, uncert_hdu, mask_hdu])


@pytest.fixture
def image_cube_hdu_obj_microns():
    # Basic rectangle ramp for aperture photometry test.
    a = np.zeros((8, 9, 10)).astype(np.float32)  # (nz, ny, nx)
    for i in range(8):
        a[i, :5, :3] = i + 1
    flux_hdu = fits.ImageHDU(a)
    flux_hdu.name = 'FLUX'

    uncert_hdu = fits.ImageHDU(np.zeros((8, 9, 10)).astype(np.float32))
    uncert_hdu.name = 'ERR'

    mask_hdu = fits.ImageHDU(np.ones((8, 9, 10)).astype(np.uint16))
    mask_hdu.name = 'MASK'

    wcs = {
        'WCSAXES': 3, 'CRPIX1': 38.0, 'CRPIX2': 38.0, 'CRPIX3': 1.0,
        'CRVAL1': 205.4384, 'CRVAL2': 27.004754, 'CRVAL3': 4.890499866509344,
        'CTYPE1': 'RA---TAN', 'CTYPE2': 'DEC--TAN', 'CTYPE3': 'WAVE',
        'CUNIT1': 'deg', 'CUNIT2': 'deg', 'CUNIT3': 'um',
        'CDELT1': 3.61111097865634E-05, 'CDELT2': 3.61111097865634E-05, 'CDELT3': 0.001000000047497451,  # noqa
        'PC1_1 ': -1.0, 'PC1_2 ': 0.0, 'PC1_3 ': 0,
        'PC2_1 ': 0.0, 'PC2_2 ': 1.0, 'PC2_3 ': 0,
        'PC3_1 ': 0, 'PC3_2 ': 0, 'PC3_3 ': 1,
        'DISPAXIS': 2, 'VELOSYS': -2538.02,
        'SPECSYS': 'BARYCENT', 'RADESYS': 'ICRS', 'EQUINOX': 2000.0,
        'LONPOLE': 180.0, 'LATPOLE': 27.004754,
        'MJDREFI': 0.0, 'MJDREFF': 0.0, 'DATE-OBS': '2014-03-30'}

    flux_hdu.header.update(wcs)
    flux_hdu.header['BUNIT'] = '1E-17 erg*s^-1*cm^-2*Angstrom^-1'

    uncert_hdu.header['BUNIT'] = '1E-17 erg*s^-1*cm^-2*Angstrom^-1'

    return fits.HDUList([fits.PrimaryHDU(), flux_hdu, uncert_hdu, mask_hdu])


@pytest.fixture
def spectrum1d_cube_wcs():
    # A simple spectrum1D WCS used by some tests
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = 'WAVE-LOG', 'DEC--TAN', 'RA---TAN'
    wcs.wcs.set()
    return wcs


def _create_spectrum1d_with_spectral_unit(spectralunit=u.AA, spectral_mask=None, wfss=False,
                                          exposure='0_0_0_1', source_id='0000', seed=42):
    np.random.seed(seed)

    if spectral_mask is None:
        spectral_mask = np.array([False] * SPECTRUM_SIZE)

    # We make this first so we don't have to worry about inputting different bounds
    spec_axis = Masked(np.linspace(6000, 8000, SPECTRUM_SIZE) * u.AA,
                       mask=spectral_mask)
    if spectralunit != u.AA:
        spec_axis = spec_axis.to(spectralunit)

    flux = (np.random.randn(len(spec_axis.value)) +
            10*np.exp(-0.001*(spec_axis.value-6563)**2) +
            spec_axis.value/500) * u.Jy

    uncertainty = StdDevUncertainty(np.abs(np.random.randn(len(spec_axis.value))) * u.Jy)

    meta = dict(header=dict(FILENAME="jdaviz-test-file.fits"))
    if wfss:
        meta['header'].update(dict(DATAMODL='WFSSMulti', EXPGRPID=exposure))
        meta.update(dict(source_id=source_id))

    # Note, an INFO message pops up informing the user
    # 'overwriting Masked Quantity's current mask with specified mask. [astropy.nddata.nddata]'
    # This is expected behavior albeit a nuisance. Is it possible to suppress this message?
    return Spectrum(spectral_axis=spec_axis, flux=flux, uncertainty=uncertainty,
                    mask=spectral_mask, meta=meta)


@pytest.fixture
def make_empty_spectrum():
    return Spectrum(spectral_axis=np.array([]) * u.Hz,
                    flux=np.array([]) * u.Jy,
                    uncertainty=StdDevUncertainty(np.array([])),
                    mask=np.array([]),
                    meta={})


@pytest.fixture
def spectrum1d():
    return _create_spectrum1d_with_spectral_unit()


@pytest.fixture
def partially_masked_spectrum1d():
    mask = np.array([False] * SPECTRUM_SIZE)
    mask[-3:] = True
    return _create_spectrum1d_with_spectral_unit(spectral_mask=mask)


@pytest.fixture
def wfss_spectrum1d():
    return _create_spectrum1d_with_spectral_unit(wfss=True)


# WFSS may have spectral axes that are partially masked
# and this is not allowed in specutils
@pytest.fixture
def partially_masked_wfss_spectrum1d():
    mask = np.array([False] * SPECTRUM_SIZE)
    mask[-3:] = True
    return _create_spectrum1d_with_spectral_unit(spectral_mask=mask, wfss=True, source_id='1111')


@pytest.fixture
def partially_masked_wfss_spectrum1d_exp1():
    mask = np.array([False] * SPECTRUM_SIZE)
    mask[-3:] = True
    return _create_spectrum1d_with_spectral_unit(spectral_mask=mask, wfss=True,
                                                 exposure='1_1_1', source_id='1111')


@pytest.fixture
def spectrum1d_nm():
    return _create_spectrum1d_with_spectral_unit(u.nm)


@pytest.fixture
def spectrum_collection(spectrum1d):
    sc = [spectrum1d] * 5

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        result = SpectrumCollection.from_spectra(sc)
    return result


@pytest.fixture
def premade_spectrum_list(spectrum1d, partially_masked_spectrum1d,
                          wfss_spectrum1d, partially_masked_wfss_spectrum1d,
                          partially_masked_wfss_spectrum1d_exp1):
    return SpectrumList([
        spectrum1d,
        partially_masked_spectrum1d,
        wfss_spectrum1d,
        partially_masked_wfss_spectrum1d,
        partially_masked_wfss_spectrum1d_exp1])


@pytest.fixture
def multi_order_spectrum_list(spectrum1d, spectral_orders=10):
    sc = []
    np.random.seed(42)

    for i in range(spectral_orders):

        spec_axis = (np.arange(SPECTRUM_SIZE) + 6000 + i * SPECTRUM_SIZE) * u.AA
        flux = (np.random.randn(len(spec_axis.value)) +
                10 * np.exp(-0.002 * (spec_axis.value - 6563) ** 2) +
                spec_axis.value / 500) * u.Jy
        uncertainty = StdDevUncertainty(np.abs(np.random.randn(len(spec_axis.value))) * u.Jy)
        meta = dict(header=dict(FILENAME="jdaviz-test-multi-order-file.fits"))
        spectrum1d = Spectrum(spectral_axis=spec_axis, flux=flux,
                              uncertainty=uncertainty, meta=meta)

        sc.append(spectrum1d)

    return SpectrumList(sc)


def _create_spectrum1d_cube_with_fluxunit(fluxunit=u.Jy, shape=(2, 2, 4), with_uncerts=False):
    # nz=2 nx=2 ny=4
    flux = np.arange(np.prod(shape)).reshape(shape) * fluxunit
    wcs_dict = {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CTYPE3": "WAVE-LOG",
                "CRVAL1": 205, "CRVAL2": 27, "CRVAL3": 4.622e-7,
                "CDELT1": -0.0001, "CDELT2": 0.0001, "CDELT3": 8e-11,
                "CRPIX1": 0, "CRPIX2": 0, "CRPIX3": 0, "PIXAR_SR": 10.,
                # Need these for aperture photometry test.
                "TELESCOP": "JWST", "BUNIT": fluxunit.to_string(), "PIXAR_A2": 0.01}
    w = WCS(wcs_dict)
    if with_uncerts:
        uncert = StdDevUncertainty(np.abs(np.random.normal(flux) * fluxunit))

        return Spectrum(flux=flux,
                        uncertainty=uncert,
                        wcs=w,
                        meta=wcs_dict)
    else:
        return Spectrum(flux=flux, wcs=w, meta=wcs_dict)


@pytest.fixture
def spectrum1d_cube():
    return _create_spectrum1d_cube_with_fluxunit(fluxunit=u.Jy)


@pytest.fixture
def spectrum1d_cube_with_uncerts():
    return _create_spectrum1d_cube_with_fluxunit(fluxunit=u.Jy, with_uncerts=True)


@pytest.fixture
def spectrum1d_cube_larger():
    return _create_spectrum1d_cube_with_fluxunit(fluxunit=u.Jy, shape=(SPECTRUM_SIZE, 2, 4))


@pytest.fixture
def spectrum1d_cube_largest():
    wcs_dict = {"CTYPE1": "WAVE-LOG", "CTYPE2": "DEC--TAN", "CTYPE3": "RA---TAN",
                "CRVAL1": 4.622e-7, "CRVAL2": 27, "CRVAL3": 205,
                "CDELT1": 8e-11, "CDELT2": 0.0001, "CDELT3": -0.0001,
                "CRPIX1": 0, "CRPIX2": 0, "CRPIX3": 0}
    w = WCS(wcs_dict)
    flux = np.zeros((20, 30, 3001), dtype=np.float32)  # nx=20 ny=30 nz=3001
    flux[1:11, 5:15, :] = 1  # Bright corner
    return Spectrum(flux=flux * u.Jy, wcs=w, meta=wcs_dict)


@pytest.fixture
def spectrum1d_cube_custom_fluxunit():
    return _create_spectrum1d_cube_with_fluxunit


@pytest.fixture
def spectrum1d_cube_fluxunit_jy_per_steradian():
    return _create_spectrum1d_cube_with_fluxunit(fluxunit=u.Jy/u.sr, shape=(10, 4, 5),
                                                 with_uncerts=True)


@pytest.fixture
def spectrum1d_cube_sb_unit():
    # similar fixture to spectrum1d_cube_fluxunit_jy_per_steradian, but no uncerts
    # and different shape. can probably remove one of these eventually
    return _create_spectrum1d_cube_with_fluxunit(fluxunit=u.Jy / u.sr)


@pytest.fixture
def mos_spectrum1d(mos_spectrum2d):
    '''
    A specially defined Spectrum1d that matches the corresponding spectrum2d below.

    TODO: this fixture should be replaced by the global spectrum1d fixture defined in
    jdaviz/conftest.py AFTER reforming the spectrum2d fixture below to match the
    global spectrum1d fixture.

    Unless linking the two is required, try to use the global spectrum1d fixture.
    '''
    spec_axis = mos_spectrum2d.spectral_axis
    np.random.seed(42)
    flux = (np.random.randn(len(spec_axis.value)) +
            10*np.exp(-0.001*(spec_axis.value-6563)**2) +
            spec_axis.value/500) * u.Jy

    return Spectrum(spectral_axis=spec_axis, flux=flux)


@pytest.fixture
def spectrum2d():
    '''
    A simple 2D Spectrum with a center "trace" array rising from 0 to 10
    with two "zero array" buffers above and below
    '''
    data = np.zeros((5, 10))
    data[3] = np.arange(10)

    return Spectrum(flux=data*u.MJy, spectral_axis=data[3]*u.um)


def _generate_mos_spectrum2d():
    header = {
        'WCSAXES': 2,
        'CRPIX1': 0.0, 'CRPIX2': 1024.5,
        'CDELT1': 1E-06, 'CDELT2': 2.9256727777778E-05,
        'CUNIT1': 'm', 'CUNIT2': 'deg',
        'CTYPE1': 'WAVE', 'CTYPE2': 'OFFSET',
        'CRVAL1': 0.0, 'CRVAL2': 5.0,
        'RADESYS': 'ICRS', 'SPECSYS': 'BARYCENT'}
    np.random.seed(42)
    data = np.random.sample((15, 1024)) * u.Jy
    return data, header


@pytest.fixture
def mos_spectrum2d():
    '''
    A specially defined 2D (spatial) Spectrum whose wavelength range matches the
    mos-specific 1D spectrum.

    TODO: This should be reformed to match the global Spectrum defined above so that we may
    deprecate the mos-specific spectrum1d.
    '''
    data, header = _generate_mos_spectrum2d()
    wcs = WCS(header)
    return Spectrum(data, wcs=wcs, meta=header)


@pytest.fixture
def mos_spectrum2d_as_hdulist():
    data, header = _generate_mos_spectrum2d()
    hdu = fits.ImageHDU(data.value)
    hdu.header.update(header)

    # This layout is to trick specutils to think it is JWST s2d
    hdulist = fits.HDUList([fits.PrimaryHDU(), hdu, hdu])
    hdulist[0].header["TELESCOP"] = "JWST"
    hdulist[1].name = "SCI"
    hdulist[1].ver = 1
    hdulist[2].name = "SCI"
    hdulist[2].ver = 2

    return hdulist


@pytest.fixture
def mos_image():
    header = {
        'WCSAXES': 2,
        'CRPIX1': 937.0, 'CRPIX2': 696.0,
        'CDELT1': -1.5182221158397e-05, 'CDELT2': 1.5182221158397e-05,
        'CUNIT1': 'deg', 'CUNIT2': 'deg',
        'CTYPE1': 'RA---TAN', 'CTYPE2': 'DEC--TAN',
        'CRVAL1': 5.0155198140981, 'CRVAL2': 5.002450989248,
        'LONPOLE': 180.0, 'LATPOLE': 5.002450989248,
        'DATEREF': '1858-11-17', 'MJDREFI': 0.0, 'MJDREFF': 0.0,
        'RADESYS': 'ICRS'}
    wcs = WCS(header)
    np.random.seed(42)
    data = np.random.sample((55, 55))
    return CCDData(data, wcs=wcs, unit='Jy', meta=header)


@pytest.fixture
def roman_imagemodel():
    if HAS_ROMAN_DATAMODELS:
        return create_wfi_image_model((20, 10))


@pytest.fixture
def image_hdu_nowcs():
    return _image_hdu_nowcs()


@pytest.fixture
def image_hdu_wcs():
    return _image_hdu_wcs()


@pytest.fixture
def multi_extension_image_hdu_wcs():
    return fits.HDUList([fits.PrimaryHDU(),
                         _image_hdu_wcs(),
                         _image_hdu_nowcs(np.zeros((10, 10)), name='MASK'),
                         _image_hdu_nowcs(name='ERR'),
                         _image_hdu_nowcs(name='DQ')])


@pytest.fixture
def image_nddata_wcs():
    return _image_nddata_wcs()


# Copied over from https://github.com/spacetelescope/ci_watson
@pytest.fixture(scope='function')
def _jail(tmp_path):
    """Perform test in a pristine temporary working directory."""
    old_dir = os.getcwd()
    os.chdir(tmp_path)
    try:
        yield str(tmp_path)
    finally:
        os.chdir(old_dir)


try:
    from pytest_astropy_header.display import PYTEST_HEADER_MODULES, TESTED_VERSIONS
except ImportError:
    PYTEST_HEADER_MODULES = {}
    TESTED_VERSIONS = {}

# ============================================================================
# Memory logging plugin (memlog) - log per-test memory usage
# ============================================================================

# Module-level storage for memlog
_memlog_records = []
_memlog_enabled_flag = False


def _get_memory_bytes():
    """
    Return the current process resident set size (RSS) in bytes.

    Uses psutil if available, otherwise falls back to resource.
    """
    return psutil.Process().memory_info().rss


def _format_bytes(b):
    """
    Format byte count as human-readable string with MiB unit.
    """
    mib = b / (1024.0 * 1024.0)
    return f'{mib:7.2f} MiB'


def _format_memlog_line(record, include_worker=False):
    """
    Format a memlog record as a display line.

    Parameters
    ----------
    record : dict
        A memlog record with 'mem_diff', 'mem_before', 'mem_after',
        'worker_id', and 'nodeid' keys.
    include_worker : bool
        If True, include the worker ID in the output.

    Returns
    -------
    str
        Formatted line for display.
    """
    diff = record['mem_diff'] or 0
    before = record['mem_before'] or 0
    after = record['mem_after'] or 0

    if include_worker:
        worker = record.get('worker_id') or 'master'
        return (
            f'{_format_bytes(diff):>10}  '
            f'{_format_bytes(before):>10}  '
            f'{_format_bytes(after):>10}  '
            f'{worker:>8}  {record["nodeid"]}'
        )
    else:
        return (
            f'{_format_bytes(diff):>10}  '
            f'{_format_bytes(before):>10}  '
            f'{_format_bytes(after):>10}  {record["nodeid"]}'
        )


def _parse_worker_id(worker_id):
    """
    Parse worker_id into a sortable tuple.

    For xdist worker IDs like 'gw0', 'gw1', etc., returns
    (prefix, number). For 'master', returns ('~', 0) to sort
    last. Ensures numerical ordering within each prefix.

    Parameters
    ----------
    worker_id : str
        The worker ID string to parse.

    Returns
    -------
    tuple
        A (prefix, number) tuple suitable for sorting.
    """
    import re

    if worker_id == 'master':
        return ('~', 0)
    match = re.match(r'([a-z]+)(\d+)', worker_id)
    if match:
        prefix, number = match.groups()
        return (prefix, int(number))
    return (worker_id, 0)


def pytest_addoption(parser):
    """
    Register pytest options including memlog options.
    """
    # Memlog options
    group = parser.getgroup('memlog')
    group.addoption(
        '--memlog',
        action='store',
        dest='memlog',
        default='10',
        help='Enable per-test memory logging and summary. Default: 10'
    )

    group.addoption(
        '--memlog-sort',
        action='store',
        dest='memlog_sort',
        default='diff',
        help='Enable sorting of memory results. Default: diff\n'
             'diff   - Sort by memory allocation difference.\n'
             'before - Sort by highest memory before test.\n'
             'after  - Sort by highest memory after test.\n'
             'peak   - Sort by highest peak memory allocation.\n'
             'seq    - Sort by test output order '
             '(can help determine sustained memory allocation).\n'
             'worker - Group by worker ID, then sort by peak memory '
             'which can serve as a proxy for in-node sequential memory allocation '
             '(xdist only).\n'
    )

    group.addoption(
        '--memlog-max-worker',
        action='store_true',
        dest='memlog_max_worker',
        default=False,
        help='Show memory report for the worker with highest peak memory allocation (xdist only).'
    )


def pytest_runtest_setup(item):
    """
    Setup hook that records memory before test.
    """
    if not _memlog_enabled_flag:
        return
    mem = _get_memory_bytes()
    item._mem_before = mem


def pytest_runtest_teardown(item, nextitem):
    """
    Teardown hook that records memory after test.
    """
    if not _memlog_enabled_flag:
        return
    mem = _get_memory_bytes()
    item._mem_after = mem


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook wrapper to attach memory measurements to report user_properties.

    This runs during report creation when we still have access to the item.
    The user_properties are serialized and sent to master in xdist.
    """
    outcome = yield
    report = outcome.get_result()

    if call.when != 'teardown':
        return

    if not _memlog_enabled_flag:
        return

    mem_before = getattr(item, '_mem_before', None)
    mem_after = getattr(item, '_mem_after', None)

    if mem_before is None or mem_after is None:
        return

    diff = int(mem_after) - int(mem_before)

    # Get worker_id from config (xdist sets this)
    worker_id = getattr(item.config, 'workerinput', {}).get('workerid', 'master')

    # Attach to user_properties - these get serialized to master in xdist
    report.user_properties.append(('mem_before', int(mem_before)))
    report.user_properties.append(('mem_after', int(mem_after)))
    report.user_properties.append(('mem_diff', int(diff)))
    report.user_properties.append(('worker_id', worker_id))


def _extract_memlog_properties(props):
    """
    Extract memory properties from user_properties list.

    Parameters
    ----------
    props : list
        List of (name, value) tuples from report.user_properties.

    Returns
    -------
    dict or None
        Dictionary with 'mem_before', 'mem_after', 'mem_diff', and
        'worker_id' keys, or None if no memory data found.
    """
    mem_before = None
    mem_after = None
    mem_diff = None
    worker_id = None

    for name, value in props:
        if name == 'mem_before':
            mem_before = int(value)
        elif name == 'mem_after':
            mem_after = int(value)
        elif name == 'mem_diff':
            mem_diff = int(value)
        elif name == 'worker_id':
            worker_id = value

    # Return None if no memory data found
    if mem_before is None and mem_after is None and mem_diff is None:
        return None

    return {
        'mem_before': mem_before,
        'mem_after': mem_after,
        'mem_diff': mem_diff,
        'worker_id': worker_id
    }


def pytest_runtest_logreport(report):
    """
    Log report hook that collects memory measurements from user_properties.

    This runs on both workers and master. On master (xdist), it receives
    the serialized user_properties from workers.
    """
    if report.when != 'teardown':
        return

    props = getattr(report, 'user_properties', [])

    if not props:
        return

    mem_props = _extract_memlog_properties(props)
    if mem_props is None:
        return

    _memlog_records.append({
        'nodeid': getattr(report, 'nodeid', '<unknown>'),
        'worker_id': mem_props['worker_id'],
        'when': report.when,
        'mem_before': mem_props['mem_before'],
        'mem_after': mem_props['mem_after'],
        'mem_diff': mem_props['mem_diff']
    })


def _apply_memlog_sort(records, sort_method, top_n):
    """
    Apply sorting to memlog records based on sort_method.

    Parameters
    ----------
    records : list
        List of memlog record dictionaries.
    sort_method : str
        Sorting method: 'diff', 'before', 'after', 'peak', or 'seq'.
    top_n : int
        Number of top records to return.

    Returns
    -------
    list
        Sorted records, limited to top_n items.
    """
    if sort_method == 'diff':
        records.sort(key=lambda r: r['mem_diff'], reverse=True)

    elif sort_method == 'before':
        records.sort(key=lambda r: max(r['mem_before']), reverse=True)

    elif sort_method == 'after':
        records.sort(key=lambda r: max(r['mem_after']), reverse=True)

    elif sort_method == 'peak':
        records.sort(key=lambda r: max(r['mem_before'], r['mem_after']), reverse=True)

    elif sort_method == 'seq':
        records = records[::-1]  # Keep original order but reverse for display purposes

    return records[:top_n]


def pytest_terminal_summary(terminalreporter, config=None):
    """
    Terminal summary hook that prints memlog summary.
    """
    if config is None:
        config = terminalreporter.config

    if not getattr(config, '_memlog_enabled', False):
        return

    if not _memlog_records:
        terminalreporter.write_line('memlog: no records collected.')
        return

    top_n = getattr(config, '_memlog_top', 10)
    records = [r for r in _memlog_records if r.get('mem_diff') is not None]

    sort_method = getattr(config, '_memlog_sort', 'diff')

    # If max worker is requested, find and report on the worker with
    # highest peak memory allocation
    if getattr(config, '_memlog_max_worker', False):
        # Find the worker with the highest peak memory across all tests
        max_worker = None
        max_peak = -1

        for r in records:
            worker_id = r.get('worker_id') or 'master'
            peak = max(r['mem_before'], r['mem_after'])
            if peak > max_peak:
                max_peak = peak
                max_worker = worker_id

        if max_worker is None:
            terminalreporter.write_line('memlog: no worker found with memory data.')
            return

        # Filter to only this worker's records
        worker_records = [r for r in records if (r.get('worker_id') or 'master') == max_worker]

        # Apply the selected sort method to worker records
        worker_records = _apply_memlog_sort(worker_records, 'seq', top_n)

        title = (f'Top {top_n} tests for worker {max_worker} '
                 f'(highest peak memory: {_format_bytes(max_peak)})')
        terminalreporter.write_sep('-', title)

        header = f'{"mem diff":>10}  {"before":>10}  {"after":>10}  test'
        terminalreporter.write_line(header)

        for r in worker_records:
            terminalreporter.write_line(_format_memlog_line(r))

        terminalreporter.write_sep('-', 'end of memlog summary')

        return

    # Group by worker_id if sorting by worker
    if sort_method == 'worker':
        from itertools import groupby

        # Sort records by worker_id first (with numerical sorting)
        records.sort(key=lambda r: _parse_worker_id(r.get('worker_id') or 'master'))

        # Group by worker_id
        grouped = {}
        for worker_id, group_records in groupby(
                records, key=lambda r: r.get('worker_id') or 'master'
        ):
            # Within each worker, sort by sequential order
            grouped[worker_id] = _apply_memlog_sort(list(group_records), 'seq', top_n)

        # Display results grouped by worker
        title = f'Top {top_n} tests by worker, sorted by peak memory'
        terminalreporter.write_sep('-', title)

        header = (f'{"mem diff":>10}  {"before":>10}  {"after":>10}  '
                  f'{"worker":>8}  test')

        # Sort worker_ids numerically for display
        sorted_worker_ids = sorted(grouped.keys(), key=_parse_worker_id)

        for worker_id in sorted_worker_ids:
            terminalreporter.write_line(f'\nWorker: {worker_id}')
            terminalreporter.write_line(header)

            for r in grouped[worker_id][:top_n]:
                terminalreporter.write_line(_format_memlog_line(r, include_worker=True))
    else:
        # Apply the selected sort method to all records
        records = _apply_memlog_sort(records, sort_method, top_n)

        title = f'Top {top_n} tests by memory difference'
        terminalreporter.write_sep('-', title)

        header = (f'{"mem diff":>10}  {"before":>10}  {"after":>10}  '
                  f'{"worker":>8}  test')
        terminalreporter.write_line(header)

        for r in records:
            terminalreporter.write_line(_format_memlog_line(r, include_worker=True))

    terminalreporter.write_sep('-', 'end of memlog summary')


def pytest_configure(config):
    """
    Configure pytest, including memlog initialization.
    """
    global _memlog_enabled_flag

    # Initialize memlog
    if len(config.getoption('memlog')) > 0:
        config._memlog_top = int(config.getoption('memlog'))
        config._memlog_sort = config.getoption('memlog_sort')
        config._memlog_max_worker = config.getoption('memlog_max_worker')
        _memlog_enabled_flag = True
        config._memlog_enabled = True

    PYTEST_HEADER_MODULES['astropy'] = 'astropy'
    PYTEST_HEADER_MODULES['pyyaml'] = 'yaml'
    PYTEST_HEADER_MODULES['scikit-image'] = 'skimage'
    PYTEST_HEADER_MODULES['specutils'] = 'specutils'
    PYTEST_HEADER_MODULES['specreduce'] = 'specreduce'
    PYTEST_HEADER_MODULES['asteval'] = 'asteval'
    PYTEST_HEADER_MODULES['echo'] = 'echo'
    PYTEST_HEADER_MODULES['idna'] = 'idna'
    PYTEST_HEADER_MODULES['traitlets'] = 'traitlets'
    PYTEST_HEADER_MODULES['bqplot'] = 'bqplot'
    PYTEST_HEADER_MODULES['bqplot-image-gl'] = 'bqplot_image_gl'
    PYTEST_HEADER_MODULES['glue-core'] = 'glue'
    PYTEST_HEADER_MODULES['glue-jupyter'] = 'glue_jupyter'
    PYTEST_HEADER_MODULES['glue-astronomy'] = 'glue_astronomy'
    PYTEST_HEADER_MODULES['ipyvue'] = 'ipyvue'
    PYTEST_HEADER_MODULES['ipyvuetify'] = 'ipyvuetify'
    PYTEST_HEADER_MODULES['ipysplitpanes'] = 'ipysplitpanes'
    PYTEST_HEADER_MODULES['ipygoldenlayout'] = 'ipygoldenlayout'
    PYTEST_HEADER_MODULES['ipypopout'] = 'ipypopout'
    PYTEST_HEADER_MODULES['solara'] = 'solara'
    PYTEST_HEADER_MODULES['vispy'] = 'vispy'
    PYTEST_HEADER_MODULES['gwcs'] = 'gwcs'
    PYTEST_HEADER_MODULES['asdf'] = 'asdf'
    PYTEST_HEADER_MODULES['stdatamodels'] = 'stdatamodels'
    PYTEST_HEADER_MODULES['roman_datamodels'] = 'roman_datamodels'

    TESTED_VERSIONS['jdaviz'] = __version__
