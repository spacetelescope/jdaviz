"""
Tests for the parsers module.
"""
from collections import defaultdict
import re

import numpy as np
import pytest
from astropy import units as u
from astropy.nddata import StdDevUncertainty
from glue.core import Data
from specutils import Spectrum, SpectrumList

from jdaviz.configs.specviz.plugins.parsers import (
    specviz_spectrum1d_parser,
    group_spectra_by_filename,
    combine_lists_to_1d_spectrum,
    split_spectrum_with_2D_flux_array
)


class TestSpecvizSpectrum1DParser:
    """
    Test the main specviz_spectrum1d_parser function.
    """
    @pytest.mark.parametrize('label', [None, 'custom_label'])
    def test_parse_single_spectrum1d(self, specviz_helper, spectrum1d, label):
        """
        Test parsing a single Spectrum1D object.
        """
        specviz_spectrum1d_parser(specviz_helper.app, spectrum1d, data_label=label)

        assert len(specviz_helper.app.data_collection) == 1
        if label:
            assert specviz_helper.app.data_collection[0].label == label
        else:
            assert specviz_helper.app.data_collection[0].label == 'Spectrum'

    def test_parse_spectrum_list(self, specviz_helper, premade_spectrum_list):
        """
        Test parsing a SpectrumList.
        """
        specviz_spectrum1d_parser(specviz_helper.app,
                                  premade_spectrum_list,
                                  data_label=[f"spec{i}_label"
                                              for i in range(len(premade_spectrum_list))])

        assert len(specviz_helper.app.data_collection) == len(premade_spectrum_list)
        for i, data in enumerate(specviz_helper.app.data_collection):
            assert data.label == f"spec{i}_label"

    def test_parse_2d_flux_spectrum(self, specviz_helper, spectrum2d):
        """
        Test that 2D flux spectra are split automatically.
        """
        specviz_spectrum1d_parser(specviz_helper.app, spectrum2d, data_label='spec2d_label')

        assert len(specviz_helper.app.data_collection) == np.shape(spectrum2d)[0]
        for i, data in enumerate(specviz_helper.app.data_collection):
            assert data.label == f"spec2d_label [{i}]"

    def test_parse_spectrum_collection(self, specviz_helper, spectrum_collection):
        """
        Test parsing a SpectrumCollection.
        """
        msg = 'SpectrumCollection detected. Please provide a Spectrum or SpectrumList'
        with pytest.raises(TypeError, match=msg):
            specviz_spectrum1d_parser(specviz_helper.app, spectrum_collection)

    def test_parse_mismatched_label_length(self, specviz_helper, premade_spectrum_list):
        """
        Test error when label list length doesn't match data length.
        """
        msg = "Length of data labels list (1) is different than length of list of data (5)"
        with pytest.raises(ValueError, match=re.escape(msg)):
            specviz_spectrum1d_parser(specviz_helper.app,
                                      premade_spectrum_list,
                                      data_label=['oops'])

    def test_parse_concat_by_file(self, specviz_helper):
        """
        Test the concat_by_file functionality.
        """
        spec1 = Spectrum(
            spectral_axis=np.linspace(5000, 5500, 50) * u.AA,
            flux=np.random.random(50) * u.Jy,
            meta={'header': {'FILENAME': 'same_file.fits'}}
        )
        spec2 = Spectrum(
            spectral_axis=np.linspace(5500, 6000, 50) * u.AA,
            flux=np.random.random(50) * u.Jy,
            meta={'header': {'FILENAME': 'same_file.fits'}}
        )
        spec_list = SpectrumList([spec1, spec2])

        specviz_spectrum1d_parser(specviz_helper.app,
                                  spec_list,
                                  data_label='test_concat',
                                  concat_by_file=True)

        # Should have 2 individual spectra + 1 combined
        assert len(specviz_helper.app.data_collection) == 3
        labels = [
            d.label for d in specviz_helper.app.data_collection
        ]
        assert any('Combined' in label for label in labels)

    def test_parse_file_path(self, specviz_helper, tmp_path):
        """
        Test parsing from a file path.
        """
        spec = Spectrum(
            spectral_axis=np.linspace(5000, 6000, 100) * u.AA,
            flux=np.random.random(100) * u.Jy,
            uncertainty=StdDevUncertainty(
                np.random.random(100) * 0.1 * u.Jy
            )
        )

        filepath = tmp_path / 'test_spectrum.fits'
        spec.write(str(filepath), overwrite=True)

        specviz_spectrum1d_parser(specviz_helper.app,
                                  str(filepath),
                                  data_label='test_filepath')

        assert len(specviz_helper.app.data_collection) == 1

    def test_parse_metadata_standardization(self, specviz_helper):
        """
        Test that metadata is standardized.
        """
        spec = Spectrum(
            spectral_axis=np.linspace(5000, 6000, 50) * u.AA,
            flux=np.random.random(50) * u.Jy,
            meta={'TELESCOPE': 'TEST', 'INSTRUMENT': 'FAKE'}
        )

        specviz_spectrum1d_parser(specviz_helper.app, spec, data_label='test_meta')

        loaded_spec = specviz_helper.get_data('test_meta')
        assert 'TELESCOPE' in loaded_spec.meta

    def test_parse_show_in_viewer_false(self, specviz_helper, spectrum1d):
        """
        Test that show_in_viewer=False doesn't add to viewer.
        """
        specviz_spectrum1d_parser(specviz_helper.app,
                                  spectrum1d,
                                  data_label='hidden_spec',
                                  show_in_viewer=False)

        assert len(specviz_helper.app.data_collection) == 1

        viewer = specviz_helper.app.get_viewer(
            specviz_helper._default_spectrum_viewer_reference_name
        )
        # Check that no data is shown in viewer
        assert len(viewer.data()) == 0


class TestGroupSpectraByFilename:
    """
    Test the group_spectra_by_filename function.
    """
    def test_group_single_filename(self):
        """
        Test grouping when all spectra have the same filename.
        """
        data1 = Data(label='spec1')
        data1.meta = {'FILENAME': 'test_file.fits'}
        data2 = Data(label='spec2')
        data2.meta = {'FILENAME': 'test_file.fits'}
        data3 = Data(label='spec3')
        data3.meta = {'FILENAME': 'test_file.fits'}

        datasets = [data1, data2, data3]

        result = group_spectra_by_filename(datasets)

        assert 'test_file.fits' in result
        assert len(result['test_file.fits']) == 3

    def test_group_multiple_filenames(self):
        """
        Test grouping when spectra come from different files.
        """
        data1 = Data(label='spec1')
        data1.meta = {'FILENAME': 'file1.fits'}
        data2 = Data(label='spec2')
        data2.meta = {'FILENAME': 'file2.fits'}
        data3 = Data(label='spec3')
        data3.meta = {'FILENAME': 'file1.fits'}

        datasets = [data1, data2, data3]

        result = group_spectra_by_filename(datasets)

        assert len(result) == 2
        assert len(result['file1.fits']) == 2
        assert len(result['file2.fits']) == 1

    def test_group_missing_filename(self):
        """
        Test grouping when some spectra don't have FILENAME metadata.
        """
        data1 = Data(label='spec1')
        data1.meta = {'FILENAME': 'test.fits'}
        data2 = Data(label='spec2')
        data2.meta = {}
        data3 = Data(label='spec3')
        data3.meta = {'FILENAME': 'test.fits'}

        datasets = [data1, data2, data3]

        result = group_spectra_by_filename(datasets)

        assert 'test.fits' in result
        assert None in result
        assert len(result['test.fits']) == 2
        assert len(result[None]) == 1

    def test_group_empty_datasets(self):
        """
        Test grouping with empty dataset list.
        """
        datasets = []

        result = group_spectra_by_filename(datasets)

        assert isinstance(result, defaultdict)
        assert len(result) == 0


# Copied and pasted from test_spectrum_list.py
@pytest.mark.parametrize('with_uncertainty', [True, False])
def test_combine_lists_to_1d_spectrum(with_uncertainty):
    wl = [1, 2, 3] * u.nm
    fnu = [10, 20, 30] * u.Jy
    if with_uncertainty:
        dfnu = [4, 5, 6] * u.Jy
    else:
        dfnu = None

    spec = combine_lists_to_1d_spectrum(wl, fnu, dfnu, u.nm, u.Jy)
    assert isinstance(spec, Spectrum)
    assert isinstance(spec.flux, u.Quantity)
    assert spec.flux.unit == u.Jy

    assert isinstance(spec.spectral_axis, u.Quantity)
    assert spec.spectral_axis.unit == u.nm

    assert np.all(spec.flux.value == np.array([10, 20, 30]))
    assert np.all(spec.spectral_axis.value == np.array([1, 2, 3]))

    if with_uncertainty:
        assert isinstance(spec.uncertainty, StdDevUncertainty)
        assert np.all(spec.uncertainty.array == np.array([4, 5, 6]))
    else:
        assert spec.uncertainty is None


class TestSplitSpectrumWith2DFluxArray:
    """
    Test the split_spectrum_with_2D_flux_array function.
    """
    def test_split_2d_flux_basic(self, spectrum2d):
        """
        Test splitting a spectrum with 2D flux array into a list.
        """
        result = split_spectrum_with_2D_flux_array(spectrum2d)

        assert len(result) == 5
        for i, sub_spec in enumerate(result):
            assert sub_spec.flux.shape == (spectrum2d.flux.shape[1],)
            assert np.array_equal(sub_spec.flux.value, spectrum2d.flux[i, :].value)
            assert np.array_equal(
                sub_spec.spectral_axis.value,
                spectrum2d.spectral_axis.value
            )

        # No uncertainty or mask in input, so none in output
        for sub_spec in result:
            assert sub_spec.uncertainty is None
            assert sub_spec.mask is None

    def test_split_2d_flux_with_uncertainty(self, spectrum2d):
        """
        Test splitting a spectrum with uncertainty.
        """
        uncertainty_2d = StdDevUncertainty(
            np.random.random(spectrum2d.shape) * spectrum2d.flux.unit,
        )
        spec = Spectrum(
            spectral_axis=spectrum2d.spectral_axis,
            flux=spectrum2d.flux,
            uncertainty=uncertainty_2d
        )

        result = split_spectrum_with_2D_flux_array(spec)

        assert len(result) == spectrum2d.flux.shape[0]
        for i, sub_spec in enumerate(result):
            assert sub_spec.uncertainty is not None
            assert np.array_equal(
                sub_spec.uncertainty.array,
                uncertainty_2d.array[i, :]
            )

    def test_split_2d_flux_with_mask(self, spectrum2d):
        """
        Test splitting a spectrum with mask.
        """
        mask_2d = np.zeros(spectrum2d.flux.shape, dtype=bool)
        mask_2d[:, -5:] = True
        spec = Spectrum(
            spectral_axis=spectrum2d.spectral_axis,
            flux=spectrum2d.flux,
            mask=mask_2d
        )

        result = split_spectrum_with_2D_flux_array(spec)

        assert len(result) == spectrum2d.flux.shape[0]
        for i, sub_spec in enumerate(result):
            assert sub_spec.mask is not None
            assert np.array_equal(sub_spec.mask, mask_2d[i, :])

    def test_split_2d_flux_with_metadata(self, spectrum2d):
        """
        Test that metadata is preserved when splitting.
        """
        meta = {'TELESCOPE': 'TEST', 'INSTRUMENT': 'FAKE'}
        spec = Spectrum(
            spectral_axis=spectrum2d.spectral_axis,
            flux=spectrum2d.flux,
            meta=meta
        )

        result = split_spectrum_with_2D_flux_array(spec)

        for sub_spec in result:
            assert sub_spec.meta == meta
