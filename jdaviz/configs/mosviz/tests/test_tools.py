from numpy.testing import assert_allclose


def test_viewer_axis_link(mosviz_helper, mos_spectrum1d, mos_spectrum2d):
    label1d = "Test 1D Spectrum"
    mosviz_helper.load_1d_spectra(mos_spectrum1d, data_labels=label1d)

    label2d = "Test 2D Spectrum"
    mosviz_helper.load_2d_spectra(mos_spectrum2d, data_labels=label2d, add_redshift_column=True)

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.select_row(0)

    s2dv = mosviz_helper.app.get_viewer('spectrum-2d-viewer')
    sv = mosviz_helper.app.get_viewer('spectrum-viewer')

    def _viewer_limits(v):
        return (v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max)

    t = sv.toolbar.tools['mosviz:boxzoom']
    s2dv_orig_limits = _viewer_limits(s2dv)
    assert_allclose(s2dv_orig_limits, (-0.5, 14.5, -0.5, 1023.5))

    sv_orig_limits = _viewer_limits(sv)
    assert_allclose(sv_orig_limits, (1e-06, 1.4999999999999999e-05, -1.9132802166577978, 1.5792128295073915))  # noqa

    t.activate()
    # changes to sv should map to s2dv
    sv.state.x_min = 1e-5
    assert_allclose(_viewer_limits(sv), (1e-05, 1.4999999999999999e-05, -1.9132802166577978, 1.5792128295073915))  # noqa
    # shift in x_max caused by original padding
    assert_allclose(_viewer_limits(s2dv), (9.000000000000002, 14.0, -0.5, 1023.5))

    t2 = s2dv.toolbar.tools['mosviz:panzoom']
    t2.activate()
    # should have deactivated the tool in the spectrum-viewer
    assert sv.toolbar.active_tool_id is None
    # and now changes to s2dv should map to sv
    s2dv.state.x_min = -0.5
    assert_allclose(_viewer_limits(s2dv), (-0.5, 14.0, -0.5, 1023.5))
    assert_allclose(_viewer_limits(sv), (5.000000000000006e-07, 1.4999999999999999e-05, -1.9132802166577978, 1.5792128295073915))  # noqa
