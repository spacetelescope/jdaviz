import pytest
from unittest.mock import PropertyMock, patch
import warnings

import numpy as np
from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose
from astropy.nddata import CCDData, NDDataArray
from glue.core import ComponentID
from glue.core.roi import CircularROI
from specutils import SpectralRegion, Spectrum

from jdaviz.core.helpers import _next_subset_num
from jdaviz.core.loaders import ObjectResolver, ObjectParser


class MockGroupItem:
    def __init__(self, label):
        self.label = label


@pytest.mark.parametrize(
    ('label', 'prefix', 'answer'),
    [('Subset 1', 'Subset', 2),
     ('Subset 10', 'Subset', 11),
     ('MaskedSubset', 'MaskedSubset', 1),
     ('acs_47tuc_1[SCI,1]', 'acs_47tuc_1[SCI,1]', 1),
     ('acs_47tuc_1[SCI,1] 1', 'acs_47tuc_1[SCI,1]', 2),
     ('asdakdh663 dada233 32432 2', 'asdakdh663', 3),
     ('asdakdh663 dada233 32432 2', 'hmmm', 1),
     ('42 1337 kookookachu', '42', 1)])
def test_next_subset_num(label, prefix, answer):
    mocked_group = [MockGroupItem(label)]
    assert _next_subset_num(prefix, mocked_group) == answer


class TestConfigHelperSpec:
    @pytest.fixture(autouse=True)
    def _setup_class(self, deconfigged_helper, spectrum1d, spectrum2d, multi_order_spectrum_list):
        self.config_helper = deconfigged_helper

        self.spec = spectrum1d
        self.label = "Test 1D Spectrum"
        spectral_axis_unit = u.AA

        self.spec2 = spectrum1d._copy(
            spectral_axis=spectrum1d.spectral_axis + 1000 * spectral_axis_unit)
        self.label2 = "Test 1D Spectrum 2"

        self.config_helper.load(spectrum1d, data_label=self.label, format='1D Spectrum')
        self.config_helper.load(self.spec2, data_label=self.label2, format='1D Spectrum')

        # Add 3 subsets to cover different parts of spec and spec2
        self.config_helper.plugins['Subset Tools'].import_region(
            SpectralRegion(6000*spectral_axis_unit, 6500*spectral_axis_unit))
        # combination_mode = 'new' is the default, so no need to specify
        self.config_helper.plugins['Subset Tools'].import_region(
            SpectralRegion(6700*spectral_axis_unit, 7200*spectral_axis_unit))
        self.config_helper.plugins['Subset Tools'].import_region(
            SpectralRegion(8200*spectral_axis_unit, 8800*spectral_axis_unit))

        self.data = self.config_helper.app.data_collection[self.label]

    @pytest.mark.parametrize(
        ('label', 'subset_name', 'answer'),
        [('Test 1D Spectrum', 'Subset 1',
          [False, False, False, True, True, True, True, True, True, True]),
         ('Test 1D Spectrum', 'Subset 2',
          [True, True, True, True, False, False, True, True, True, True]),
         ('Test 1D Spectrum', 'Subset 3',
          [True, True, True, True, True, True, True, True, True, True]),
         ('Test 1D Spectrum 2', 'Subset 1',
          [True, True, True, True, True, True, True, True, True, True]),
         ('Test 1D Spectrum 2', 'Subset 2',
          [False, True, True, True, True, True, True, True, True, True]),
         ('Test 1D Spectrum 2', 'Subset 3',
          [True, True, True, True, True, True, False, False, False, True])])
    def test_get_data_with_one_subset_per_data(self, label, subset_name, answer):
        results = self.config_helper._get_data(data_label=label, spectral_subset=subset_name)
        assert list(results.mask) == answer

    def test_get_data_errors(self):
        # multiple data, no label
        with pytest.raises(ValueError, match='data_label must be set if more'):
            self.config_helper._get_data()

        # data label not in data collection
        with pytest.raises(ValueError, match='Blah not in '):
            self.config_helper._get_data(data_label="Blah")

        # invalid cls type
        self.config_helper.app.data_collection.remove(
            self.config_helper.app.data_collection[self.label2])
        with pytest.raises(TypeError, match="cls in get_data must be a class or None."):
            self.config_helper._get_data('Test 1D Spectrum', cls=42)

        # spectral subset name not in data collection
        with pytest.raises(ValueError, match="not in list of valid subset names"):
            self.config_helper._get_data('Test 1D Spectrum', spectral_subset="Fail")

    def test_get_data_no_label_one_in_dc(self):
        self.config_helper.app.data_collection.remove(
            self.config_helper.app.data_collection[self.label2])
        results = self.config_helper._get_data()
        assert_quantity_allclose(results.flux,
                                 self.spec.flux, atol=1e-5 * u.Unit(self.spec.flux.unit))

    def test_get_clone_viewer_reference(self):
        """
        Test _get_clone_viewer_reference alone and with multiple existing clones.
        """
        base_viewer_name = '1D Spectrum'
        result = self.config_helper._get_clone_viewer_reference(base_viewer_name)
        assert result == f"{base_viewer_name}[1]"

        # Get the original viewers dict
        original_viewers = self.config_helper.viewers
        mock_viewers = dict(original_viewers)
        for i in range(1, 4):
            mock_viewers[f"{base_viewer_name}[{i}]"] = original_viewers[base_viewer_name]

        # Patch the viewers property to return our mocked dict
        with patch.object(type(self.config_helper),
                          'viewers',
                          new_callable=PropertyMock,
                          return_value=mock_viewers):
            result = self.config_helper._get_clone_viewer_reference(base_viewer_name)
            assert result == f"{base_viewer_name}[4]"

    def test_set_data_component(self):
        """
        Test _set_data_component with a new component label and update it.
        """
        original_n_components = len(self.data.components)

        new_values = np.ones(len(self.data.get_object().flux))
        self.config_helper._set_data_component(self.data, 'test_component', new_values)

        assert len(self.data.components) == original_n_components + 1
        assert 'test_component' in self.config_helper._component_ids

        # Now check updating existing component
        n_components_after_add = len(self.data.components)
        # Now update it
        updated_values = np.ones(len(self.data.get_object().flux)) * 2
        self.config_helper._set_data_component(self.data, 'test_component', updated_values)

        # Should not add a new component, just update
        assert len(self.data.components) == n_components_after_add

    def test_set_data_component_existing_in_data_not_in_cache(self):
        """
        Test _set_data_component with component in data but not cache.
        """
        # Add a component directly to data, bypassing the cache
        comp_id = ComponentID('direct_component')
        values = np.ones(len(self.data.get_object().flux))
        self.data.add_component(values, comp_id)

        # Now use _set_data_component with the same label
        updated_values = np.ones(len(self.data.get_object().flux)) * 3
        self.config_helper._set_data_component(self.data, 'direct_component', updated_values)

        # Should update, not add a duplicate
        component_labels = [c.label for c in self.data.components]
        assert component_labels.count('direct_component') == 1

    def test_set_data_component_cached_component_id(self):
        """
        Test _set_data_component uses cached ComponentID.
        """
        # Add a component to populate the cache
        values = np.ones(len(self.data.get_object().flux))
        self.config_helper._set_data_component(self.data, 'cached_comp', values)

        # Get the cached component ID
        cached_id = self.config_helper._component_ids['cached_comp']

        # Update the component
        new_values = np.ones(len(self.data.get_object().flux)) * 5
        self.config_helper._set_data_component(self.data, 'cached_comp', new_values)

        # Should still use the same component ID
        assert self.config_helper._component_ids['cached_comp'] == cached_id


class TestConfigHelperSubsets:
    @pytest.fixture(autouse=True)
    def setup_class(self, cubeviz_helper, deconfigged_helper, image_cube_hdu_obj):
        """
        Set up test data with spatial subsets.
        """
        # self.config_helper = deconfigged_helper
        self.config_helper = cubeviz_helper
        # self.config_helper.load(image_cube_hdu_obj, format='Spectral Cube')
        self.config_helper.load_data(image_cube_hdu_obj)
        self.data = self.config_helper.app.data_collection[0]
        self.label = self.data.label

        subset_plugin = self.config_helper.plugins['Subset Tools']
        # Subset 1, Spatial
        subset_plugin.import_region(CircularROI(5, 5, 3))
        # Subset 2, Spectral
        subset_plugin.import_region(SpectralRegion(4.6e-7 * u.m, 4.8e-7 * u.m))

    @pytest.mark.parametrize(
        ('spatial_subset', 'spectral_subset', 'temporal_subset', 'mask_subset'),
        [('Subset 1', None, None, None),
         (None, 'Subset 2', None, None),
         (None, None, 'Subset 1', None),
         (None, None, None, 'Subset 2'),
         ('Subset 1', 'Subset 2', None, None)])
    def test_get_data_spatial_spectral_subsets(self,
                                               spatial_subset, spectral_subset,
                                               temporal_subset, mask_subset):
        """
        Test _get_data spatial subset code path
        (exception handling is difficult to test without deep mocking).
        """
        # Verify the spatial subset code path executes without error
        result = self.config_helper._get_data(data_label=self.label,
                                              spatial_subset=spatial_subset,
                                              spectral_subset=spectral_subset,
                                              temporal_subset=temporal_subset,
                                              mask_subset=mask_subset,
                                              cls=Spectrum)

        # Verify we got a result
        assert isinstance(result, Spectrum)

        spatial_spectral_combo = spatial_subset is not None and spectral_subset is not None
        if mask_subset is not None or temporal_subset is not None or spatial_spectral_combo:
            # Verify that result is a Spectrum with a mask applied
            assert hasattr(result, 'mask')
            assert result.mask is not None
            # The mask should have some True values (masked regions)
            assert np.any(result.mask)

    # TODO: May have to change cls=Spectrum to something else
    #  once we adjust the logic for deconfigged
    @pytest.mark.parametrize(
        ('spatial_subset', 'spectral_subset', 'temporal_subset', 'mask_subset', 'cls',
         'error_type', 'error_msg'), [
            (None, 'Subset 2', None, 'Subset 2', Spectrum,
             ValueError, 'cannot use both mask_subset and spectral_subset'),
            (None, None, 'Subset 1', 'Subset 2', Spectrum,
             ValueError, 'cannot use both mask_subset and temporal_subset'),
            ('Subset 1', None, None, None, None,
             AttributeError, 'A valid cls must be provided to apply subset'),
            (None, None, None, 'Subset 2', None,
             AttributeError, 'A valid cls must be provided to apply subset'),
            ('Subset 2', None, None, None, Spectrum,
             ValueError, 'is not a spatial subset'),
            (None, 'Subset 1', None, None, Spectrum,
             ValueError, 'is not a spectral subset')])
    def test_get_data_subset_errors(self,
                                    spatial_subset, spectral_subset,
                                    temporal_subset, mask_subset, cls,
                                    error_type, error_msg):
        if cls is None:
            # Injecting a 'Trace' key in meta is the only way to
            # get past the cls check and into the subset application code
            self.data.meta['Trace'] = True
            if '_native_data_cls' in self.data.meta:
                self.data.meta.pop('_native_data_cls')

        with pytest.raises(error_type, match=error_msg):
            self.config_helper._get_data(data_label=self.label,
                                         spatial_subset=spatial_subset,
                                         spectral_subset=spectral_subset,
                                         temporal_subset=temporal_subset,
                                         mask_subset=mask_subset,
                                         cls=cls)


@pytest.mark.skip(reason="TODO: need to adjust logic for deconfigged (lines 611-626)")
@pytest.mark.parametrize('data_tuple',
                         [('mos_image', 'Image', CCDData),
                          ('mos_spectrum1d', '1D Spectrum', Spectrum),
                          ('mos_spectrum2d', '2D Spectrum', Spectrum),
                          ('spectral_cube_wcs', 'Spectral Cube', Spectrum),
                          ('image_cube_hdu_obj', 'Spectral Cube', Spectrum),
                          # TODO: enable when rampviz loader is ready
                          # ('jwst_level_1b_ramp', 'Ramp', NDDataArray),
                          ])
def test_get_data_cls(deconfigged_helper, request, data_tuple):
    """
    Test _get_data cls inference.
    1) CCDData -> CCDData
    2) 1D Spectrum -> Spectrum
    3) 2D Spectrum -> Spectrum
    4) Spectral Cube -> Spectrum
    """
    input_fixture, data_label, expected_cls = data_tuple
    input_data = request.getfixturevalue(input_fixture)
    deconfigged_helper.load(input_data, data_label=data_label, format=data_label)

    # Get actual label from data collection after loading
    label = deconfigged_helper.app.data_collection[0].label
    data = deconfigged_helper.app.data_collection[label]

    # Clear _native_data_cls to force cls inference path
    if '_native_data_cls' in data.meta:
        data.meta.pop('_native_data_cls')

    result = deconfigged_helper._get_data(data_label=label)
    assert isinstance(result, expected_cls)


def test_get_data_cls_spectrum_for_specviz2d(specviz2d_helper, spectrum2d):
    """
    Test _get_data: cls inferred as Spectrum for specviz2d config.
    """
    specviz2d_helper.load_data(spectrum2d)
    # Get the actual label from data collection
    label = specviz2d_helper.app.data_collection[0].label

    # Spectrum should infer Spectrum2d for multi-dimensional data
    result = specviz2d_helper.get_data(data_label=label)
    assert isinstance(result, Spectrum)


def test_get_data_cls_nddataarray_for_rampviz(rampviz_helper, jwst_level_1b_ramp):
    """
    Test _get_data: cls inferred as NDDataArray for rampviz config.
    """
    rampviz_helper.load_data(jwst_level_1b_ramp)
    # Get the actual label from data collection
    label = rampviz_helper.app.data_collection[0].label

    # Rampviz should infer NDDataArray for multi-dimensional data
    result = rampviz_helper.get_data(data_label=label)
    assert isinstance(result, NDDataArray)


def test_delete_region_with_valid_subset(cubeviz_helper, image_cube_hdu_obj):
    """
    Test _delete_region with a valid subset label.
    """
    cubeviz_helper.load(image_cube_hdu_obj, format='3D Spectrum')

    # Create a subset
    subset_plugin = cubeviz_helper.plugins['Subset Tools']
    subset_plugin.import_region(CircularROI(5, 5, 3))

    # Verify subset was created
    subset_labels = [s.label for s in cubeviz_helper.app.data_collection.subset_groups]
    assert 'Subset 1' in subset_labels

    # Delete the region
    cubeviz_helper._delete_region('Subset 1')

    # Verify it was deleted
    subset_labels_after = [s.label for s in cubeviz_helper.app.data_collection.subset_groups]
    assert 'Subset 1' not in subset_labels_after


def test_delete_region_with_invalid_subset(cubeviz_helper, image_cube_hdu_obj):
    """
    Test _delete_region with an invalid subset label (early return).
    """
    cubeviz_helper.load_data(image_cube_hdu_obj)

    # Try to delete a non-existent subset (should not raise error, just return)
    cubeviz_helper._delete_region('NonExistentSubset')

    # Should not raise any errors


def test_load_with_show_in_viewer_deprecated(specviz_helper, spectrum1d):
    """
    Test _load with deprecated 'show_in_viewer' kwarg triggers warning and conversion.
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        specviz_helper.load(spectrum1d, format='1D Spectrum', show_in_viewer=True)
        # Check that deprecation warning was raised
        assert len(w) >= 1
        for warning in w:
            if 'show_in_viewer' in str(warning.message):
                assert issubclass(warning.category, DeprecationWarning)
                break
        else:
            assert False, "DeprecationWarning for 'show_in_viewer' not raised."


def test_load_with_both_viewer_and_show_in_viewer_raises_error(deconfigged_helper, spectrum1d):
    """
    Test _load with both 'viewer' and 'show_in_viewer' raises ValueError.
    """
    with pytest.raises(ValueError, match='Cannot specify both'):
        deconfigged_helper.load(
            spectrum1d, format='1D Spectrum', viewer='spectrum-viewer', show_in_viewer=True)


def test_loaders_not_implemented_without_dev_flag(deconfigged_helper, mosviz_helper):
    """
    Test loaders property raises NotImplementedError without dev flag/or for configs
    not in CONFIGS_WITH_LOADERS.
    """
    # Mosviz is not in CONFIGS_WITH_LOADERS (for now)
    with pytest.raises(NotImplementedError, match='loaders is under active development'):
        _ = mosviz_helper.loaders


def test_get_loader_default_args(deconfigged_helper, spectrum1d):
    """
    Test _get_loader with parser_name is None
    """
    deconfigged_helper.load(spectrum1d, data_label='test', format='1D Spectrum')
    resolver = deconfigged_helper._get_loader('object')
    assert isinstance(resolver, ObjectResolver)

    parser = deconfigged_helper._get_loader('object', parser_name='object')
    assert isinstance(parser, ObjectParser)
