"""
Tests the features of the Model Fitting Plugin (Selecting model parameters, adding models, etc.)
This does NOT test the actual fitting self (see test_fitting.py for that)
"""

import uuid

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
        modelfit_plugin.comp_selected = model
        assert modelfit_plugin.comp_label[0] == model[0]

        # Test component label increments by default
        previous_label = modelfit_plugin.comp_label
        modelfit_plugin.vue_add_model()
        try:
            assert modelfit_plugin.comp_label == previous_label + "_1"
        except AssertionError:
            # Both Linear and Lortenz have the same default label
            # If the above check fails, check to see if it's incremented by 2
            if model in ('Linear1D', 'Lorentz1D'):
                assert modelfit_plugin.comp_label == "L_2"
            else:
                raise

    assert len(modelfit_plugin.component_models) == len(MODELS)

    # Test that default equation adds all components together
    # Make sure to remove the trailing '+' sign!
    assert (
        modelfit_plugin.model_equation
        == "".join((param["id"] + "+") for param in modelfit_plugin.component_models)[:-1]
    )


def test_custom_model_labels(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    modelfit_plugin = specviz_helper.app.get_tray_item_from_name('g-model-fitting')

    for model in MODELS:
        # Add one of each model with a unique name
        modelfit_plugin.comp_selected = model
        modelfit_plugin.comp_label = uuid.uuid4().hex
        modelfit_plugin.vue_add_model()

    assert len(modelfit_plugin.component_models) == len(MODELS)

    # Test that default equation adds all components together
    # Make sure to remove the trailing '+' sign!
    assert (
        modelfit_plugin.model_equation
        == "".join((param["id"] + "+") for param in modelfit_plugin.component_models)[:-1]
    )


@pytest.mark.filterwarnings('ignore')
def test_register_model(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    modelfit_plugin = specviz_helper.app.get_tray_item_from_name('g-model-fitting')

    # Test registering a simple linear fit
    modelfit_plugin.comp_selected = 'Linear1D'
    modelfit_plugin.vue_add_model()
    modelfit_plugin.vue_model_fitting()
    assert len(specviz_helper.app.data_collection) == 2

    # Test fitting again overwrites original fit
    modelfit_plugin.vue_model_fitting()
    assert len(specviz_helper.app.data_collection) == 2

    # Test custom model label
    test_label = uuid.uuid4().hex
    modelfit_plugin.results_label = test_label
    modelfit_plugin.vue_model_fitting()
    assert test_label in specviz_helper.app.data_collection


@pytest.mark.filterwarnings('ignore')
def test_register_cube_model(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube)
    modelfit_plugin = cubeviz_helper.app.get_tray_item_from_name('g-model-fitting')

    # Test custom model label
    modelfit_plugin.comp_selected = 'Linear1D'
    modelfit_plugin.vue_add_model()
    test_label = uuid.uuid4().hex
    modelfit_plugin.results_label = test_label
    modelfit_plugin.vue_fit_model_to_cube()
    assert test_label in cubeviz_helper.app.data_collection
