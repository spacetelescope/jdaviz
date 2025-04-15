from astropy.coordinates import SkyCoord
from astropy.table import QTable
from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.table import TableViewer

from jdaviz.core.events import (AddDataToViewerMessage,
                                RemoveDataFromViewerMessage,
                                TableClickMessage)
from jdaviz.core.astrowidgets_api import AstrowidgetsImageViewerMixin
from jdaviz.core.registries import viewer_registry
from jdaviz.core.freezable_state import FreezableBqplotImageViewerState
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin
from jdaviz.configs.specviz.plugins.viewers import Spectrum1DViewer, Spectrum2DViewer

__all__ = ['MosvizImageView', 'MosvizProfile2DView',
           'MosvizProfileView', 'MosvizTableViewer']


@viewer_registry("mosviz-image-viewer", label="Image 2D (Mosviz)")
class MosvizImageView(JdavizViewerMixin, BqplotImageView, AstrowidgetsImageViewerMixin):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom'],
                    ['jdaviz:panzoom'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = None
    _state_cls = FreezableBqplotImageViewerState

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_astrowidgets_api()
        self._subscribe_to_layers_update()

        self.state.show_axes = False  # Axes are wrong anyway
        self.figure.fig_margin = {'left': 0, 'bottom': 0, 'top': 0, 'right': 0}

        self.data_menu._obj.dataset.add_filter('is_image_not_spectrum')
        self.data_menu._obj.dataset.add_filter('same_mosviz_row')

    def data(self, cls=None):
        return [layer_state.layer.get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]

    # NOTE: This is currently only for debugging. It is not used in app.
    def _mark_targets(self):
        table_data = self.jdaviz_app.data_collection['MOS Table']

        if ("R.A." not in table_data.component_ids() or
                "Dec." not in table_data.component_ids()):
            return

        ra = table_data["R.A."]
        dec = table_data["Dec."]
        sky = SkyCoord(ra, dec, unit='deg')
        t = QTable({'coord': sky})
        self.add_markers(t, use_skycoord=True, marker_name='Targets')


@viewer_registry("mosviz-profile-2d-viewer", label="Spectrum 2D (Mosviz)")
class MosvizProfile2DView(Spectrum2DViewer):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['mosviz:homezoom'],
                    ['mosviz:boxzoom', 'mosviz:xrangezoom', 'jdaviz:yrangezoom'],
                    ['mosviz:panzoom', 'mosviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    _state_cls = FreezableBqplotImageViewerState

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_menu._obj.dataset.add_filter('same_mosviz_row')


@viewer_registry("mosviz-profile-viewer", label="Profile 1D")
class MosvizProfileView(Spectrum1DViewer):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['mosviz:homezoom'],
                    ['mosviz:boxzoom', 'mosviz:xrangezoom', 'jdaviz:yrangezoom'],  # noqa
                    ['mosviz:panzoom', 'mosviz:panzoom_x', 'jdaviz:panzoom_y'],  # noqa
                    ['bqplot:xrange'],
                    ['jdaviz:selectline'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_menu._obj.dataset.add_filter('same_mosviz_row')


@viewer_registry("mosviz-table-viewer", label="Table (Mosviz)")
class MosvizTableViewer(TableViewer, JdavizViewerMixin):
    def __init__(self, session, *args, **kwargs):
        super().__init__(session, *args, **kwargs)

        self.figure_widget.observe(self._on_row_selected, names=['highlighted'])
        # enable scrolling: # https://github.com/glue-viz/glue-jupyter/pull/287
        self.widget_table.scrollable = True

        self._selected_data = {}
        self._shared_image = False
        self.row_selection_in_progress = False

        self._on_row_selected_begin = None
        self._on_row_selected_end = None

    @property
    def _default_table_viewer_reference_name(self):
        return self.jdaviz_helper._default_table_viewer_reference_name

    @property
    def _default_spectrum_viewer_reference_name(self):
        return self.jdaviz_helper._default_spectrum_viewer_reference_name

    @property
    def _default_spectrum_2d_viewer_reference_name(self):
        return self.jdaviz_helper._default_spectrum_2d_viewer_reference_name

    @property
    def _default_image_viewer_reference_name(self):
        return self.jdaviz_helper._default_image_viewer_reference_name

    def redraw(self):

        # Overload to hide components - we do this via overloading instead of
        # checking for changes in self.figure_widget.data because some components
        # might be added inplace to the dataset.

        if self.figure_widget.data is None:
            self.figure_widget.hidden_components = []
        else:
            components_str = [cid.label for cid in self.figure_widget.data.main_components]
            hidden = []
            for colname in ('Images', '1D Spectra', '2D Spectra'):
                if colname in components_str:
                    hidden.append(self.figure_widget.data.id[colname])
            self.figure_widget.hidden_components = hidden

        super().redraw()

    @property
    def nrows(self):
        return self.widget_table.get_state()['total_length']

    @property
    def current_row(self):
        return self.widget_table.highlighted

    def select_row(self, n):
        if n < 0 or n >= self.nrows:
            raise ValueError("n must be between 0 and {}".format(self.nrows-1))

        # compute and set the appropriate page
        # NOTE: traitlets won't detect internal changes to a dict
        options = self.widget_table.get_state()['options']
        page = int(n / options['itemsPerPage']) + 1
        if options['page'] != page:
            self.widget_table.set_state({'options': {**options, 'page': page}})
            self.widget_table.send_state()
        # select and highlight the row
        self.widget_table.highlighted = n

    def next_row(self):
        current_row = self.current_row
        new_row = 0 if current_row == self.nrows - 1 else current_row + 1
        self.select_row(new_row)

    def prev_row(self):
        current_row = self.current_row
        new_row = self.nrows - 1 if current_row == 0 else current_row - 1
        self.select_row(new_row)

    def _on_row_selected(self, event):
        if self._on_row_selected_begin:
            self._on_row_selected_begin(event)

        self.row_selection_in_progress = True
        # Grab the index of the latest selected row
        selected_index = event['new']
        mos_data = self.session.data_collection['MOS Table']

        # plugin data entries: select all in new row, deselect all others
        for data_item in self.jdaviz_app.data_collection:
            if data_item.meta.get('Plugin') is not None:
                if data_item.meta.get('mosviz_row') == selected_index:
                    self.session.hub.broadcast(AddDataToViewerMessage(
                        self._default_spectrum_viewer_reference_name, data_item.label, sender=self))
                else:
                    self.session.hub.broadcast(RemoveDataFromViewerMessage(
                        self._default_spectrum_viewer_reference_name, data_item.label, sender=self))

        for component in mos_data.components:
            comp_data = mos_data.get_component(component).data
            selected_data = comp_data[selected_index]

            if component.label == '1D Spectra':
                prev_data = self._selected_data.get(self._default_spectrum_viewer_reference_name)
                if prev_data != selected_data:
                    if prev_data:
                        # This covers the cases where data is unit converted
                        # and the name is modified
                        all_prev_data = [x
                                         for x in self.session.data_collection.labels
                                         if prev_data in x]
                        for modified_prev_data in all_prev_data:
                            if modified_prev_data:
                                remove_data_from_viewer_message = RemoveDataFromViewerMessage(
                                    self._default_spectrum_viewer_reference_name,
                                    modified_prev_data, sender=self
                                )
                                # reset the counter in the spectrum viewer's color cycler
                                # so that the newly selected row is displayed in gray and
                                # future additions will have other colors:
                                spectrum_viewer = self.jdaviz_app.get_viewer(
                                    self._default_spectrum_viewer_reference_name
                                )
                                spectrum_viewer.color_cycler.reset()

                                self.session.hub.broadcast(remove_data_from_viewer_message)

                    add_data_to_viewer_message = AddDataToViewerMessage(
                        self._default_spectrum_viewer_reference_name,
                        selected_data, sender=self
                    )
                    self.session.hub.broadcast(add_data_to_viewer_message)

                    self._selected_data[
                        self._default_spectrum_viewer_reference_name
                    ] = selected_data

            if component.label == '2D Spectra':
                prev_data = self._selected_data.get(self._default_spectrum_2d_viewer_reference_name)
                if prev_data != selected_data:
                    if prev_data:
                        remove_data_from_viewer_message = RemoveDataFromViewerMessage(
                            self._default_spectrum_2d_viewer_reference_name,
                            prev_data, sender=self
                        )
                        self.session.hub.broadcast(remove_data_from_viewer_message)

                    add_data_to_viewer_message = AddDataToViewerMessage(
                        self._default_spectrum_2d_viewer_reference_name,
                        selected_data, sender=self
                    )
                    self.session.hub.broadcast(add_data_to_viewer_message)

                    self._selected_data[
                        self._default_spectrum_2d_viewer_reference_name
                    ] = selected_data

            if component.label == 'Images':
                prev_data = self._selected_data.get(self._default_image_viewer_reference_name)
                if prev_data != selected_data:
                    if prev_data:
                        remove_data_from_viewer_message = RemoveDataFromViewerMessage(
                            self._default_image_viewer_reference_name, prev_data, sender=self)
                        self.session.hub.broadcast(remove_data_from_viewer_message)

                    add_data_to_viewer_message = AddDataToViewerMessage(
                        self._default_image_viewer_reference_name, selected_data, sender=self)
                    self.session.hub.broadcast(add_data_to_viewer_message)

                    self._selected_data[self._default_image_viewer_reference_name] = selected_data

        message = TableClickMessage(selected_index=selected_index,
                                    shared_image=self._shared_image,
                                    sender=self)
        self.session.hub.broadcast(message)

        self.row_selection_in_progress = False

        if self._on_row_selected_end:
            self._on_row_selected_end(event)

    def set_plot_axes(self, *args, **kwargs):
        return
