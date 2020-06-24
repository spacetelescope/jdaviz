# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: config.py
# Project: core
# Author: Brian Cherinka
# Created: Tuesday, 23rd June 2020 1:22:32 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Tuesday, 23rd June 2020 1:22:32 pm
# Modified By: Brian Cherinka

#
#  This file contains helper function related to configuration handling
#

from __future__ import print_function, division, absolute_import
import copy
import os
import pathlib
import yaml


def read_configuration(path=None):
    """ Loads a configuration from a YAML file

    Loads application configuration settings from a YAML file

    Parameters
    ----------
    path : str, optional
        Path to the configuration file to be loaded. If None, loads the
        default configuration.

    Returns:
        A dictionary object
    """
    assert isinstance(path, (str, type(None))), 'path must be a string'

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
    elif not os.path.isfile(path):
        raise ValueError("Configuration must be path to a .yaml file.")

    with open(path, 'r') as f:
        config = yaml.safe_load(f)

    return config


def get_configuration(path=None, section=None, config=None):
    """ Returns a copy of the application configuration

    Returns a copy of the configuration specification.  If path
    is not specified, returns the currently loaded configuration.

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
    A configuration specification dictionary

    """
    # read the YAML configuration for the given path
    if path:
        config = read_configuration(path=path)
    else:
        assert config is not None, 'A pre-existing config must be specified'

    cfg = copy.deepcopy(config)

    # return only a section if requested
    if section:
        return cfg.get(section, None)
    return cfg


def list_configurations():
    ''' Get a list of pre-built configurations '''

    path = pathlib.Path(__file__).resolve().parent.parent / "configs"
    return [i.stem for i in path.rglob('*.yaml')]
