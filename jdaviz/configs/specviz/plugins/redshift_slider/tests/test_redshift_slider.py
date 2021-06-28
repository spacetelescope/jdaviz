from .. import redshift_slider as rs


def test_bounds_orderly_new_val_greater_than(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    redshift_slider = rs.RedshiftSlider
    redshift_slider.max_value = 100000
    redshift_slider.min_value = 0
    redshift_slider._set_bounds_orderly(redshift_slider, 0, 100500, 100500)

    assert redshift_slider.max_value == 100500
    assert redshift_slider.min_value == 0
    assert redshift_slider.slider == 100500


def test_bounds_orderly_new_val_less_than(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    redshift_slider = rs.RedshiftSlider
    redshift_slider.max_value = 100000
    redshift_slider.min_value = 0
    redshift_slider._set_bounds_orderly(redshift_slider, -100500, 0, -500)

    assert redshift_slider.max_value == 0
    assert redshift_slider.min_value == -100500
    assert redshift_slider.slider == -500


def test_bounds_orderly_new_val_else(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    redshift_slider = rs.RedshiftSlider
    redshift_slider.max_value = 200000
    redshift_slider.min_value = 0
    slider = redshift_slider.slider
    redshift_slider._set_bounds_orderly(redshift_slider, 0, 100500, 100500)

    assert redshift_slider.max_value == 100500
    assert redshift_slider.min_value == 0
    assert redshift_slider.slider == slider
