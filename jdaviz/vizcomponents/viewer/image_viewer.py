from astropy.io import fits
from reproject import reproject_interp

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

        # these should be somehow accessible by
        # the user, from the notebook level.
        self.hdu = 1
        self.vmin = 0.
        self.vmax = 10.

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

        self.fig_image_1 = Figure(title='Reference',
                                  scales={'x': self.scale_x,
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

        self.fig_image_2 = Figure(title='Reprojected',
                                  scales={'x': self.scale_x,
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
                                       grid_template_rows='20% 30%',
                                       grid_gap='30px 30px'))

        self.layout.justify_content = "center"
        self.layout.align_items = "center"

    def add_data(self, data):
        '''
        Adds the two images to be displayed, re-projecting the
        second image on the coordinate system of the first image.

        :param data: 2-element sequence
         with file names for reference image, and image to
         be re-projected.
        :return: True
        '''
        hdu1 = fits.open(data[0])[self.hdu]
        hdu2 = fits.open(data[1])[self.hdu]
        array, footprint = reproject_interp(hdu2, hdu1.header)

        image_1_data = hdu1.data
        self.image_1_mark.image = image_1_data
        self.image_1_mark.x = (-0.5, 20.)
        self.image_1_mark.y = (-0.5, 20.)

        self.scale_image_1.min = float(image_1_data.min())
        self.scale_image_1.max = float(image_1_data.max())
        if self.vmin is not None and self.vmax is not None:
            self.scale_image_1.min = self.vmin
            self.scale_image_1.max = self.vmax

        image_2_data = array
        self.image_2_mark.image = image_2_data
        self.image_2_mark.x = (-0.5, 20.)
        self.image_2_mark.y = (-0.5, 20.)

        self.scale_image_2.min = float(image_2_data.min())
        self.scale_image_2.max = float(image_2_data.max())
        if self.vmin is not None and self.vmax is not None:
            self.scale_image_2.min = self.vmin
            self.scale_image_2.max = self.vmax

        self.scale_x.min = 0
        self.scale_x.max = 20.5

        self.scale_y.min = -0.5
        self.scale_y.max = 20.5

        return True



