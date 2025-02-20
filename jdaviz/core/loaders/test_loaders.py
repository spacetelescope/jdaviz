import pytest
from jdaviz.core.registries import loader_resolver_registry


def test_loaders_registry(specviz_helper):
    with pytest.raises(NotImplementedError):
        specviz_helper.loaders
    specviz_helper.app.state.dev_loaders = True
    # built-in loaders: file, url
    assert len(specviz_helper.loaders) == len(loader_resolver_registry.members)


def test_resolver_url(specviz_helper):
    specviz_helper.app.state.dev_loaders = True

    loader = specviz_helper.loaders['url']

    # no url, no valid formats
    assert len(loader.format.choices) == 0

    # non-valid input
    loader.url = 'not-valid-url'
    assert len(loader.format.choices) == 0

    loader.url = 'https://stsci.box.com/shared/static/exnkul627fcuhy5akf2gswytud5tazmw.fits'  # noqa
    assert len(loader.format.choices) == 2  # may change with future importers
    assert loader.format.selected == '2D Spectrum'

    # test target filtering
    assert len(loader.target.choices) > 1
    assert loader.target.selected == 'Any'
    loader.target = loader.target.choices[-1]
    assert len(loader.format.choices) == 1

    loader.target = 'Any'
    assert len(loader.format.choices) == 2
    loader.format = '2D Spectrum'

    assert len(specviz_helper.app.data_collection) == 0

    loader.importer()

    assert len(specviz_helper.app.data_collection) == 1
