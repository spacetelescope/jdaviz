import pytest

import numpy as np
from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose
from astropy.nddata import CCDData, NDDataArray
from glue.core import ComponentID
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
    def setup_class(self, specviz_helper, spectrum1d, multi_order_spectrum_list):
        self.spec_app = specviz_helper
        self.spec = spectrum1d
        self.label = "Test 1D Spectrum"
        spectral_axis_unit = u.AA

        self.spec2 = spectrum1d._copy(
            spectral_axis=spectrum1d.spectral_axis+1000*spectral_axis_unit)
        self.label2 = "Test 1D Spectrum 2"
        self.spec_app.load_data(spectrum1d, data_label=self.label)
        self.spec_app.load_data(self.spec2, data_label=self.label2)

        # Add 3 subsets to cover different parts of spec and spec2
        self.spec_app.plugins['Subset Tools'].import_region(
            SpectralRegion(6000*spectral_axis_unit, 6500*spectral_axis_unit))
        self.spec_app.plugins['Subset Tools'].import_region(
            SpectralRegion(6700*spectral_axis_unit, 7200*spectral_axis_unit),
            combination_mode='new')
        self.spec_app.plugins['Subset Tools'].import_region(
            SpectralRegion(8200*spectral_axis_unit, 8800*spectral_axis_unit),
            combination_mode='new')

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
    def test_get_data_with_one_subset_per_data(self, specviz_helper, label, subset_name, answer):

        results = specviz_helper.get_data(data_label=label,
                                          spectral_subset=subset_name)
        assert list(results.mask) == answer

    def test_get_data_no_label_multiple_in_dc(self, specviz_helper):
        with pytest.raises(ValueError, match='data_label must be set if more'):
            specviz_helper.get_data()

    def test_get_data_label_not_in_dc(self, specviz_helper):
        with pytest.raises(ValueError, match='Blah not in '):
            specviz_helper.get_data(data_label="Blah")

    def test_get_data_no_label_one_in_dc(self, specviz_helper):
        specviz_helper.app.data_collection.remove(specviz_helper.app.data_collection[self.label2])
        results = specviz_helper.get_data()
        assert_quantity_allclose(results.flux,
                                 self.spec.flux, atol=1e-5 * u.Unit(self.spec.flux.unit))

    def test_get_data_invald_cls_class(self, specviz_helper):
        specviz_helper.app.data_collection.remove(specviz_helper.app.data_collection[self.label2])
        with pytest.raises(TypeError, match="cls in get_data must be a class or None."):
            specviz_helper.get_data('Test 1D Spectrum', cls=42)

    def test_get_data_invald_subset_name(self, specviz_helper):
        with pytest.raises(ValueError, match="not in list of valid subset names"):
            specviz_helper.get_data('Test 1D Spectrum', spectral_subset="Fail")


class TestGetCloneViewerReference:
    """
    Test coverage for _get_clone_viewer_reference function.
    """

    def test_get_clone_viewer_reference_no_clones(self, specviz_helper):
        """
        Test _get_clone_viewer_reference when no clones exist.
        """
        ref = specviz_helper._get_clone_viewer_reference(
            'spectrum-viewer'
        )
        assert ref == 'spectrum-viewer[1]'

    def test_get_clone_viewer_reference_with_existing_clones(
        self, specviz_helper
    ):
        """
        Test _get_clone_viewer_reference with existing cloned viewers.
        """
        # Manually add cloned viewer references to simulate existing
        # clones
        viewer = list(specviz_helper.app._viewer_store.values())[0]
        from jdaviz.configs.default.plugins.viewers import (
            JdavizViewerWindow
        )

        # Simulate an existing clone by adding to viewers dict
        viewer._ref_or_id = 'spectrum-viewer[1]'
        specviz_helper.app._viewer_store['spectrum-viewer[1]'] = viewer

        ref = specviz_helper._get_clone_viewer_reference(
            'spectrum-viewer'
        )
        assert ref == 'spectrum-viewer[2]'

    def test_get_clone_viewer_reference_multiple_clones(
            self, specviz_helper
    ):
        """
        Test _get_clone_viewer_reference with multiple existing clones.
        """
        viewer = list(specviz_helper.app._viewer_store.values())[0]

        # Simulate multiple clones
        for i in range(1, 4):
            viewer._ref_or_id = f'spectrum-viewer[{i}]'
            specviz_helper.app._viewer_store[
                f'spectrum-viewer[{i}]'
            ] = viewer

        ref = specviz_helper._get_clone_viewer_reference(
            'spectrum-viewer'
        )
        assert ref == 'spectrum-viewer[4]'


class TestSetDataComponent:
    """
    Test coverage for _set_data_component function.
    """

    @pytest.fixture(autouse=True)
    def setup_data(self, specviz_helper, spectrum1d):
        """
        Set up test data.
        """
        self.helper = specviz_helper
        self.label = 'Test Spectrum'
        self.helper.load_data(spectrum1d, data_label=self.label)
        self.data = self.helper.app.data_collection[self.label]

    def test_set_data_component_new_component(self):
        """
        Test _set_data_component with a new component label.
        """
        original_n_components = len(self.data.components)

        new_values = np.ones(len(self.data.get_object().flux))
        self.helper._set_data_component(
            self.data, 'test_component', new_values
        )

        assert len(self.data.components) == original_n_components + 1
        assert 'test_component' in self.helper._component_ids

    def test_set_data_component_update_existing(self):
        """
        Test _set_data_component updating an existing component.
        """
        # First add a component
        new_values = np.ones(len(self.data.get_object().flux))
        self.helper._set_data_component(
            self.data, 'test_component', new_values
        )
        n_components_after_add = len(self.data.components)

        # Now update it
        updated_values = np.ones(len(self.data.get_object().flux)) * 2
        self.helper._set_data_component(
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
        self.helper._set_data_component(
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
        self.helper._set_data_component(
            self.data, 'cached_comp', values
        )

        # Get the cached component ID
        cached_id = self.helper._component_ids['cached_comp']

        # Update the component
        new_values = np.ones(len(self.data.get_object().flux)) * 5
        self.helper._set_data_component(
            self.data, 'cached_comp', new_values
        )

        # Should still use the same component ID
        assert self.helper._component_ids['cached_comp'] == cached_id


class TestGetDataSpecificLines:
    """
    Test coverage for specific lines in _get_data function.
    """

    @pytest.fixture(autouse=True)
    def setup_data(self, specviz_helper, spectrum1d):
        """
        Set up test data with subsets.
        """
        self.helper = specviz_helper
        self.label = 'Test Spectrum'
        self.helper.load_data(spectrum1d, data_label=self.label)

        # Add spectral subsets
        self.helper.plugins['Subset Tools'].import_region(
            SpectralRegion(6000*u.AA, 6500*u.AA)
        )
        self.helper.plugins['Subset Tools'].import_region(
            SpectralRegion(7000*u.AA, 7500*u.AA),
            combination_mode='new'
        )

    def test_get_data_spectral_subset_with_mask_subset_error(self):
        """
        Test _get_data line 597: spectral_subset with mask_subset
        raises ValueError.
        """
        with pytest.raises(
            ValueError,
            match="cannot use both mask_subset and spectral_subset"
        ):
            self.helper._get_data(
                data_label=self.label,
                spectral_subset='Subset 1',
                mask_subset='Subset 2'
            )

    def test_get_data_temporal_subset_with_mask_subset_error(self):
        """
        Test _get_data lines 603-606: temporal_subset with mask_subset
        raises ValueError.
        """
        with pytest.raises(
            ValueError,
            match="cannot use both mask_subset and temporal_subset"
        ):
            self.helper._get_data(
                data_label=self.label,
                temporal_subset='Subset 1',
                mask_subset='Subset 2'
            )

    def test_get_data_spatial_subset_not_region_error(self):
        """
        Test _get_data line 658: spatial_subset that is not a Region
        raises ValueError.
        """
        # 'Subset 1' is a spectral subset, not spatial
        with pytest.raises(
            ValueError, match="is not a spatial subset"
        ):
            self.helper._get_data(
                data_label=self.label,
                spatial_subset='Subset 1',
                cls=Spectrum
            )

    def test_get_data_spectral_subset_not_spectral_region_error(self):
        """
        Test _get_data line 674: spectral_subset that is not a
        SpectralRegion raises ValueError.
        """
        # Create a non-spectral subset and try to use it as spectral
        data = self.helper.app.data_collection[self.label]
        subset_state = data.id['flux'] > 5
        subset_group = self.helper.app.data_collection.new_subset_group(
            'not_spectral', subset_state
        )

        with pytest.raises(
            ValueError, match="is not a spectral subset"
        ):
            self.helper._get_data(
                data_label=self.label,
                spectral_subset='not_spectral'
            )

    def test_get_data_cls_none_with_spatial_subset_error(self):
        """
        Test _get_data line 644: cls=None with spatial_subset raises
        AttributeError.
        """
        data = self.helper.app.data_collection[self.label]
        original_meta = data.meta.copy()

        # Clear native_data_cls to force cls=None path
        if '_native_data_cls' in data.meta:
            del data.meta['_native_data_cls']

        try:
            # Create a dummy spatial subset
            subset_state = data.id['flux'] > 0
            subset_group = (
                self.helper.app.data_collection.new_subset_group(
                    'spatial_test', subset_state
                )
            )

            with pytest.raises(
                AttributeError,
                match="A valid cls must be provided"
            ):
                self.helper._get_data(
                    data_label=self.label,
                    spatial_subset='spatial_test',
                    cls=None
                )
        finally:
            data.meta = original_meta

    def test_get_data_cls_none_with_mask_subset_error(self):
        """
        Test _get_data line 648: cls=None with mask_subset raises
        AttributeError.
        """
        data = self.helper.app.data_collection[self.label]
        original_meta = data.meta.copy()

        # Clear native_data_cls to force cls=None path
        if '_native_data_cls' in data.meta:
            del data.meta['_native_data_cls']

        try:
            with pytest.raises(
                AttributeError,
                match="A valid cls must be provided"
            ):
                self.helper._get_data(
                    data_label=self.label,
                    mask_subset='Subset 1',
                    cls=None
                )
        finally:
            data.meta = original_meta


class TestGetDataClsInference:
    """
    Test coverage for cls inference in _get_data (lines 616, 618, 623).
    """

    def test_get_data_cls_ccddata_for_2d(self, cubeviz_helper):
        """
        Test _get_data line 616: cls inferred as CCDData for 2D data
        (not in specviz2d).
        """
        # Load 2D data into cubeviz
        flux = np.ones((10, 10))
        ccd = CCDData(data=flux, unit=u.Jy)
        cubeviz_helper.load_data(ccd, data_label='2d_data')

        data = cubeviz_helper.app.data_collection['2d_data']
        assert data.ndim == 2

        result = cubeviz_helper._get_data(data_label='2d_data')
        assert isinstance(result, CCDData)

    def test_get_data_cls_spectrum_from_cube(
        self, cubeviz_helper, image_cube_hdu_obj
    ):
        """
        Test _get_data line 626: cls inferred as Spectrum for 3D
        cube in cubeviz.
        """
        cubeviz_helper.load_data(image_cube_hdu_obj)
        # Get the actual label from data collection after loading
        label = cubeviz_helper.app.data_collection[0].label

        data = cubeviz_helper.app.data_collection[label]
        assert data.ndim == 3

        result = cubeviz_helper._get_data(data_label=label)
        assert isinstance(result, Spectrum)

    def test_get_data_cls_nddataarray_for_rampviz(
        self, rampviz_helper, jwst_level_1b_ramp
    ):
        """
        Test _get_data line 623: cls inferred as NDDataArray for
        rampviz config.
        """
        rampviz_helper.load_data(jwst_level_1b_ramp)
        # Get the actual label from data collection
        label = rampviz_helper.app.data_collection[0].label

        data = rampviz_helper.app.data_collection[label]

        # Rampviz should infer NDDataArray for multi-dimensional data
        result = rampviz_helper._get_data(data_label=label)
        assert isinstance(result, NDDataArray)

