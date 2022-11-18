import pytest

from jdaviz import utils


@pytest.mark.parametrize("test_input,expected", [(0, 'a'), (1, 'b'), (25, 'z'), (26, 'aa'),
                                                 (701, 'zz'), (702, '{a')])
def test_alpha_index(test_input, expected):
    assert utils.alpha_index(test_input) == expected


def test_alpha_index_exceptions():
    with pytest.raises(TypeError, match="index must be an integer"):
        utils.alpha_index(4.2)
    with pytest.raises(ValueError, match="index must be positive"):
        utils.alpha_index(-1)
