import pytest

from jdaviz import utils


def test_alpha_index():
    assert utils.alpha_index(0) == 'a'
    assert utils.alpha_index(1) == 'b'
    assert utils.alpha_index(25) == 'z'
    assert utils.alpha_index(26) == 'aa'
    assert utils.alpha_index(701) == 'zz'
    with pytest.raises(NotImplementedError):
        utils.alpha_index(702)
