from jdaviz import Specviz


def test_helper(specviz2d_helper, spectrum1d):
    specviz2d_helper.load_data(spectrum_1d=spectrum1d)
    assert isinstance(specviz2d_helper.specviz, Specviz)
