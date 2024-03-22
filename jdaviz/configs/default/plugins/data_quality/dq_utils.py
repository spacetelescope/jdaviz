from importlib import resources
from pathlib import Path
from astropy.table import Table

dq_flag_map_paths = {
    'jwst': Path('data', 'data_quality', 'jwst.csv'),
    'roman': Path('data', 'data_quality', 'roman.csv'),
}


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
        flag_table = Table.read(path, format='ascii.csv')

    flag_mapping = {}
    for flag, name, desc in flag_table.iterrows():
        flag_mapping[flag] = dict(name=name, description=desc)

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
