import numpy as np
import bqplot
from astropy.io import fits
from astropy.table import Table
from ipywidgets import GridBox, Layout, HTML, Textarea, Button, ButtonStyle
from bqplot.interacts import PanZoom
# from ipyastroimage import AstroImage
from bqplot_image_gl import ImageGL
from bqplot import ColorScale
from glue.viewers.common.viewer import BaseViewer


class MOSVizWidget(BaseViewer, GridBox):

    LABEL = 'MOSViz Widget'

    def __init__(self, *args, **kwargs):
        BaseViewer.__init__(self, *args, **kwargs)
        self._init_grid()

        self._main_data = None
        self._current_row = None
        self._current_index = None
        self._rows = []

    def _init_grid(self):

        # Set up scales for the spatial x, spatial y, spectral, and flux
        self.scale_x = bqplot.LinearScale(min=0, max=1)
        self.scale_y = bqplot.LinearScale(min=0, max=1)
        self.scale_spec = bqplot.LinearScale(min=0, max=1)
        self.scale_flux = bqplot.LinearScale(min=0, max=1)

        # Set up colorscale
        self.scale_cutout_image = ColorScale(colors=['black', 'white'])
        self.scale_spec2d_image = ColorScale(colors=['black', 'white'])

        # Set up axes
        self.axis_x = bqplot.Axis(scale=self.scale_x, grid_lines='solid', label='x')
        self.axis_y = bqplot.Axis(scale=self.scale_y, grid_lines='solid', label='y', orientation='vertical')

        self.axis_spec = bqplot.Axis(scale=self.scale_spec, grid_lines='solid', label='spec')
        self.axis_flux = bqplot.Axis(scale=self.scale_flux, grid_lines='solid', label='flux', orientation='vertical')

        # Set up bqplot viewers
        # =====================

        # Cutout
        # ------
        self.fig_cutout = bqplot.Figure(scales={'x': self.scale_x,
                                                'y': self.scale_y},
                                        axes=[self.axis_x, self.axis_y],
                                        layout={'width': '500px',
                                                'height': '400px'}
                                        )
        self.fig_cutout.interaction = PanZoom(scales={'x': [self.scale_x],
                                                      'y': [self.scale_y]})

        # Spec 2d
        # -------
        self.fig_spec2d = bqplot.Figure(scales={'x': self.scale_spec,
                                                'y': self.scale_y},
                                        axes=[self.axis_spec, self.axis_y],
                                        layout={'width': '500px',
                                                'height': '400px'})

        self.fig_spec2d.interaction = PanZoom(scales={'x': [self.scale_spec],
                                                      'y': [self.scale_y]})

        # Spec 1d
        # -------
        self.fig_spec1d = bqplot.Figure(scales={'x': self.scale_spec,
                                                'y': self.scale_flux},
                                        axes=[self.axis_spec, self.axis_flux],
                                        layout={'width': '500px', 'height': '400px'})

        self.fig_spec1d.interaction = PanZoom(scales={'x': [self.scale_spec],
                                                      'y': [self.scale_flux]})

        # info box
        # --------
        self.info_box = Textarea(value='Hello World')
        self.info_box.layout.height = '100%'
        self.info_box.layout.width = '100%'
        self.info_box.layout.align_self = 'flex-end'

        # Set up content of figures
        # =========================

        self.cutout_mark = ImageGL(scales={'x': self.scale_x,
                                              'y': self.scale_y,
                                              'image': self.scale_cutout_image})
        self.fig_cutout.marks = [self.cutout_mark]

        self.spec2d_mark = ImageGL(scales={'x': self.scale_spec,
                                              'y': self.scale_y,
                                              'image': self.scale_spec2d_image})
        self.fig_spec2d.marks = [self.spec2d_mark]

        self.spec1d_mark = bqplot.Lines(scales={'x': self.scale_spec, 'y': self.scale_flux},
                                        x=[], y=[])
        self.fig_spec1d.marks = [self.spec1d_mark]

        GridBox.__init__(self,
                         [self.fig_cutout, HTML(), self.fig_spec2d,
                          HTML(), HTML(), HTML(),
                          self.info_box, HTML(), self.fig_spec1d],
                         layout=Layout(width='100%',
                                       grid_template_columns='35% 5% 35%',
                                       grid_template_rows='30% 5% 30%',
                                       grid_gap='30px 30px'))

        self.layout.justify_content = "center"
        self.layout.align_items = "center"

    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    def current_index(self, value):
        value = int(value)
        if 0 <= value < len(self._rows):
            self._current_index = value
            self._current_row = self._rows[value]
            self.load_current_row()

    @property
    def current_row(self):
        return self._current_row

    def next_row(self):
        self.current_index += 1

    def previous_row(self):
        self.current_index -= 1

    def add_data(self, data):

        if self._main_data is None:
            self._main_data = data
        else:
            raise Exception('data is already set')

        cell_data = []

        for i in self._main_data.main_components:
            cell_data.append(list(self._main_data.get_data(i)))

        cell_data = [list(col) for col in zip(*cell_data)]

        self._rows = cell_data

        if len(cell_data) > 0:
            self.current_index = 0

        return True

    def load_current_row(self):
        if self._current_row is None:
            return
        cutout = self._current_row[5]
        spec1d = self._current_row[3]
        spec2d = self._current_row[4]

        s1d = Table.read(spec1d, hdu=1)

        # The following shows how to set up the image and spectrum data
        cutout_data = fits.getdata(cutout)
        self.cutout_mark.image = cutout_data
        self.cutout_mark.x = (-0.5, 15.5)
        self.cutout_mark.y = (-0.5, 15.5)

        d = fits.getdata(spec2d)
        d = np.choose(d > 1, [0.1, d])
        spec2d_data = np.log10(d)
        self.spec2d_mark.image = spec2d_data
        self.spec2d_mark.x = (min(s1d['WAVELENGTH']), max(s1d['WAVELENGTH']))
        self.spec2d_mark.y = (-0.5, 15.5)

        self.spec1d_mark.x = s1d['WAVELENGTH']
        self.spec1d_mark.y = s1d['FLUX']

        # Adjust limits for all scales - note that x and y are in pixels, spec is in wav units, and flux in flux units

        self.scale_x.min = 0
        self.scale_x.max = 15.5

        self.scale_y.min = -0.5
        self.scale_y.max = 15.5

        self.scale_spec.min = float(min(s1d['WAVELENGTH']))
        self.scale_spec.max = float(max(s1d['WAVELENGTH']))

        self.scale_flux.min = float(min(s1d['FLUX']))
        self.scale_flux.max = float(max(s1d['FLUX']))

        # Adjust color scales

        self.scale_cutout_image.min = float(cutout_data.min())
        self.scale_cutout_image.max = float(cutout_data.max())

        self.scale_spec2d_image.min = float(spec2d_data.min())
        self.scale_spec2d_image.max = float(spec2d_data.mean())

        # Info box
        string = "\n".join([str(i) for i in self.current_row])
        self.info_box.value = string

