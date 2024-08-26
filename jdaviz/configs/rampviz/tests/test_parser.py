

def test_load_rectangular_ramp(rampviz_helper, jwst_level_1b_rectangular_ramp):
    rampviz_helper.load_data(jwst_level_1b_rectangular_ramp)

    # drop the integration axis
    original_cube_shape = jwst_level_1b_rectangular_ramp.shape[1:]

    # on ramp cube load (1), the parser loads a diff cube (2) and
    # the ramp extraction plugin produces a default extraction (3):
    assert len(rampviz_helper.app.data_collection) == 3

    parsed_cube_shape = rampviz_helper.app.data_collection[0].shape
    assert parsed_cube_shape == (
        original_cube_shape[2], original_cube_shape[1], original_cube_shape[0]
    )


def test_load_nirspec_irs2(rampviz_helper, jwst_level_1b_rectangular_ramp):
    # update the Level1bModel to have the header cards that are
    # expected for an exposure from NIRSpec in IRS2 readout mode
    jwst_level_1b_rectangular_ramp.update(
        {
            'meta': {
                '_primary_header': {
                    "TELESCOP": "JWST",
                    "INSTRUME": "NIRSPEC",
                    "READPATT": "NRSIRS2"
                }
            }
        }
    )
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
