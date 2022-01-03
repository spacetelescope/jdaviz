from specutils import Spectrum1D

from jdaviz.configs.cubeviz.plugins.moment_maps.moment_maps import MomentMap


def test_moment_calculation(cubeviz_app, spectrum1d_cube):
    app = cubeviz_app.app
    dc = app.data_collection
    app.add_data(spectrum1d_cube, 'test')

    mm = MomentMap(app=app)
    mm._subset_selected = 'None'
    mm._on_data_updated(None)

    mm._on_data_selected({'new': 'test'})
    mm._on_subset_selected({'new': None})

    mm.n_moment = 0
    mm.vue_calculate_moment()

    assert mm.moment_available
    assert dc[1].label == 'Moment 0: test'
    assert dc[1].get_object(cls=Spectrum1D, statistic=None).shape == (4, 2, 2)
