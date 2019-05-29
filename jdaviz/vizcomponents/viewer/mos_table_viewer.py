import ipysheet
from ipywidgets import Textarea
from glue.core import message as msg
from glue.viewers.common.viewer import BaseViewer
from glue.utils.colors import alpha_blend_colors


class MOSVizTable(BaseViewer):
    LABEL = 'Table Viewer'

    def __init__(self, data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._main_data = data
        self._area = Textarea()
        self._sheet = ipysheet.sheet(column_headers=[x.label for x in data.main_components])

        self._add_data()

        self.register_to_hub(kwargs['session'].hub)

    def register_to_hub(self, hub):

        super().register_to_hub(hub)

        hub.subscribe(self, msg.SubsetCreateMessage,
                      handler=self._rerender_table)

        hub.subscribe(self, msg.SubsetUpdateMessage,
                      handler=self._rerender_table)

        hub.subscribe(self, msg.SubsetDeleteMessage,
                      handler=self._rerender_table)

    def _add_data(self):

        cell_data = []

        for i in self._main_data.main_components:
            cell_data.append(list(self._main_data.get_data(i)))

        cell_data = [list(col) for col in zip(*cell_data)]
        assert max(map(len, cell_data)) == min(map(len, cell_data))

        num_row, num_col = len(cell_data), len(cell_data[0])

        self._sheet.columns = num_col
        self._sheet.rows = num_row

        self.rows = []
        for i in range(len(cell_data)):
            self.rows.append(ipysheet.row(i, cell_data[i]))

        return True

    def remove_data(self, data):
        raise NotImplementedError()

    def _rerender_table(self, *args, **kwargs):
        colors = [[] for i in range(self._main_data.shape[0])]
        for sub in self._main_data.subsets:
            mask = sub.to_mask()
            sub.style.color
            for i in range(len(mask)):
                if mask[i]:
                    colors[i].append(sub.style.color)

        styles = []
        for i, c in enumerate(colors):
            if len(c) > 0:
                color = alpha_blend_colors(c, additional_alpha=0.5)
                style = {'backgroundColor': "rgba({}, {}, {}, {})".format(*color)}
            else:
                style = {}
            styles.append(style)

        for i, s in enumerate(styles):
            self.rows[i].style = s

    def _select_row(self, *args, idx=None, **kwargs):
        colors = [[] for i in range(self._main_data.shape[0])]

        styles = []
        for i, c in enumerate(colors):
            if i == idx:
                style = {'backgroundColor': "rgba({}, {}, {}, {})".format(100, 100, 100, 0.5)}
            else:
                style = {}
            styles.append(style)

        for i, s in enumerate(styles):
            self.rows[i].style = s

    def show(self):
        return self._sheet