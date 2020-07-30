from jdaviz.core.helpers import ConfigHelper
from astropy.table import QTable
import astropy.units as u


class MosViz(ConfigHelper):
    """MosViz Helper class"""
    _default_configuration = 'mosviz'

    def load_1d_spectra(self, data_obj, data_labels=None):
        """
        Load and parse a set of 1D spectra objects.

        Parameters
        ----------
        data_obj : list or str
            A list of spectra as translatable container objects (e.g.
            ``Spectrum1D``) that can be read by glue-jupyter. Alternatively,
            can be a string file path.
        data_labels : str or list
            String representing the label for the data item loaded via
            ``data_obj``. Can be a list of strings representing data labels
            for each item in ``data_obj`` if  ``data_obj`` is a list.
        """
        self.app.load_data(data_obj, parser_reference="mosviz-spec1d-parser",
                           data_labels=data_labels)

    def load_2d_spectra(self, data_obj, data_labels=None):
        """
        Load and parse a set of 2D spectra objects.

        Parameters
        ----------
        data_obj : list or str
            A list of 2D spectra as translatable container objects (e.g.
            ``Spectrum1D``) that can be read by glue-jupyter. Alternatively,
            can be a string file path.
        data_labels : str or list
            String representing the label for the data item loaded via
            ``data_obj``. Can be a list of strings representing data labels
            for each item in ``data_obj`` if  ``data_obj`` is a list.
        """
        self.app.load_data(data_obj, parser_reference="mosviz-spec2d-parser",
                           data_labels=data_labels)

    def load_images(self, data_obj, data_labels=None):
        """
        Load and parse a set of image objects. If providing a file path, it
        must be readable by ``CCDData`` io registries.

        Parameters
        ----------
        data_obj : list or str
            A list of spectra as translatable container objects (e.g.
            ``CCDData``) that can be read by glue-jupyter. Alternatively,
            can be a string file path.
        data_labels : str or list
            String representing the label for the data item loaded via
            ``data_obj``. Can be a list of strings representing data labels
            for each item in ``data_obj`` if  ``data_obj`` is a list.
        """
        self.app.load_data(data_obj, parser_reference="mosviz-image-parser",
                           data_labels=data_labels)

    def add_column(self, data, column_name=None):
        """
        Add a new data column to the table.

        Parameters
        ----------
        data : array-like
            Array-like set of data values, e.g. redshifts, RA, DEC, etc.
        column_name : str
            Header string to be shown in the table.
        """
        table_data = self.app.data_collection['MOS Table']
        table_data.add_component(data, column_name)

    def to_table(self):
        """
        Creates an astropy `~astropy.table.QTable` object from the MOS table
        viewer.

        Returns
        -------
        `~astropy.table.QTable`
            An astropy table constructed from the loaded mos data.
        """
        table_data = self.app.data_collection['MOS Table']

        data_dict = {}

        for cid in table_data.components:
            comp = table_data.get_component(cid)
            unit = u.Unit(comp.units)

            data_dict[cid.label] = comp.data * unit

        return QTable(data_dict)
