import os
import tempfile
import pytest
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


def test_load_write_load():
    # load the JWST flag map
    flag_map = load_flag_map('jwst')

    with tempfile.TemporaryDirectory() as tmp_dir:

        # write out the flag map to a temporary CSV file
        path = os.path.join(tmp_dir, 'test_flag_map.csv')
        write_flag_map(flag_map, path)

        # load that temporary CSV file back in
        reloaded_flag_map = load_flag_map(path=path)

        # confirm all values round-trip successfully:
        for flag, orig_value in flag_map.items():
            assert orig_value == reloaded_flag_map[flag]
