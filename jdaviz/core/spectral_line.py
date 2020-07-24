from bqplot.marks import Lines

class SpectralLine(Lines):
    """
    Subclass on bqplot Lines, mostly so that we can erase spectral lines
    by eliminating any SpectralLines objects from a figures marks list. Also
    lets us do wavelength redshifting here on mark creation.
    """
    def __init__(self, rest_value, scales, redshift=None, name=None, **kwargs):
        self._rest_value = rest_value
        self._redshift = redshift
        self.name = name
        self.table_index = kwargs.pop("table_index", None)

        if redshift is not None:
            x = rest_value*(1+redshift)
            x_coords = [x, x]
        else:
            x_coords = [rest_value, rest_value]

        y_coords = [scales['y'].min, scales['y'].max]

        super().__init__(x=x_coords, y=y_coords, scales=scales, stroke_width=1,
                       fill='none', close_path=False, **kwargs)
