"""
Tests the features of the Model Fitting Plugin (Selecting model parameters, adding models, etc.)
This does NOT test the actual fitting self (see test_fitting.py for that)
"""

import numpy as np
from astropy.nddata import StdDevUncertainty
import pytest

from jdaviz.configs.default.plugins.model_fitting.initializers import MODELS


def test_default_model_labels(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    modelfit_plugin = specviz_helper.app.get_tray_item_from_name('g-model-fitting')
    # By default, the spectral region should be the entire spectrum
    assert modelfit_plugin.spectral_subset_selected == "Entire Spectrum"

    for model in MODELS:
        # Check that the auto label is set correctly (or at least the first character matches)
        # BlackBody and Polynomial labels behave differently, so check only the first character
        modelfit_plugin.model_comp_selected = model
        assert modelfit_plugin.comp_label[0] == model[0]

        # Test component label increments by default
        previous_label = modelfit_plugin.comp_label
        modelfit_plugin.vue_add_model({})
        assert modelfit_plugin.comp_label == previous_label + "_1"

    assert len(modelfit_plugin.component_models) == len(MODELS)

    # Test that default equation adds all components together
    assert (
        modelfit_plugin.model_equation
        == "+".join(param["id"] for param in modelfit_plugin.component_models)
    )


def test_custom_model_labels(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    modelfit_plugin = specviz_helper.app.get_tray_item_from_name('g-model-fitting')

    for i, model in enumerate(MODELS):
        # Add one of each model with a unique name
        modelfit_plugin.model_comp_selected = model
        modelfit_plugin.comp_label = f"test_model_{i}"
        modelfit_plugin.vue_add_model({})

    assert len(modelfit_plugin.component_models) == len(MODELS)

    # Test that default equation adds all components together
    assert (
        modelfit_plugin.model_equation
        == "+".join(param["id"] for param in modelfit_plugin.component_models)
    )


@pytest.mark.filterwarnings('ignore')
def test_register_model_with_uncertainty_weighting(specviz_helper, spectrum1d):
    spectrum1d.uncertainty = StdDevUncertainty(spectrum1d.flux * 0.1)
    specviz_helper.load_data(spectrum1d)
    modelfit_plugin = specviz_helper.app.get_tray_item_from_name('g-model-fitting')

    # Test registering a simple linear fit
    modelfit_plugin.model_comp_selected = 'Linear1D'
    modelfit_plugin.vue_add_model({})
    modelfit_plugin.calculate_fit()
    assert len(specviz_helper.app.data_collection) == 2

    # Test fitting again overwrites original fit
    modelfit_plugin.calculate_fit()
    assert len(specviz_helper.app.data_collection) == 2

    # Test custom model label
    test_label = 'my_Linear1D'
    modelfit_plugin.results_label = test_label
    modelfit_plugin.calculate_fit()
    assert test_label in specviz_helper.app.data_collection

    # Test that the parameter uncertainties were updated
    expected_uncertainties = {'slope': 0.0003657, 'intercept': 2.529}
    result_model = modelfit_plugin.component_models[0]
    for param in result_model["parameters"]:
        assert np.allclose(param["std"], expected_uncertainties[param["name"]], rtol=0.01)


@pytest.mark.filterwarnings('ignore')
def test_register_model_uncertainty_is_none(specviz_helper, spectrum1d):
    # Set uncertainty to None
    spectrum1d.uncertainty = None
    specviz_helper.load_data(spectrum1d)
    modelfit_plugin = specviz_helper.app.get_tray_item_from_name('g-model-fitting')

    # Test registering a simple linear fit
    modelfit_plugin.model_comp_selected = 'Linear1D'
    modelfit_plugin.vue_add_model({})
    modelfit_plugin.calculate_fit()
    assert len(specviz_helper.app.data_collection) == 2

    # Test fitting again overwrites original fit
    modelfit_plugin.calculate_fit()
    assert len(specviz_helper.app.data_collection) == 2

    # Test custom model label
    test_label = 'my_Linear1D'
    modelfit_plugin.results_label = test_label
    modelfit_plugin.calculate_fit()
    assert test_label in specviz_helper.app.data_collection

    # Test that the parameter uncertainties were updated
    expected_uncertainties = {'slope': 0.00038, 'intercept': 2.67}
    result_model = modelfit_plugin.component_models[0]
    for param in result_model["parameters"]:
        assert np.allclose(param["std"], expected_uncertainties[param["name"]], rtol=0.01)


@pytest.mark.filterwarnings('ignore')
def test_register_cube_model(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube)
    modelfit_plugin = cubeviz_helper.app.get_tray_item_from_name('g-model-fitting')

    # Test custom model label
    modelfit_plugin.create_model_component('Linear1D', 'L')
    test_label = 'my_Linear1D'
    modelfit_plugin.results_label = test_label
    # changing the lable should set auto to False, but the event may not have triggered yet
    modelfit_plugin.results_label_auto = False
    modelfit_plugin.cube_fit = True
    assert modelfit_plugin.results_label_default == 'cube-fit model'
    assert modelfit_plugin.results_label == test_label
    modelfit_plugin.calculate_fit()
    assert test_label in cubeviz_helper.app.data_collection


@pytest.mark.filterwarnings('ignore')
def test_user_api(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    p = specviz_helper.plugins['Model Fitting']

    # even though the default label is set to C, adding Linear1D should default to its automatic
    # default label of 'L'
    assert p.model_component_label.value == 'C'
    p.create_model_component('Linear1D')
    assert p.model_components == ['L']

    with pytest.raises(ValueError, match='poly_order should only be passed if model_component is Polynomial1D'):  # noqa
        p.create_model_component('Linear1D', poly_order=2)

    with pytest.raises(ValueError, match="model component label 'L' already in use"):
        p.create_model_component('Linear1D', 'L')

    with pytest.raises(ValueError, match="model component with label 'dne' does not exist"):
        p.remove_model_component('dne')

    p.remove_model_component('L')
    assert len(p.model_components) == 0

    p.create_model_component('Polynomial1D', poly_order=2)
    assert p.model_components == ['P2']

    with pytest.raises(ValueError, match="'dne' is not a label of an existing model component"):
        p.get_model_component('dne')

    p.get_model_component('P2')
    p.set_model_component('P2', 'c0', value=0.2, fixed=True)
    assert p.get_model_component('P2', 'c0')['value'] == 0.2
    assert p.get_model_component('P2', 'c0')['fixed'] is True
