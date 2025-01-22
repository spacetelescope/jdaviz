import numpy as np
import astropy.units as u
from functools import cached_property

from jdaviz.core.marks import SliceIndicatorMarks

__all__ = ['WithSliceIndicator', 'WithSliceSelection']


class WithSliceIndicator:
    @property
    def slice_component_label(self):
        return str(self.state.x_att)

    @property
    def slice_display_unit_name(self):
        return 'spectral' if self.jdaviz_app.config == 'cubeviz' else 'temporal'

    @cached_property
    def slice_indicator(self):
        # SliceIndicatorMarks does not yet exist
        slice_indicator = SliceIndicatorMarks(self)
        self.figure.marks = self.figure.marks + slice_indicator.marks
        return slice_indicator

    @property
    def slice_values(self):
        # NOTE: these are cached at the slice-plugin level
        # Retrieve display units
        slice_display_units = self.jdaviz_app._get_display_unit(
            self.slice_display_unit_name
        )

        def _get_component(layer):
            try:
                # Retrieve layer data and units
                data_comp = layer.layer.data.get_component(self.slice_component_label)
            except (AttributeError, KeyError):
                # layer either does not have get_component (because its a subset)
                # or slice_component_label is not a component in this layer
                # either way, return an empty array and skip this layer
                return np.array([])

            # Convert axis if display units are set and are different
            data_units = getattr(data_comp, 'units', None)
            if slice_display_units and data_units and slice_display_units != data_units:
                data = np.asarray(data_comp.data, dtype=float) * u.Unit(data_units)
                return data.to_value(slice_display_units,
                                     equivalencies=u.spectral())
            else:
                return data_comp.data
        try:
            return np.asarray(np.unique(np.concatenate([_get_component(layer) for layer in self.layers])),  # noqa
                              dtype=float)
        except ValueError:
            # NOTE: this will result in caching an empty list
            return np.array([])

    def _set_slice_indicator_value(self, value):
        # this is a separate method so that viewers can override and map value if necessary
        # NOTE: on first call, this will initialize the indicator itself
        self.slice_indicator.value = value


class WithSliceSelection:
    @property
    def slice_index(self):
        # index in state.slices corresponding to the slice axis
        return 2

    @property
    def slice_component_label(self):
        slice_plg = self.jdaviz_helper.plugins.get('Slice', None)
        if slice_plg is None:  # pragma: no cover
            raise ValueError("slice plugin must be activated to access slice_component_label")
        return slice_plg._obj.slice_indicator_viewers[0].slice_component_label

    @property
    def slice_display_unit_name(self):
        return 'spectral' if self.jdaviz_app.config == 'cubeviz' else 'temporal'

    @property
    def slice_values(self):
        # NOTE: these are cached at the slice-plugin level
        # TODO: add support for multiple cubes (but then slice selection needs to be more complex)
        # if slice_index is 0, then we want the equivalent of [:, 0, 0]
        # if slice_index is 1, then we want the equivalent of [0, :, 0]
        # if slice_index is 2, then we want the equivalent of [0, 0, :]
        take_inds = [2, 1, 0]
        take_inds.remove(self.slice_index)
        converted_axis = np.array([])

        # Retrieve display units
        slice_display_units = self.jdaviz_app._get_display_unit(
            self.slice_display_unit_name
        )

        for layer in self.layers:
            coords = layer.layer.data.coords
            if hasattr(coords, 'temporal_wcs'):
                data_units = coords.temporal_wcs.unit
                data = coords.temporal_wcs.pixel_to_world_values(
                    np.arange(layer.layer.data.shape[0])
                )

            else:
                world_comp_ids = layer.layer.data.world_component_ids

                if not len(world_comp_ids):
                    # rampviz uses coordinate components:
                    world_comp_ids = layer.layer.data.coordinate_components

                if self.slice_index >= len(world_comp_ids):
                    # Case where 2D image is loaded in image viewer
                    continue

                try:
                    # Retrieve layer data and units using the slice index
                    # of the world components ids
                    data_comp = layer.layer.data.get_component(
                        world_comp_ids[self.slice_index]
                    )
                except (AttributeError, KeyError):
                    continue

                data = np.asarray(
                    data_comp.data.take(0, take_inds[0]).take(0, take_inds[1]),
                    dtype=float)
                data_units = getattr(data_comp, 'units', None)

            # Convert to display units if applicable
            if slice_display_units and data_units and slice_display_units != data_units:
                converted_axis = (data * u.Unit(data_units)).to_value(
                    slice_display_units,
                    equivalencies=u.spectral() + u.pixel_scale(1*u.pix)
                )
            else:
                converted_axis = data

        return converted_axis

    @property
    def slice(self):
        return self.state.slices[self.slice_index]

    @slice.setter
    def slice(self, slice):
        # NOTE: not intended for user-access - this should be controlled through the slice plugin
        # in order to sync with all other viewers/slice indicators
        slices = [0, 0, 0]
        slices[self.slice_index] = slice
        self.state.slices = tuple(slices)

    @property
    def slice_value(self):
        return self.slice_values[self.slice]

    @slice_value.setter
    def slice_value(self, slice_value):
        # NOTE: not intended for user-access - this should be controlled through the slice plugin
        # in order to sync with all other viewers/slice indicators
        # find the slice nearest slice_value
        slice_values = self.slice_values
        if not len(slice_values):
            return
        self.slice = np.argmin(abs(slice_values - slice_value))
