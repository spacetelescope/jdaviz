

def test_load_rectangular_ramp(rampviz_helper, jwst_level_1b_rectangular_ramp):
    rampviz_helper.load_data(jwst_level_1b_rectangular_ramp)

    # drop the integration axis
    original_cube_shape = jwst_level_1b_rectangular_ramp.shape[1:]

    # on ramp cube load (1), the parser loads a diff cube (2) and
    # the ramp extraction plugin produces a default extraction (3):
    assert len(rampviz_helper.app.data_collection) == 3

    parsed_cube_shape = rampviz_helper.app.data_collection[0].shape
    assert parsed_cube_shape == (
        original_cube_shape[1], original_cube_shape[2], original_cube_shape[0]
    )


def test_load_level_1_and_2(
        rampviz_helper,
        jwst_level_1b_rectangular_ramp,
        jwst_level_2c_rate_image
):
    # load level 1 ramp and level 2 rate image
    rampviz_helper.load_data(jwst_level_1b_rectangular_ramp)
    rampviz_helper.load_data(jwst_level_2c_rate_image)

    # confirm that a "level-2" viewer is created, and that
    # the rate image is loaded into it
    assert len(rampviz_helper.viewers) == 4
    assert 'level-2' in rampviz_helper.viewers

    layers = rampviz_helper.app.get_viewer('level-2').layers
    assert len(layers) == 1
