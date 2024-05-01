from importlib import resources
from pathlib import Path

import numpy as np
from matplotlib.colors import ListedColormap, rgb2hex
from glue.config import stretches
from astropy.table import Table

# paths to CSV files with DQ flag mappings:
dq_flag_map_paths = {
    'jwst': Path('data', 'data_quality', 'jwst.csv'),
    'roman': Path('data', 'data_quality', 'roman.csv'),
    'hst-stis': Path('data', 'data_quality', 'hst-stis.csv'),
    'hst-acs': Path('data', 'data_quality', 'hst-acs.csv'),
    'hst-wfc3-uvis': Path('data', 'data_quality', 'hst-wfc3-uvis.csv'),
    'hst-wfc3-ir': Path('data', 'data_quality', 'hst-wfc3-ir.csv'),
    'hst-cos': Path('data', 'data_quality', 'hst-cos.csv'),
}


class LookupStretch:
    """
    Stretch class specific to DQ arrays.

    Attributes
    ----------
    flags : array-like
        DQ flags.
    """

    def __init__(self, flags=None, hidden_flags=None):
        # Default x, y values(0-1) range chosen for a typical initial spline shape.
        # Can be modified if required.
        if flags is None:
            flags = np.linspace(0, 1, 5)
        if hidden_flags is None:
            hidden_flags = []

        self.flags = np.asarray(flags)
        self.hidden_flags = np.asarray(hidden_flags).astype(int)

    @property
    def flag_range(self):
        return np.max(self.flags) - np.min(self.flags)

    @property
    def scaled_flags(self):
        # renormalize the flags on range (0, 1):
        return (self.flags - np.min(self.flags)) / self.flag_range

    def dq_array_to_flag_index(self, values):
        # Find the index of the closest entry in `scaled_flags`
        # for each of `values` using array broadcasting:
        return np.argmin(
            np.abs(
                np.nan_to_num(values, nan=-10).flatten()[None, :] -
                self.scaled_flags[:, None]
            ), axis=0
        ).reshape(values.shape)

    def __call__(self, values, out=None, clip=False):
        # For our uses, we can ignore `out` and `clip`, but those would need
        # to be implemented before contributing this class upstream.

        # find closest index in `self.flags` for each value in `values`:
        if hasattr(values, 'squeeze'):
            values = values.squeeze()

        # `values` will have already been passed through
        # astropy.visualization.ManualInterval and normalized on (0, 1)
        # before they arrive here. First, remove that interval and get
        # back the integer values:
        values_integer = np.round(values * self.flag_range + np.min(self.flags))

        # normalize by the number of flags, onto interval (0, 1):
        renormed = self.dq_array_to_flag_index(values) / len(self.flags)

        if len(self.hidden_flags):
            # mask that is True for `values` in the hidden flags list:
            value_is_hidden = np.isin(
                np.nan_to_num(values_integer, nan=-10).astype(int),
                self.hidden_flags.astype(int)
            )
        else:
            value_is_hidden = False

        # preserve NaNs in values, and make hidden flags NaNs:
        return np.where(
            np.isnan(values) | value_is_hidden,
            np.nan,
            renormed
        )


if "lookup" not in stretches:
    stretches.add("lookup", LookupStretch, display="DQ")


def load_flag_map(mission_or_instrument=None, path=None):
    """
    Load a flag map from disk.

    Parameters
    ----------
    mission_or_instrument : {"jwst", "roman"}, optional
        Load the flag map for this mission or instrument.
    path : path-like
        Path to a flag map file (CSV).

    Returns
    -------
    flag_mapping : dict
        Flag mapping definitions. Keys are powers of two,
        values are the "name" and "description" for each flag.
    """
    if mission_or_instrument is not None and path is None:
        flag_map_path = dq_flag_map_paths.get(mission_or_instrument)

        if flag_map_path is None:
            raise NotImplementedError("No flag map found for "
                                      f"mission/instrument '{mission_or_instrument}'.")

    elif mission_or_instrument is None and path is not None:
        # load directly from a CSV file:
        flag_map_path = path

    with resources.as_file(resources.files('jdaviz').joinpath(flag_map_path)) as path:
        # by default astropy's Table.read returns "masked" for empty table data, so
        # here we supply a fill value (empty string)
        fill_values = ['']

        flag_table = Table.read(path, format='ascii.csv', fill_values=fill_values)

    flag_mapping = {}
    for flag, name, desc in flag_table[['flag', 'name', 'description']].iterrows():
        flag_mapping[int(flag)] = dict(name=name, description=desc)

    return flag_mapping


def write_flag_map(flag_mapping, csv_path, **kwargs):
    """
    Write a table containing bitmask flags and their descriptions
    to a CSV file.

    Parameters
    ----------
    flag_mapping : dict
        Flag mapping definitions. Keys are powers of two,
        values are the "name" and "description" for each flag.
    csv_path : path-like
        Where to save the CSV output.
    **kwargs : dict
        Other keywords passed to `~astropy.table.Table.write`
    """
    names = ['flag', 'name', 'description']
    dtype = (int, str, str)
    table = Table(names=names, dtype=dtype)

    for key, value in flag_mapping.items():
        row = {'flag': key}
        row.update(value)
        table.add_row(row)

    table.write(csv_path, format='ascii.csv', **kwargs)


def generate_listed_colormap(n_flags=None, rgba_colors=None, seed=3):
    """
    Generate a list of random "light" colors of length ``n_flags``.

    Parameters
    ----------
    n_flags : int
        Number of colors in the listed colormap, should match the
        number of unique DQ flags (before they're decomposed).
    rgba_colors : list of tuples
        List of RGBA tuples for each color in the colormap.
    seed : int
        Seed for the random number generator used to
        draw random colors.

    Returns
    -------
    cmap : `~matplotlib.pyplot.colors.ListedColormap`
        Colormap constructed with ``n_flags`` colors.
    rgba_colors : list of tuples
        Random light colors of length ``n_flags``.
    """
    rng = np.random.default_rng(seed)
    default_alpha = 1

    if rgba_colors is None:
        # Generate random colors that are generally "light", i.e. with
        # RGB values in the upper half of the interval (0, 1):
        rgba_colors = [
            tuple(np.insert(rng.uniform(size=2), rng.integers(0, 3), 1).tolist() + [default_alpha])
            for _ in range(n_flags)
        ]

    cmap = ListedColormap(rgba_colors)

    # setting `bad` alpha=0 will make NaNs transparent:
    cmap.set_bad(color='k', alpha=0)
    return cmap, rgba_colors


def decompose_bit(bit):
    """
    For an integer ``bit``, return a list of the powers of
    two that sum up to ``bit``.

    Parameters
    ----------
    bit : int
        Sum of powers of two.

    Returns
    -------
    powers : list of integers
        Powers of two which sum to ``bit``.
    """
    bit = int(bit)
    powers = []
    i = 1
    while i <= bit:
        if i & bit:
            powers.append(int(np.log2(i)))
        i <<= 1
    return sorted(powers)


def decode_flags(flag_map, unique_flags, rgba_colors):
    """
    For a list of unique bits in ``unique_flags``, return a list of
    dictionaries of the decomposed bits with their names, definitions, and
    colors defined in ``rgba_colors``.

    Parameters
    ----------
    flag_map : dict
        Flag mapping, such as the ones produced by ``load_flag_map``.
    unique_flags : list or array
        Sequence of unique flags which occur in a data quality array.
    rgba_colors : list of tuples
        RGBA color tuples, one per unique flag.
    """
    decoded_flags = []

    for i, (bit, color) in enumerate(zip(unique_flags, rgba_colors)):
        decoded_bits = decompose_bit(bit)
        decoded_flags.append({
            'flag': int(bit),
            'decomposed': {bit: flag_map[bit] if bit in flag_map else bit
                           for bit in decoded_bits},
            'color': rgb2hex(color),
            'show': True,
        })

    return decoded_flags
