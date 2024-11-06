__all__ = ["get_plugin_description"]


def get_plugin_description(config, plugin):

    # descriptions that are shared between all configs
    common_plugin_descriptions = {'About': 'Information about Jdaviz.',
                                  'Export': 'Export data/plots and other outputs to a file.',
                                  'Markers': 'Create markers on viewers.',
                                  'Metadata': 'View metadata.',
                                  'Plot Options': 'Set viewer and layer data options.',
                                  'Data Quality': 'Data Quality layer visualization options.',
                                  }

    # descriptions that are shared between all configs with spectrum viewers
    spec_plugin_descriptions = {'Gaussian Smooth': 'Smooth data with a Gaussian kernel.',
                                'Model Fitting': 'Fit an analytic model to data or a subset of data.',  # noqa
                                'Line Lists': 'Plot spectral lines from preset or custom line lists.',  # noqa
                                'Line Analysis': 'Return statistics for spectral line.'}

    config_plugins = {
        'cubeviz': {
            'Subset Tools': 'Select and interact with spectral/spatial subsets.',
            'Slice': 'Select and interact with slice of cube in image viewers.',
            'Spectral Extraction': 'Extract a spectrum from a spectral cube.',
            'Collapse': 'Collapse a spectral cube along one axis.',
            'Moment Maps': 'Create a 2D image from a data cube.',
            'Aperture Photometry': 'Perform aperture photometry for drawn regions.',
            'Unit Conversion': 'Convert the units of displayed physical quantities.'
        } | spec_plugin_descriptions | common_plugin_descriptions,

        'imviz': {
            'Orientation': 'Rotate viewer orientation and choose alignment (pixel or sky).',
            'Subset Tools': 'Select and interact with spatial subsets.',
            'Compass': 'Show active data label, compass, and zoom box.',
            'Image Profiles (XY)': 'Plot line profiles across X and Y.',
            'Aperture Photometry': 'Perform aperture photometry for drawn regions.',
            'Catalog Search': 'Query catalog for objects within region on sky.',
            'Footprints': 'Show instrument footprints as overlays on image viewers.'
        } | common_plugin_descriptions,

        'specviz': {
            'Subset Tools': 'Select and interact with spectral subsets.',
            'Unit Conversion': 'Convert the units of displayed physical quantities.'
        } | spec_plugin_descriptions | common_plugin_descriptions,

        'specviz2d': {
            'Subset Tools': 'Select and interact with spectral/spatial subsets.',
            'Spectral Extraction': 'Extract 1D spectrum from 2D image.'
        } | spec_plugin_descriptions | common_plugin_descriptions,

        'mosviz': {
            'Subset Tools': 'Select and interact with spectral/spatial subsets.',
            'Slit Overlay': 'Add a slit to the image viewer.'
        } | spec_plugin_descriptions | common_plugin_descriptions,

        'rampviz': {
            'Slice': 'Select and interact with slice of cube in image viewers.',
            'Subset Tools': 'Select and interact with spectral/spatial subsets.',
            'Ramp Extraction': 'Extract a ramp from a ramp cube.'
        } | common_plugin_descriptions
    }

    if config in config_plugins.keys():
        return config_plugins[config].get(plugin, '')
    # if other config, check 'common_plugin_descriptions' for the correct
    # plugin, otherwise fall back to an empty string
    return common_plugin_descriptions.get(plugin, '')
