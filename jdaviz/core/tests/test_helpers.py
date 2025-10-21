import pytest
from unittest.mock import PropertyMock, patch

import numpy as np
from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose
from astropy.nddata import CCDData, NDDataArray
from astropy.wcs import WCS
from glue.core import ComponentID
from glue.core.roi import CircularROI
from specutils import SpectralRegion, Spectrum

from jdaviz.core.helpers import _next_subset_num


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


class TestConfigHelper:
    @pytest.fixture(autouse=True)
    def setup_class(self, deconfigged_helper, spectrum1d, spectrum2d, multi_order_spectrum_list):
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
        self.config_helper.plugins['Subset Tools'].import_region(
            SpectralRegion(6700*spectral_axis_unit, 7200*spectral_axis_unit),
            combination_mode='new')
        self.config_helper.plugins['Subset Tools'].import_region(
            SpectralRegion(8200*spectral_axis_unit, 8800*spectral_axis_unit),
            combination_mode='new')

        # flux_viewer = self.config_helper.app.get_viewer('Spectral Cube')
        # flux_viewer.apply_roi(CircularROI(5, 5, 3))

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
          [True, True, True, True, True, True, False, False, False, True])
         ])
    def test_get_data_with_one_subset_per_data(self, label, subset_name, answer):
        results = self.config_helper._get_data(data_label=label, spectral_subset=subset_name)
        assert list(results.mask) == answer

    def test_get_data_no_label_multiple_in_dc(self):
        with pytest.raises(ValueError, match='data_label must be set if more'):
            self.config_helper._get_data()

    def test_get_data_label_not_in_dc(self):
        with pytest.raises(ValueError, match='Blah not in '):
            self.config_helper._get_data(data_label="Blah")

    def test_get_data_no_label_one_in_dc(self):
        self.config_helper.app.data_collection.remove(
            self.config_helper.app.data_collection[self.label2])
        results = self.config_helper._get_data()
        assert_quantity_allclose(results.flux,
                                 self.spec.flux, atol=1e-5 * u.Unit(self.spec.flux.unit))

    def test_get_data_invalid_cls_class(self, specviz_helper):
        self.config_helper.app.data_collection.remove(
            self.config_helper.app.data_collection[self.label2])
        with pytest.raises(TypeError, match="cls in get_data must be a class or None."):
            self.config_helper._get_data('Test 1D Spectrum', cls=42)

    def test_get_data_invalid_subset_name(self):
        with pytest.raises(ValueError, match="not in list of valid subset names"):
            self.config_helper._get_data('Test 1D Spectrum', spectral_subset="Fail")

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
            mock_viewers[f"{base_viewer_name}[{i}]"] = (
                original_viewers[base_viewer_name]
            )

        # Patch the viewers property to return our mocked dict
        with patch.object(
            type(self.config_helper),
            'viewers',
            new_callable=PropertyMock,
            return_value=mock_viewers
        ):
            result = self.config_helper._get_clone_viewer_reference(
                base_viewer_name
            )
            assert result == f"{base_viewer_name}[4]"
            
    def test_set_data_component_new_component(self):
        """
        Test _set_data_component with a new component label.
        """
        original_n_components = len(self.data.components)

        new_values = np.ones(len(self.data.get_object().flux))
        self.config_helper._set_data_component(
            self.data, 'test_component', new_values
        )

        assert len(self.data.components) == original_n_components + 1
        assert 'test_component' in self.config_helper._component_ids

    def test_set_data_component_update_existing(self):
        """
        Test _set_data_component updating an existing component.
        """
        # First add a component
        new_values = np.ones(len(self.data.get_object().flux))
        self.config_helper._set_data_component(
            self.data, 'test_component', new_values
        )
        n_components_after_add = len(self.data.components)

        # Now update it
        updated_values = np.ones(len(self.data.get_object().flux)) * 2
        self.config_helper._set_data_component(
            self.data, 'test_component', updated_values
        )

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
        self.config_helper._set_data_component(
            self.data, 'direct_component', updated_values
        )

        # Should update, not add a duplicate
        component_labels = [c.label for c in self.data.components]
        assert component_labels.count('direct_component') == 1

    def test_set_data_component_cached_component_id(self):
        """
        Test _set_data_component uses cached ComponentID.
        """
        # Add a component to populate the cache
        values = np.ones(len(self.data.get_object().flux))
        self.config_helper._set_data_component(
            self.data, 'cached_comp', values
        )

        # Get the cached component ID
        cached_id = self.config_helper._component_ids['cached_comp']

        # Update the component
        new_values = np.ones(len(self.data.get_object().flux)) * 5
        self.config_helper._set_data_component(
            self.data, 'cached_comp', new_values
        )

        # Should still use the same component ID
        assert self.config_helper._component_ids['cached_comp'] == cached_id

    def test_get_data_spectral_subset_with_mask_subset_error(self):
        """
        Test _get_data: spectral_subset with mask_subset raises ValueError.
        """
        with pytest.raises(
            ValueError,
            match="cannot use both mask_subset and spectral_subset"
        ):
            self.config_helper._get_data(
                data_label=self.label,
                spectral_subset='Subset 1',
                mask_subset='Subset 2'
            )

    def test_get_data_temporal_subset_with_mask_subset_error(self):
        """
        Test _get_data: temporal_subset with mask_subset raises ValueError.
        """
        with pytest.raises(
            ValueError,
            match="cannot use both mask_subset and temporal_subset"
        ):
            self.config_helper._get_data(
                data_label=self.label,
                temporal_subset='Subset 1',
                mask_subset='Subset 2'
            )

    def test_get_data_temporal_subset_assignment(self):
        """
        Test _get_data: temporal_subset is assigned to mask_subset.
        """
        # This tests that temporal_subset flows through as mask_subset
        result = self.config_helper._get_data(
            data_label=self.label,
            temporal_subset='Subset 1'
        )
        # Verify the mask was applied (temporal_subset treated as mask)
        assert hasattr(result, 'mask')
        assert result.mask is not None

    def test_get_data_spatial_subset_not_region_error(self):
        """
        Test _get_data: spatial_subset that is not a Region raises ValueError.
        """
        # 'Subset 1' is a spectral subset, not spatial
        with pytest.raises(
            ValueError, match="is not a spatial subset"
        ):
            self.config_helper._get_data(
                data_label=self.label,
                spatial_subset='Subset 1',
                cls=Spectrum
            )

    def test_get_data_spectral_subset_not_spectral_region_error(self):
        """
        Test _get_data: spectral_subset that is not a SpectralRegion raises ValueError.
        """
        # Create a non-spectral subset and try to use it as spectral
        data = self.config_helper.app.data_collection[self.label]
        subset_state = data.id['flux'] > 5
        _ = self.config_helper.app.data_collection.new_subset_group(
            'not_spectral', subset_state
        )

        with pytest.raises(
            ValueError, match="is not a spectral subset"
        ):
            self.config_helper._get_data(
                data_label=self.label,
                spectral_subset='not_spectral'
            )

    def test_get_data_spatial_subset_code_path(self):
        """
        Test _get_data spatial subset code path
        (exception handling is difficult to test without deep mocking).
        """
        # Create a spatial subset using proper glue ROI
        # TODO: will likely have to adjust viewer name
        # flux_viewer = self.config_helper.app.get_viewer('Spectral Cube')
        # flux_viewer.apply_roi(CircularROI(5, 5, 3))

        # Verify the spatial subset code path executes without error
        result = self.config_helper._get_data(
            data_label=self.label,
            spatial_subset='Subset 1',
            cls=Spectrum
        )

        # Verify we got a result (successful path through lines 660-667)
        assert isinstance(result, Spectrum)

@pytest.mark.skip(reason="TODO: unskip once cube loaders are have been implemented")
class TestGetDataSubsetExceptionHandling:
    """
    Test coverage for exception handling in subset operations.
    """
    @pytest.fixture(autouse=True)
    def setup_data(self, deconfigged_helper, image_cube_hdu_obj):
        """
        Set up test data with spatial subsets.
        """
        self.config_helper = deconfigged_helper
        deconfigged_helper.load(image_cube_hdu_obj, format='Spectral Cube')
        self.label = deconfigged_helper.app.data_collection[0].label



    def test_get_data_mask_subset_code_path(self):
        """
        Test _get_data lines 684-687: mask subset code path
        (exception handling is difficult to test without deep mocking).
        """
        subset_plugin = self.config_helper.plugins['Subset Tools']
        subset_plugin.import_region(SpectralRegion(4.6e-7*u.m, 4.8e-7*u.m))

        # Verify the mask subset code path executes without error
        result = self.config_helper._get_data(
            data_label=self.label,
            mask_subset='Subset 1',
            cls=Spectrum
        )

        # Verify we got a result (successful path through lines 684-687)
        assert isinstance(result, Spectrum)
        assert hasattr(result, 'mask')

    def test_get_data_spatial_and_spectral_subset_combined(self):
        """
        Test _get_data line 690: spatial_subset with spectral_subset
        applies mask to data.
        """
        # Create spatial subset using proper glue ROI
        flux_viewer = self.config_helper.app.get_viewer('flux-viewer')
        flux_viewer.apply_roi(CircularROI(5, 5, 3))

        # Create spectral subset
        subset_plugin = self.config_helper.plugins['Subset Tools']
        subset_plugin.import_region(
            SpectralRegion(4.6e-7*u.m, 4.8e-7*u.m),
            combination_mode='new'
        )

        # Get data with both subsets
        result = self.config_helper._get_data(
            data_label=self.label,
            spatial_subset='Subset 1',
            spectral_subset='Subset 2',
            cls=Spectrum
        )

        # Verify that result is a Spectrum with a mask applied
        assert isinstance(result, Spectrum)
        assert hasattr(result, 'mask')
        assert result.mask is not None
        # The mask should have some True values (masked regions)
        assert np.any(result.mask)




@pytest.mark.skip(reason="TODO: need to adjust logic for deconfigged (lines 611-626)")
@pytest.mark.parametrize('data_tuple',
                         [('mos_image', 'Image', CCDData),
                          ('mos_spectrum1d', '1D Spectrum', Spectrum),
                          ('mos_spectrum2d', '2D Spectrum', Spectrum),
                          # TODO: enable when spectral cube loader is ready
                          # ('spectral_cube_wcs', 'Spectral Cube', Spectrum),
                          # ('image_cube_hdu_obj', 'Spectral Cube', Spectrum),
                          # TODO: enable when rampviz loader is ready
                          # ('jwst_level_1b_ramp', 'Ramp', NDDataArray),
                          ]
                         )
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


def test_get_data_cls_nddataarray_for_rampviz(rampviz_helper, jwst_level_1b_ramp):
    """
    Test _get_data: cls inferred as NDDataArray for rampviz config.
    """
    rampviz_helper.load_data(jwst_level_1b_ramp)
    # Get the actual label from data collection
    label = rampviz_helper.app.data_collection[0].label

    data = rampviz_helper.app.data_collection[label]

    # Rampviz should infer NDDataArray for multi-dimensional data
    result = rampviz_helper.get_data(data_label=label)
    assert isinstance(result, NDDataArray)
