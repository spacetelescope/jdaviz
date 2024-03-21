import pytest
import numpy as np

from stdatamodels.jwst.datamodels.dqflags import pixel as pixel_jwst

from jdaviz.configs.imviz.plugins.parsers import HAS_ROMAN_DATAMODELS
from jdaviz.configs.default.plugins.data_quality.dq_utils import (
    load_flag_map, write_flag_map
)


@pytest.mark.parametrize(
    "mission_or_instrument, flag, name,",
    [['jwst', 26, 'OPEN'],
     ['roman', 26, 'RESERVED_5'],
     ['jwst', 15, 'TELEGRAPH'],
     ['roman', 15, 'TELEGRAPH']]
)
def test_flag_map_utils(mission_or_instrument, flag, name):
    flag_map = load_flag_map(mission_or_instrument)
    assert flag_map[flag]['name'] == name


def test_load_write_load(tmp_path):
    # load the JWST flag map
    flag_map = load_flag_map('jwst')

    # write out the flag map to a temporary CSV file
    path = tmp_path / 'test_flag_map.csv'
    write_flag_map(flag_map, path)

    # load that temporary CSV file back in
    reloaded_flag_map = load_flag_map(path=path)

    # confirm all values round-trip successfully:
    for flag, orig_value in flag_map.items():
        assert orig_value == reloaded_flag_map[flag]


def test_jwst_against_stdatamodels():
    # compare our flag map against the flag map dictionary in `stdatamodels`:
    flag_map_loaded = load_flag_map('jwst')

    flag_map_expected = {
        int(np.log2(flag)): {'name': name}
        for name, flag in pixel_jwst.items() if flag > 0
    }

    # check no keys are missing in either flag map:
    assert len(set(flag_map_loaded.keys()) - set(flag_map_expected.keys())) == 0

    for flag in flag_map_expected:
        assert flag_map_loaded[flag]['name'] == flag_map_expected[flag]['name']


@pytest.mark.skipif(not HAS_ROMAN_DATAMODELS, reason="roman_datamodels is not installed")
def test_roman_against_rdm():
    # compare our flag map against the flag map dictionary in `roman_datamodels`:
    from roman_datamodels.dqflags import pixel as pixel_roman

    flag_map_loaded = load_flag_map('roman')

    flag_map_expected = {
        int(np.log2(p.value)): {'name': p.name}
        for p in pixel_roman if p.value > 0
    }

    # check no keys are missing in either flag map:
    assert len(set(flag_map_loaded.keys()) - set(flag_map_expected.keys())) == 0

    for flag in flag_map_expected:
        assert flag_map_loaded[flag]['name'] == flag_map_expected[flag]['name']
