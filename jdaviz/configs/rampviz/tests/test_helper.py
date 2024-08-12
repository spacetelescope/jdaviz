

def test_load_data(rampviz_helper, roman_level_1_ramp):
    rampviz_helper.load_data(roman_level_1_ramp)

    # on ramp cube load (1), the parser loads a diff cube (2) and
    # the ramp extraction plugin produces a default extraction (3):
    assert len(rampviz_helper.app.data_collection) == 3

    # each viewer should have one loaded data entry:
    for refname in 'group-viewer, diff-viewer, integration-viewer'.split(', '):
        viewer = rampviz_helper.app.get_viewer(refname)
        assert len(viewer.state.layers) == 1

    assert viewer.axis_x.label == 'Group'
    assert viewer.axis_y.label == 'DN'
