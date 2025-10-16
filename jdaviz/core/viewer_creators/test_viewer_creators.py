

def test_viewer_creator_relevance(deconfigged_helper, spectrum1d, spectrum2d):
    assert len(deconfigged_helper.new_viewers) == 0
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    # 1D Spectrum, Scatter, Histogram
    assert len(deconfigged_helper.new_viewers) == 3
    deconfigged_helper.load(spectrum2d, format='2D Spectrum')
    # 1D Spectrum, 2D Spectrum, Scatter, Histogram
    assert len(deconfigged_helper.new_viewers) == 4


def test_viewer_creation(deconfigged_helper, spectrum1d):
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    assert len(deconfigged_helper.viewers) == 1
    deconfigged_helper.new_viewers['1D Spectrum']()
    assert len(deconfigged_helper.viewers) == 2
