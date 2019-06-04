import bqplot

from astropy.io import fits

from ipywidgets import GridBox, Layout, HTML
from bqplot.interacts import PanZoom
from bqplot_image_gl import ImageGL
from bqplot import Figure, Axis, LinearScale, ColorScale

from glue.viewers.common.viewer import BaseViewer


class ImageVizWidget(BaseViewer, GridBox):

    LABEL = 'ImageViz Widget'

    def __init__(self, *args, **kwargs):
        BaseViewer.__init__(self, *args, **kwargs)
        self._init_gui()

        self._main_data = None

    def _init_gui(self):

        # we use bqplot to exploit its ability to lock together
        # the plot axis of separate figures.

        self.scale_x = LinearScale(min=0, max=1)
        self.scale_y = LinearScale(min=0, max=1)

        self.scale_image_1 = ColorScale(colors=['black', 'white'])
        self.scale_image_2 = ColorScale(colors=['black', 'white'])

        self.axis_x = Axis(scale=self.scale_x, grid_lines='solid', label='x')
        self.axis_y = Axis(scale=self.scale_y, grid_lines='solid', label='y',
                           orientation='vertical')

        self.fig_image_1 = Figure(scales={'x': self.scale_x,
                                          'y': self.scale_y},
                                  axes=[self.axis_x, self.axis_y],
                                  layout={'width': '500px',
                                          'height': '500px'}
                                  )
        self.fig_image_1.interaction = PanZoom(scales={'x': [self.scale_x],
                                                       'y': [self.scale_y]})
        self.image_1_mark = ImageGL(scales={'x': self.scale_x,
                                            'y': self.scale_y,
                                            'image': self.scale_image_1})
        self.fig_image_1.marks = [self.image_1_mark]

        self.fig_image_2 = Figure(scales={'x': self.scale_x,
                                          'y': self.scale_y},
                                  axes=[self.axis_x, self.axis_y],
                                  layout={'width': '500px',
                                          'height': '500px'}
                                  )
        self.fig_image_2.interaction = PanZoom(scales={'x': [self.scale_x],
                                                       'y': [self.scale_y]})
        self.image_2_mark = ImageGL(scales={'x': self.scale_x,
                                            'y': self.scale_y,
                                            'image': self.scale_image_2})
        self.fig_image_2.marks = [self.image_2_mark]

        GridBox.__init__(self,
                         [HTML(), HTML(),HTML(),
                         self.fig_image_1, HTML(), self.fig_image_2],
                         layout=Layout(width='100%',
                                       grid_template_columns='35% 5% 35%',
                                       grid_template_rows='10% 30%',
                                       grid_gap='30px 30px'))

        self.layout.justify_content = "center"
        self.layout.align_items = "center"

    def add_data(self, data):

        # in this simple demo version, data is a two-element sequence
        # with the full path names of the two images to be displayed.

        image_1_data = fits.getdata(data[0])
        self.image_1_mark.image = image_1_data
        self.image_1_mark.x = (-0.5, 20.)
        self.image_1_mark.y = (-0.5, 20.)

        self.scale_image_1.min = float(image_1_data.min())
        self.scale_image_1.max = float(image_1_data.max())

        image_2_data = fits.getdata(data[1])
        self.image_2_mark.image = image_2_data
        self.image_2_mark.x = (-0.5, 20.)
        self.image_2_mark.y = (-0.5, 20.)

        self.scale_image_2.min = float(image_2_data.min())
        self.scale_image_2.max = float(image_2_data.max())

        self.scale_x.min = 0
        self.scale_x.max = 20.5

        self.scale_y.min = -0.5
        self.scale_y.max = 20.5

        return True


