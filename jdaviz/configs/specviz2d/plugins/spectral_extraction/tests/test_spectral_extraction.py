import gwcs
import pytest

from astropy.modeling import models
from astropy.nddata import VarianceUncertainty
from astropy.tests.helper import assert_quantity_allclose
import astropy.units as u
from astropy.utils.data import download_file
import numpy as np
from numpy.testing import assert_allclose
from packaging.version import Version
from specreduce import tracing, background, extract
from specutils import Spectrum, SpectralRegion
from glue.core.link_helpers import LinkSameWithUnits
from glue.core.roi import XRangeROI

from jdaviz.core.custom_units_and_equivs import SPEC_PHOTON_FLUX_DENSITY_UNITS
from jdaviz.utils import cached_uri
from jdaviz.core.marks import Lines

GWCS_LT_0_18_1 = Version(gwcs.__version__) < Version('0.18.1')


@pytest.mark.remote_data
@pytest.mark.filterwarnings('ignore')
def test_plugin(specviz2d_helper):
    # TODO: Change back to smaller number (30?) when ITSD is convinced it is them and not us.
    #       Help desk ticket INC0183598, J. Quick.
    fn = download_file('https://stsci.box.com/shared/static/exnkul627fcuhy5akf2gswytud5tazmw.fits',
                       cache=True, timeout=100)

    specviz2d_helper.load_data(spectrum_2d=fn)

    pext = specviz2d_helper.app.get_tray_item_from_name('spectral-extraction-2d')

    # test trace marks - won't be created until after opening the plugin
    sp2dv = specviz2d_helper.app.get_viewer('spectrum-2d-viewer')
    # includes 2 hidden marks from cross-dispersion profile plugin
    assert len(sp2dv.figure.marks) == 5

    pext.keep_active = True
    # includes 2 hidden marks from cross-dispersion profile plugin
    assert len(sp2dv.figure.marks) == 14
    assert pext.marks['trace'].marks_list[0].visible is True
    assert len(pext.marks['trace'].marks_list[0].x) > 0

    # create FlatTrace
    pext.trace_type_selected = 'Flat'
    pext.trace_pixel = 28
    trace = pext.export_trace(add_data=True)
    assert isinstance(trace, tracing.FlatTrace)
    assert trace.trace_pos == 28
    trace.trace_pos = 27
    pext.import_trace(trace)
    assert pext.trace_pixel == 27

    # offset existing trace
    pext.trace_trace_selected = 'trace'
    pext.trace_offset = 2
    trace = pext.export_trace(add_data=True)  # overwrite
    assert isinstance(trace, tracing.FlatTrace)

    # create FitTrace
    pext.trace_trace_selected = 'New Trace'
    pext.trace_type_selected = 'Polynomial'
    trace = pext.export_trace(add_data=True)
    assert isinstance(trace, tracing.FitTrace)
    assert trace.guess == 27
    trace = pext.export_trace(trace_pixel=26, add_data=False)
    assert trace.guess == 26
    trace.guess = 28
    pext.import_trace(trace)
    assert pext.trace_pixel == 28

    # offset existing trace
    pext.trace_trace_selected = 'trace'
    pext.trace_offset = 2
    trace = pext.export_trace(add_data=True)  # overwrite
    assert isinstance(trace, tracing.ArrayTrace)

    # TODO: Investigate extra hidden mark from glue-jupyter, see
    # https://github.com/spacetelescope/jdaviz/pull/2478#issuecomment-1731864411
    # 3 new trace objects should have been loaded and plotted in the spectrum-2d-viewer
    # and there are 2 invisible marks from the cross-dispersion profile plugin
    assert len(sp2dv.figure.marks) in [18, 20]

    # interact with background section, check marks
    pext.trace_trace_selected = 'New Trace'
    pext.trace_type_selected = 'Flat'
    pext.bg_separation = 5
    pext.bg_width = 3
    pext.bg_type_selected = 'TwoSided'
    for mark in ['bg1_center', 'bg2_center']:
        assert pext.marks[mark].marks_list[0].visible is True
        assert len(pext.marks[mark].marks_list[0].x) > 0
    bg = pext.export_bg()
    pext.import_bg(bg)
    assert pext.bg_type_selected == 'TwoSided'

    pext.bg_type_selected = 'Manual'
    assert len(pext.marks['bg1_center'].marks_list[0].x) == 0
    assert len(pext.marks['bg2_center'].marks_list[0].x) == 0
    assert len(pext.marks['bg1_lower'].marks_list[0].x) > 0

    pext.bg_type_selected = 'OneSided'
    # only bg1 is populated for OneSided
    assert len(pext.marks['bg1_center'].marks_list[0].x) > 0
    assert len(pext.marks['bg2_center'].marks_list[0].x) == 0

    # create background image
    pext.bg_separation = 4
    bg = pext.export_bg()
    assert isinstance(bg, background.Background)
    assert len(bg.traces) == 1
    assert bg.traces[0].trace[0] == 28 + 4
    assert bg.width == 3
    bg = pext.export_bg(bg_width=3.3)
    assert bg.width == 3.3
    bg.width = 4
    pext.import_bg(bg)
    assert pext.bg_width == 4
    bg_img = pext.export_bg_img()
    assert isinstance(bg_img, Spectrum)
    bg_spec = pext.export_bg_spectrum()
    assert isinstance(bg_spec, Spectrum)
    bg_sub = pext.export_bg_sub()
    assert isinstance(bg_sub, Spectrum)

    # interact with extraction section, check marks
    pext.ext_width = 1
    for mark in ['bg1_center', 'bg2_center']:
        assert pext.marks[mark].marks_list[0].visible is False
    for mark in ['ext_lower', 'ext_upper']:
        assert pext.marks[mark].marks_list[0].visible is True
        assert len(pext.marks[mark].marks_list[0].x) > 0

    # create subtracted spectrum
    ext = pext.export_extract(ext_width=3)
    assert isinstance(ext, extract.BoxcarExtract)
    assert ext.width == 3
    ext.width = 2
    pext.import_extract(ext)
    assert pext.ext_width == 2
    sp_ext = pext.export_extract_spectrum()
    assert isinstance(sp_ext, Spectrum)

    pext.ext_type_selected = 'Horne'
    sp_ext = pext.export_extract_spectrum()
    assert isinstance(sp_ext, Spectrum)

    # test API calls
    for step in ['trace', 'bg', 'ext']:
        pext.update_marks(step)

    # test exception handling
    pext.trace_type = 'Polynomial'
    pext.bg_type_selected = 'TwoSided'
    pext.bg_separation = 1
    pext.bg_width = 5
    assert len(pext.ext_specreduce_err) > 0
    pext.bg_results_label = 'should not be created'
    pext.vue_create_bg_img()
    assert 'should not be created' not in [d.label for d in specviz2d_helper.app.data_collection]

    with pytest.raises(ValueError):
        pext.export_extract(invalid_kwarg=5)

    # test importing traces
    img = specviz2d_helper.get_data('Spectrum 2D')
    flat_trace = tracing.FlatTrace(img, trace_pos=25)
    fit_trace = tracing.FitTrace(img)

    for imported_trace in [flat_trace, fit_trace]:
        pext.import_trace(imported_trace)
        exported_trace = pext.export_trace(add_data=False)
        assert isinstance(exported_trace, type(imported_trace))

    # array trace needs to go through loader, uncomment after JDAT-5518
    array_trace = tracing.ArrayTrace(img, np.arange(len(img.spectral_axis)))
    specviz2d_helper.load(array_trace, data_label='array_trace')
    pext.trace_trace.selected = 'array_trace'
    exported_trace = pext.export_trace(add_data=False)
    assert isinstance(exported_trace, tracing.ArrayTrace)


@pytest.mark.remote_data
@pytest.mark.filterwarnings('ignore')
def test_user_api(specviz2d_helper):
    fn = download_file('https://stsci.box.com/shared/static/exnkul627fcuhy5akf2gswytud5tazmw.fits', cache=True)  # noqa

    specviz2d_helper.load_data(spectrum_2d=fn)

    pext = specviz2d_helper.plugins['2D Spectral Extraction']
    pext.keep_active = True

    # test that setting a string to an AddResults object redirects to the label
    pext.bg_sub_add_results = 'override label'
    assert pext.bg_sub_add_results.label == 'override label'
    pext.bg_sub_add_results.label = 'override label 2'
    assert "override label 2" in pext.bg_sub_add_results._obj.__repr__()
    assert "override label 2" in pext.bg_sub_add_results._obj.auto_label.__repr__()

    pext.export_bg_sub(add_data=True)
    assert 'override label 2' in pext.ext_dataset.choices

    # test setting auto label
    pext.bg_sub_add_results.auto = True


@pytest.mark.remote_data
@pytest.mark.skipif(GWCS_LT_0_18_1, reason='Needs GWCS 0.18.1 or later')
@pytest.mark.filterwarnings("ignore::astropy.wcs.wcs.FITSFixedWarning")
def test_background_extraction_and_display(specviz2d_helper):
    uri = 'mast:jwst/product/jw01538-o161_t002-s000000001_nirspec_f290lp-g395h-s1600a1_s2d.fits'
    specviz2d_helper.load_data(spectrum_2d=cached_uri(uri), cache=True)
    pext = specviz2d_helper.app.get_tray_item_from_name('spectral-extraction-2d')

    # check that the background extraction method and parameters are as expected
    assert pext.bg_type_selected == 'TwoSided'
    np.testing.assert_allclose(pext.bg_separation, 6)

    # test extracting background and background subtracted images and adding
    # them to the viewer
    pext.export_bg_sub(add_data=True)
    assert specviz2d_helper.app.data_collection[2].label == 'background-subtracted'

    pext.export_bg_img(add_data=True)
    assert specviz2d_helper.app.data_collection[3].label == 'background'


@pytest.mark.filterwarnings('ignore')
def test_horne_extract_self_profile(specviz2d_helper):

    spec2d = np.zeros((40, 100))
    spec2dvar = np.ones((40, 100))

    for ii in range(spec2d.shape[1]):
        mgaus = models.Gaussian1D(amplitude=10,
                                  mean=(9.+(20/spec2d.shape[1])*ii),
                                  stddev=2)
        rg = np.arange(0, spec2d.shape[0], 1)
        gaus = mgaus(rg)
        spec2d[:, ii] = gaus

    wave = np.arange(0, spec2d.shape[1], 1)
    objectspec = Spectrum(spectral_axis=wave*u.m,
                          flux=spec2d*u.Jy,
                          uncertainty=VarianceUncertainty(spec2dvar*u.Jy*u.Jy))

    specviz2d_helper.load(objectspec)
    pext = specviz2d_helper.plugins['2D Spectral Extraction']._obj

    trace_fit = tracing.FitTrace(objectspec,
                                 trace_model=models.Polynomial1D(degree=1),
                                 window=13, peak_method='gaussian', guess=20)
    pext.import_trace(trace_fit)

    pext.ext_type.selected = "Horne"
    pext.horne_ext_profile.selected = "Self (interpolated)"

    # check that correct defaults are set
    assert pext.self_prof_n_bins == 10
    assert pext.self_prof_interp_degree_x == 1
    assert pext.self_prof_interp_degree_y == 1

    sp_ext = pext.export_extract_spectrum()

    bg_sub = pext.export_bg_sub()

    extract_horne_interp = extract.HorneExtract(bg_sub, trace_fit,
                                                spatial_profile='interpolated_profile')

    assert_quantity_allclose(extract_horne_interp.spectrum.flux, sp_ext.flux)

    # now try changing from defaults
    pext.self_prof_n_bins = 5
    pext.self_prof_interp_degree_x = 2
    pext.self_prof_interp_degree_y = 2

    sp_ext = pext.export_extract_spectrum()
    bg_sub = pext.export_bg_sub()

    extract_horne_interp = extract.HorneExtract(bg_sub, trace_fit,
                                                spatial_profile={'name': 'interpolated_profile',
                                                                 'n_bins_interpolated_profile': 5,
                                                                 'interp_degree': (2, 2)})

    assert_quantity_allclose(extract_horne_interp.spectrum.flux, sp_ext.flux)

    # test that correct errors are raised
    pext.self_prof_n_bins = 0
    with pytest.raises(ValueError, match='must be greater than 0'):
        sp_ext = pext.export_extract_spectrum()

    pext.self_prof_n_bins = 1
    pext.self_prof_interp_degree_x = 0
    with pytest.raises(ValueError, match='must be greater than 0'):
        sp_ext = pext.export_extract_spectrum()

    pext.self_prof_interp_degree_x = 1
    pext.self_prof_interp_degree_y = 0
    with pytest.raises(ValueError, match='`self_prof_interp_degree_y` must be greater than 0.'):
        sp_ext = pext.export_extract_spectrum()


def test_spectral_extraction_flux_unit_conversions(specviz2d_helper, mos_spectrum2d):
    specviz2d_helper.load(mos_spectrum2d)

    uc = specviz2d_helper.plugins["Unit Conversion"]
    pext = specviz2d_helper.plugins['2D Spectral Extraction']

    for new_flux_unit in SPEC_PHOTON_FLUX_DENSITY_UNITS:

        # iterate through flux units verifying that selected object/spectrum is obtained using
        # display units
        uc.flux_unit.selected = new_flux_unit

        exported_bg = pext.export_bg()
        assert exported_bg.image._unit == specviz2d_helper.app._get_display_unit('flux')

        exported_bg_img = pext.export_bg_img()
        assert exported_bg_img._unit == specviz2d_helper.app._get_display_unit('flux')

        exported_bg_sub = pext.export_bg_sub()
        assert exported_bg_sub._unit == specviz2d_helper.app._get_display_unit('flux')

        exported_extract_spectrum = pext.export_extract_spectrum()
        assert exported_extract_spectrum._unit == specviz2d_helper.app._get_display_unit('flux')

        exported_extract = pext.export_extract()
        assert exported_extract.image._unit == specviz2d_helper.app._get_display_unit('flux')


@pytest.mark.filterwarnings('ignore')
def test_spectral_extraction_preview(deconfigged_helper, spectrum2d):
    # Multiple 1D viewers is a deconfigged thing so we stick with using
    # that helper throughout.
    deconfigged_helper.load(spectrum2d, format='2D Spectrum')
    # Assume auto extract is on
    default_extraction_label = deconfigged_helper.app.data_collection.labels[1]
    custom_extraction_label = 'custom-extraction'

    # Create a custom extraction and add to a existing viewer
    spext = deconfigged_helper.plugins['2D Spectral Extraction']
    spext.trace_pixel = 2  # to distinguish from auto-extract
    spext.ext_add_results.label = custom_extraction_label
    spext.export_extract_spectrum(add_data=True)  # added as layer to "1D Spectrum" viewer

    default_extraction_data = deconfigged_helper.get_data(default_extraction_label)
    custom_extraction_data = deconfigged_helper.get_data(custom_extraction_label)

    assert np.any(~np.isnan(default_extraction_data.flux))
    assert np.any(~np.isnan(custom_extraction_data.flux))
    # Check that the loaded spectra differ from one another, i.e. that
    # the second spectra is being pulled in correctly.
    assert not np.array_equal(default_extraction_data.flux, custom_extraction_data.flux)

    # Check that both are in the default viewer
    default_viewer = deconfigged_helper.viewers['1D Spectrum']
    default_dm = default_viewer.data_menu
    assert default_extraction_label in default_dm.layer.choices
    assert custom_extraction_label in default_dm.layer.choices

    # Remove layer from default viewer
    default_dm.layer = [custom_extraction_label]
    default_dm.remove_from_viewer()

    # Check that only the default extraction remains in the default viewer
    default_dm = default_viewer.data_menu
    assert default_extraction_label in default_dm.layer.choices
    assert custom_extraction_label not in default_dm.layer.choices

    # and add to a new viewer
    nvc = deconfigged_helper.new_viewers['1D Spectrum']
    nvc.dataset = custom_extraction_label
    nvc.viewer_label = 'manual-viewer'
    new_viewer = nvc()

    # Iterate through both viewers to perform the existence and preview checks.
    # Adds the custom extraction *back* to the default viewer to check
    # that the preview works there as well even after all the moving around.
    for i, viewer in enumerate([new_viewer, default_viewer]):
        dm = viewer.data_menu
        if i == 0:
            # Check that only the custom extraction is in the new viewer
            assert default_extraction_label not in dm.layer.choices
        else:
            # re-add to old viewer and confirm that the preview appears there too
            default_dm.add_data(custom_extraction_label)
            assert default_extraction_label in dm.layer.choices

        assert custom_extraction_label in dm.layer.choices

        # check that the preview lines appear/disappear as expected
        # (as modified from 'test_ramp_extraction.py')
        for interactive_extract in [True, False]:
            with spext.as_active():
                spext.interactive_extract = interactive_extract
                assert len([
                    mark for mark in viewer._obj.custom_marks
                    if mark.visible and isinstance(mark, Lines) and
                       len(mark.x) == len(spectrum2d.spectral_axis)]) == int(interactive_extract)


class TestTwo2dSpectra:

    def load_2d_spectrum(self, helper, spec2d, spec2d_label_idx=0, spec2d_ext_label_idx=1):
        # Allow this to use the default label
        helper.load(spec2d, format='2D Spectrum')
        dc_labels = helper.app.data_collection.labels
        self.spec2d_label = dc_labels[spec2d_label_idx]
        self.spec2d_ext_label = dc_labels[spec2d_ext_label_idx]

    def setup_another_2d_spectrum(self, spec2d):
        # Specific data labels
        another_spec2d_label = 'Another 2D Spectrum'
        another_spec2d_ext_label = 'Another 2D Spectral Extraction'

        # Make the data different enough that extracted spectra should differ
        another_spec2d = Spectrum(flux=spec2d.flux * 2, spectral_axis=spec2d.spectral_axis)

        self.another_spec2d = another_spec2d
        self.another_spec2d_label = another_spec2d_label
        self.another_spec2d_ext_label = another_spec2d_ext_label

    def load_another_2d_spectrum(self, helper, spec2d):
        self.setup_another_2d_spectrum(spec2d)
        helper.load(self.another_spec2d,
                    format='2D Spectrum',
                    data_label=self.another_spec2d_label,
                    ext_data_label=self.another_spec2d_ext_label)

    @pytest.mark.parametrize(('method', 'helper'),
                             [('load', 'deconfigged_helper'),
                              ('specviz2d', 'specviz2d_helper'),
                              ('specviz2d_alternate_order', 'specviz2d_helper'),
                              ('loader_infrastructure', 'deconfigged_helper'),
                              ('loader_infrastructure_alternate_order', 'deconfigged_helper')])
    def test_labels_and_spectral_extraction_flux_difference(self, method, helper, request,
                                                            spectrum2d):
        helper = request.getfixturevalue(helper)
        if method in ('load', 'specviz2d'):
            self.load_2d_spectrum(helper, spectrum2d)
            self.load_another_2d_spectrum(helper, spectrum2d)

        elif method == 'specviz2d_alternate_order':
            self.load_another_2d_spectrum(helper, spectrum2d)
            self.load_2d_spectrum(helper, spectrum2d, spec2d_label_idx=2, spec2d_ext_label_idx=3)

        elif method == 'loader_infrastructure':
            # Allow this to use the default label
            ldr = helper.loaders['object']
            ldr.object = spectrum2d
            ldr.format = '2D Spectrum'
            ldr.importer.auto_extract = True
            ldr.importer()
            self.spec2d_label, self.spec2d_ext_label = helper.app.data_collection.labels[:2]

            self.setup_another_2d_spectrum(spectrum2d)
            ldr.object = self.another_spec2d
            ldr.format = '2D Spectrum'
            ldr.importer.auto_extract = True
            ldr.importer.data_label = self.another_spec2d_label
            ldr.importer.ext_data_label = self.another_spec2d_ext_label
            ldr.importer()

        elif method == 'loader_infrastructure_alternate_order':
            self.setup_another_2d_spectrum(spectrum2d)
            # Swapping the load order changes the parent and
            # the spectral extraction that is duplicated
            ldr = helper.loaders['object']
            ldr.object = self.another_spec2d
            ldr.format = '2D Spectrum'
            ldr.importer.auto_extract = True
            ldr.importer.data_label = self.another_spec2d_label
            ldr.importer.ext_data_label = self.another_spec2d_ext_label
            ldr.importer()

            # Allow this to use the default label
            ldr.object = spectrum2d
            ldr.format = '2D Spectrum'
            ldr.importer.auto_extract = True
            ldr.importer()
            self.spec2d_label, self.spec2d_ext_label = helper.app.data_collection.labels[-2:]

        else:
            raise NotImplementedError(f"Method {method} not implemented.")

        expected_labels = [self.spec2d_label, self.spec2d_ext_label,
                           self.another_spec2d_label, self.another_spec2d_ext_label]

        dc = helper.app.data_collection

        assert self.spec2d_label in dc.labels
        assert self.spec2d_ext_label in dc.labels
        spec2d = helper.get_data(self.spec2d_label)
        extracted_spec2d = helper.get_data(self.spec2d_ext_label)
        # Check for any non-NaN data, if all NaNs, something went wrong
        assert np.any(~np.isnan(spec2d.flux))
        assert np.any(~np.isnan(extracted_spec2d.flux))

        assert self.another_spec2d_label in dc.labels
        assert self.another_spec2d_ext_label in dc.labels
        another_spec2d = helper.get_data(self.another_spec2d_label)
        extracted_another_spec2d = helper.get_data(self.another_spec2d_ext_label)
        # Check for any non-NaN data, if all NaNs, something went wrong
        assert np.any(~np.isnan(another_spec2d.flux))
        assert np.any(~np.isnan(extracted_another_spec2d.flux))

        # Check that the loaded spectra differ from one another, i.e. that
        # the second spectra is being pulled in correctly.
        assert not np.array_equal(spec2d.flux, another_spec2d.flux), \
            'Loaded spectra should differ!'
        assert not np.array_equal(extracted_spec2d.flux, extracted_another_spec2d.flux), \
            'Extracted spectra should differ!'

        # Check linking, e.g.
        # 2D Spectrum (auto-ext) <=> 2D Spectrum [spectral axis]
        # 2D Spectrum (auto-ext) <=> 2D Spectrum [spectral flux density]
        # Another 2D Spectrum <=> 2D Spectrum [spectral axis]
        # Another 2D Spectrum <=> 2D Spectrum [spectral flux density]
        # Another 2D Spectral Extraction <=> 2D Spectrum [spectral axis]
        # Another 2D Spectral Extraction <=> 2D Spectrum
        assert len(dc.external_links) == 9
        for link in dc.external_links:
            # Check that linking is correct by confirming that both
            # are in `expected_labels`
            assert (link.data1.label in expected_labels) and (link.data2.label in expected_labels)
            assert isinstance(link, LinkSameWithUnits)

    def test_subsets_and_viewer_things(self, deconfigged_helper, spectrum2d):
        # Allow this to use the default label
        self.load_2d_spectrum(deconfigged_helper, spectrum2d)
        self.load_another_2d_spectrum(deconfigged_helper, spectrum2d)

        # Test marks/subsets between the two layers
        viewer_2d = deconfigged_helper.app.get_viewer('2D Spectrum')
        viewer_1d = deconfigged_helper.app.get_viewer('1D Spectrum')

        # We'll be panning along x so keep x_min, x_max generic but specify y_min_1d, y_max_1d
        x_min_2d, x_max_2d = viewer_2d.get_limits()[:2]
        midway = (x_min_2d + x_max_2d) / 2

        # Confirm that no subsets are present to start with
        assert not any('subset' in str(layer).lower() for layer in viewer_1d.layers)
        assert not any('subset' in str(layer).lower() for layer in viewer_2d.layers)

        # Following the procedure from ``test_subsets.py``
        # create subset in 2d viewer, want data in 1d viewer
        viewer_2d.apply_roi(XRangeROI(x_min_2d + 0.5 * midway, x_max_2d - 0.5 * midway))
        # Confirm that subsets are present in both viewers
        subset_label = 'Subset 1'
        assert any(subset_label in str(layer) for layer in viewer_1d.layers)
        assert any(subset_label in str(layer) for layer in viewer_2d.layers)

        subset_drawn_2d = viewer_1d.native_marks[-1]
        # get x and y components to compute subset mask
        y1 = subset_drawn_2d.y
        x1 = subset_drawn_2d.x

        subset_highlighted_region1 = x1[np.isfinite(y1)]
        min_value_subset = np.min(subset_highlighted_region1)
        max_value_subset = np.max(subset_highlighted_region1)

        expected_min = 2
        expected_max = 7
        atol = 1e-2
        assert_allclose(min_value_subset, expected_min, atol=atol)
        assert_allclose(max_value_subset, expected_max, atol=atol)

        # now create a subset in the spectrum-viewer, and determine if
        # subset is linked correctly in spectrum2d-viewer
        x_min_reg = x_min_2d + midway
        x_max_reg = x_max_2d - midway
        spec_reg = SpectralRegion(x_min_reg * u.um, x_max_reg * u.um)
        st = deconfigged_helper.plugins['Subset Tools']
        st.import_region(spec_reg, edit_subset=subset_label)

        # Check again
        assert any(subset_label in str(layer) for layer in viewer_1d.layers)
        assert any(subset_label in str(layer) for layer in viewer_2d.layers)

        mask = viewer_2d._get_layer(subset_label)._get_image()

        x_coords = np.nonzero(mask)[1]
        min_value_subset = x_coords.min()
        max_value_subset = x_coords.max()

        assert_allclose(min_value_subset, x_min_reg, atol=atol)
        assert_allclose(max_value_subset, x_max_reg, atol=atol)

        # Now trying through the viewer ROI
        roi = XRangeROI(0, 2)
        viewer_2d.toolbar.active_tool = viewer_2d.toolbar.tools['bqplot:xrange']
        viewer_2d.toolbar.active_tool.activate()
        viewer_2d.toolbar.active_tool.update_from_roi(roi)
        viewer_2d.toolbar.active_tool.update_selection()

        # Check that the subset appears in both viewers
        subset_label = 'Subset 2'
        assert any(subset_label in str(layer) for layer in viewer_1d.layers)
        assert any(subset_label in str(layer) for layer in viewer_2d.layers)

        # Not 100% sure why there is a difference of 1 in the number of marks
        # but leaving this here for posterity.
        assert len(viewer_2d.native_marks) == 7
        assert len(viewer_1d.native_marks) == 6

        # Checking that panning one viewer pans the other
        viewer_2d.toolbar.active_tool = viewer_2d.toolbar.tools['jdaviz:panzoom_matchx']

        # Simulate a pan by changing the x-axis limits
        x_min_1d, x_max_1d, y_min_1d, y_max_1d = viewer_1d.get_limits()
        dx = 1
        # 2D viewer pan
        viewer_2d.set_limits(x_min=x_min_2d+dx, x_max=x_max_2d+dx)
        # Double check that the 2D viewer limits were actually changed
        assert_allclose(viewer_2d.get_limits()[:2], (x_min_2d+dx, x_max_2d+dx))

        # Notify the active tool that the limits have changed (simulate pan event)
        viewer_2d.toolbar.active_tool.on_limits_change()

        # Check that the 1D viewer updated its x-axis limits to match the 2D viewer
        expected = (x_min_1d + dx, x_max_1d + dx, y_min_1d, y_max_1d)
        assert_allclose(viewer_1d.get_limits(), expected)
