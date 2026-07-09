import pytest
from jdaviz.configs.imviz.plugins.parsers import HAS_ROMAN_DATAMODELS


@pytest.mark.skipif(not HAS_ROMAN_DATAMODELS, reason="roman_datamodels is not installed")
def test_load_data_roman(deconfigged_helper, roman_level_1_ramp):
    deconfigged_helper.load(roman_level_1_ramp)

    # on ramp cube load (1), the parser loads a diff cube (2) and
    # the ramp extraction plugin produces a default extraction (3):
    assert len(deconfigged_helper._app.data_collection) == 3

    # each viewer should have one loaded data entry:
    for refname in '3D Ramp, 3D Ramp Diff, Ramp Integration'.split(', '):
        viewer = deconfigged_helper._app.get_viewer(refname)
        assert len(viewer.state.layers) == 1

    assert viewer.axis_x.label == 'Group'
    assert viewer.axis_y.label == 'DN'


def test_load_data_jwst(deconfigged_helper, jwst_level_1b_ramp):
    deconfigged_helper.load(jwst_level_1b_ramp)

    # on ramp cube load (1), the parser loads a diff cube (2) and
    # the ramp extraction plugin produces a default extraction (3):
    assert len(deconfigged_helper._app.data_collection) == 3

    # each viewer should have one loaded data entry:
    for refname in '3D Ramp, 3D Ramp Diff, Ramp Integration'.split(', '):
        viewer = deconfigged_helper._app.get_viewer(refname)
        assert len(viewer.state.layers) == 1

    assert viewer.axis_x.label == 'Group'
    assert viewer.axis_y.label == 'DN'
