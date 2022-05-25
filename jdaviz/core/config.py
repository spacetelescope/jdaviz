"""This file contains helper function related to configuration handling."""

import copy
import os
import pathlib
import yaml

__all__ = ['read_configuration', 'get_configuration', 'list_configurations']


def read_configuration(path=None):
    """Loads a configuration from a YAML file.

    Parameters
    ----------
    path : str, optional
        Path to the configuration file to be loaded. If None, loads the
        default configuration.

    Returns
    -------
    config : dict
        A dictionary object.
    """
    if not isinstance(path, (str, type(None))):
        raise ValueError('path must be a string')

    # Parse the default configuration file
    default_path = pathlib.Path(__file__).resolve().parent.parent / "configs"

    if path is None or path == 'default':
        path = default_path / "default" / "default.yaml"
    elif path == 'cubeviz':
        path = default_path / "cubeviz" / "cubeviz.yaml"
    elif path == 'specviz':
        path = default_path / "specviz" / "specviz.yaml"
    elif path == 'mosviz':
        path = default_path / "mosviz" / "mosviz.yaml"
    elif path == 'specviz2d':
        path = default_path / "specviz2d" / "specviz2d.yaml"
    elif path == 'imviz':
        path = default_path / "imviz" / "imviz.yaml"
    elif not os.path.isfile(path):
        raise ValueError("Configuration must be path to a .yaml file.")

    with open(path, 'r') as f:
        config = yaml.safe_load(f)

    return config


def get_configuration(path=None, section=None, config=None):
    """Retrieve a copy of a specified configuration.

    Returns a copy of a configuration specification.  If ``path``
    is not specified, then returns a copy of the current application
    configuration if ``config`` is specified.

    Parameters
    ----------
    path : str, optional
        path to the configuration file to be retrieved.
    section : str, optional
        A section of the configuration to retrieve
    config : dict, optional
        An existing configuration dictionary

    Returns
    -------
    cfg : dict
        A configuration specification dictionary

    """
    # read the YAML configuration for the given path
    if path:
        config = read_configuration(path=path)
    else:
        if config is None:
            raise ValueError('Either a path or a pre-existing config must be specified')

    cfg = copy.deepcopy(config)

    # return only a section if requested
    if section:
        return cfg.get(section, None)
    return cfg


def list_configurations():
    """Get a list of pre-built configurations."""

    path = pathlib.Path(__file__).resolve().parent.parent / "configs"
    return [i.stem for i in path.rglob('*.yaml')]
