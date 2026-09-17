import re
from collections import Counter
from functools import cached_property
from pathlib import Path

from astropy.io import fits
from traitlets import Any, Bool, List, Unicode, observe

from jdaviz.core.events import NewViewerMessage
from jdaviz.core.registries import loader_importer_registry, viewer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.template_mixin import (LoaderBannerMessagesMixin,
                                        ViewerSelectCreateNew,
                                        with_spinner)
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['MOSImporter']


_SPECTRUM_1D_PATTERN = re.compile(r'_(?:x|c)1d\.fit(?:s)?(?:\.gz)?$', re.IGNORECASE)
_SPECTRUM_2D_PATTERN = re.compile(r'_(?:s2d|cal)\.fit(?:s)?(?:\.gz)?$', re.IGNORECASE)
_IMAGE_PATTERN = re.compile(r'_i2d\.fit(?:s)?(?:\.gz)?$', re.IGNORECASE)
_CAT_PATTERN = re.compile(r'_cat\.(?:ecsv(?:\.gz)?|csv|fit(?:s)?)$', re.IGNORECASE)
_IGNORE_PATTERN = re.compile(r'(?:manifest\.html|readme(?:\.md|\.txt)?)$', re.IGNORECASE)
_FITS_PATTERN = re.compile(r'\.fit(?:s)?(?:\.gz)?$', re.IGNORECASE)

# each supported MOS product maps onto an existing importer and viewer type
# the keys are also used as the prefixes for the viewer selection
_MOS_PRODUCTS = {
    'spectrum1d': {'pattern': _SPECTRUM_1D_PATTERN,
                   'format': '1D Spectrum',
                   'viewer_label': '1D Spectrum',
                   'viewer_reference': 'spectrum-1d-viewer',
                   'viewer_traitlet_prefix': 'viewer_1d'},
    'spectrum2d': {'pattern': _SPECTRUM_2D_PATTERN,
                   'format': '2D Spectrum',
                   'viewer_label': '2D Spectrum',
                   'viewer_reference': 'spectrum-2d-viewer',
                   'viewer_traitlet_prefix': 'viewer_2d'},
    'image': {'pattern': _IMAGE_PATTERN,
              'format': 'Image',
              'viewer_label': 'Image',
              'viewer_reference': 'imviz-image-viewer',
              'viewer_traitlet_prefix': 'viewer_image'},
    'catalog': {'pattern': _CAT_PATTERN,
                'format': 'Catalog',
                'viewer_label': 'Table',
                'viewer_reference': 'table-viewer',
                'viewer_traitlet_prefix': 'viewer_catalog'},
}


def _iter_input_files(dir_path):
    """
    Yield the path and product type for every non-hidden file sorted by path.
    """

    def _product_type(filename):
        """
        Classify the file if supported by MOS.
        """
        if _IGNORE_PATTERN.search(filename):
            return 'ignore'
        for product_type, product in _MOS_PRODUCTS.items():
            if product['pattern'].search(filename):
                return product_type
        return None

    for path in sorted(dir_path.rglob('*')):
        if not path.name.startswith('.') and path.is_file():
            yield path, _product_type(path.name)


def _check_header(path):
    """
    Cheaply check whether ``path`` could be loaded as any of the supported MOS
    products (image, catalog, 1D spectrum, 2D spectrum) by inspecting only the
    FITS headers. Returns an error string if the file can be ruled out, otherwise
    an empty string. This errs on the side of considering a file valid.
    """
    if not _FITS_PATTERN.search(path.name):
        # non-FITS products (ecsv/csv catalogs) are cheap enough to load later
        return ''

    try:
        with fits.open(path, memmap=True, lazy_load_hdus=True) as hdul:
            for hdu in hdul:
                header = hdu.header
                if header.get('XTENSION', '').strip() in ('BINTABLE', 'TABLE'):
                    return ''
                if header.get('NAXIS', 0) >= 1:
                    return ''
    except Exception as e:  # nosec
        return f"MOS file is not readable as FITS: {path.name} ({e})"

    return f"MOS file does not contain any table or array data: {path.name}"


@loader_importer_registry('MOS')
class MOSImporter(BaseImporterToDataCollection, LoaderBannerMessagesMixin):
    template_file = __file__, "./mos.vue"
    parser_preference = ['fits', 'asdf', 'specutils.Spectrum']
    allow_directory_input = True

    # ``product_types`` lists the keys of ``_MOS_PRODUCTS`` that are
    # present (and so which viewer selections apply)
    # ``product_items`` adds the labels/counts shown in the UI
    product_types = List([]).tag(sync=True)
    product_items = List([]).tag(sync=True)

    # automatic extraction of 2D spectra is opt-in
    auto_extract_2d = Bool(False).tag(sync=True)

    # per-product-type viewer selection/creation
    viewer_1d_items = List([]).tag(sync=True)
    viewer_1d_selected = Any([]).tag(sync=True)
    viewer_1d_create_new_items = List([]).tag(sync=True)
    viewer_1d_create_new_selected = Unicode().tag(sync=True)
    viewer_1d_label_value = Unicode().tag(sync=True)
    viewer_1d_label_default = Unicode().tag(sync=True)
    viewer_1d_label_auto = Bool(True).tag(sync=True)
    viewer_1d_label_invalid_msg = Unicode().tag(sync=True)

    viewer_2d_items = List([]).tag(sync=True)
    viewer_2d_selected = Any([]).tag(sync=True)
    viewer_2d_create_new_items = List([]).tag(sync=True)
    viewer_2d_create_new_selected = Unicode().tag(sync=True)
    viewer_2d_label_value = Unicode().tag(sync=True)
    viewer_2d_label_default = Unicode().tag(sync=True)
    viewer_2d_label_auto = Bool(True).tag(sync=True)
    viewer_2d_label_invalid_msg = Unicode().tag(sync=True)

    viewer_image_items = List([]).tag(sync=True)
    viewer_image_selected = Any([]).tag(sync=True)
    viewer_image_create_new_items = List([]).tag(sync=True)
    viewer_image_create_new_selected = Unicode().tag(sync=True)
    viewer_image_label_value = Unicode().tag(sync=True)
    viewer_image_label_default = Unicode().tag(sync=True)
    viewer_image_label_auto = Bool(True).tag(sync=True)
    viewer_image_label_invalid_msg = Unicode().tag(sync=True)

    viewer_catalog_items = List([]).tag(sync=True)
    viewer_catalog_selected = Any([]).tag(sync=True)
    viewer_catalog_create_new_items = List([]).tag(sync=True)
    viewer_catalog_create_new_selected = Unicode().tag(sync=True)
    viewer_catalog_label_value = Unicode().tag(sync=True)
    viewer_catalog_label_default = Unicode().tag(sync=True)
    viewer_catalog_label_auto = Bool(True).tag(sync=True)
    viewer_catalog_label_invalid_msg = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # each product type gets its own viewer selection/creation component so
        # that incompatible data are never sent to the wrong viewer
        for product_type, product in _MOS_PRODUCTS.items():
            setattr(self, product['viewer_traitlet_prefix'],
                    self._init_product_viewer(product_type))

        counts = Counter(f['product_type'] for f in self.mos_files)
        self.product_types = [product_type for product_type in _MOS_PRODUCTS
                              if counts[product_type]]
        self.product_items = [{'label': _MOS_PRODUCTS[product_type]['format'],
                               'product_type': product_type,
                               'count': counts[product_type]}
                              for product_type in self.product_types]

        # every file gets its own data-label, built from a common prefix
        self.data_label_is_prefix = True
        self.data_label.default = self.default_data_label_prefix
        self.data_label_suffices = [f['suffix'] for f in self.mos_files]

    def _init_product_viewer(self, product_type):
        """
        Helper function used to create ViewerSelect components for each product type.
        """
        product = _MOS_PRODUCTS[product_type]
        viewer_traitlet_prefix = product['viewer_traitlet_prefix']
        viewer_select = ViewerSelectCreateNew(self,
                                              f'{viewer_traitlet_prefix}_items',
                                              f'{viewer_traitlet_prefix}_selected',
                                              f'{viewer_traitlet_prefix}_create_new_items',
                                              f'{viewer_traitlet_prefix}_create_new_selected',
                                              f'{viewer_traitlet_prefix}_label_value',
                                              f'{viewer_traitlet_prefix}_label_default',
                                              f'{viewer_traitlet_prefix}_label_auto',
                                              f'{viewer_traitlet_prefix}_label_invalid_msg',
                                              multiselect='viewer_multiselect',
                                              default_mode='empty')

        setattr(self, f'{viewer_traitlet_prefix}_create_new_items',
                [{'label': product['viewer_label'],
                  'reference': product['viewer_reference']}])

        viewer_cls = viewer_registry.members.get(product['viewer_reference']).get('cls')
        viewer_select.add_filter(lambda viewer: isinstance(viewer, viewer_cls))
        viewer_select.select_default()
        return viewer_select

    @staticmethod
    def _get_supported_viewers():
        # the 1D spectra viewer component is required to be present
        # for the input directory to be considered valid
        return [{'label': _MOS_PRODUCTS['spectrum1d']['viewer_label'],
                 'reference': _MOS_PRODUCTS['spectrum1d']['viewer_reference']}]

    @observe('data_label_invalid_msg', 'viewer_label_invalid_msg',
             'viewer_2d_label_invalid_msg', 'viewer_image_label_invalid_msg',
             'viewer_catalog_label_invalid_msg')
    def _set_import_disabled(self, change={}):
        super()._set_import_disabled(change)
        if self.import_disabled_msg:
            return

        for viewer_select in self._viewer_select_by_product_type.values():
            if viewer_select.create_new.selected and viewer_select.new_label.invalid_msg:
                self.import_disabled_msg = viewer_select.new_label.invalid_msg
                return

    def _check_is_valid(self):
        """
        Checks if the input is a valid MOS directory.

        The output of this method is wrapped by the IsValidWrapper
        helper class that converts the string to an inverted boolean,
        i.e. empty string => True, non-empty string => False
        since the string (when filled) carries error information.
        Furthermore, the actual 'is_valid' check is handled by the ValidatorMixin
        that wraps the check in a try/except statement so that individual
        '_check_is_valid' calls no longer need to catch potential failures.
        """
        if self._app.config not in ['deconfigged', 'generalized jdaviz']:
            # NOTE: temporary during deconfig process
            return "MOS importer is only supported in generalized jdaviz."

        if not self._app.state.dev_mos_loader:
            return "MOS importer is only supported in dev mode."

        input_path = self._input_path

        if input_path is None:
            return 'MOS importer input must be a directory.'

        # don't attempt to parse directories in the file input
        # when single-clicking on '..' to go up a directory
        if input_path.name == '..':
            return 'MOS importer input must not end with "..".'

        if not input_path.is_dir():
            return 'MOS importer input must be a directory.'

        # to be valid, the directory must contain at least one 1D spectrum
        # and no extraneous/invalid files
        has_spectrum_1d = False
        paths = []
        for path, product_type in _iter_input_files(input_path):
            if product_type is None:
                return f"Input directory contains unsupported MOS file: {path.name}"
            if product_type == 'spectrum1d':
                has_spectrum_1d = True
            if product_type != 'ignore':
                paths.append(path)

        if not has_spectrum_1d:
            return 'Input directory does not contain any MOS 1D spectra matching *_x1d.fits.'

        for path in paths:
            err = _check_header(path)
            if err:
                return err

        return ''

    @property
    def user_api(self):
        expose = ['viewer_1d', 'viewer_2d', 'viewer_image', 'viewer_catalog', 'auto_extract_2d']
        return ImporterUserApi(self, expose)

    @property
    def _input_path(self):
        """
        Expand input into a `~pathlib.Path` or None if the input can't
        be interpreted as a filesystem path.
        """
        try:
            return Path(self.input).expanduser()
        except (TypeError, ValueError, RuntimeError):
            return None

    @cached_property
    def mos_files(self):
        """
        Sorted list of dicts describing every importable MOS product in the input directory.
        ``product_types`` and ``product_items`` are per-product-type summaries of this list
        that are synced to the UI.

        Cached because the method walks the input directory and is read several
        times (in ``__init__`` and again on import).
        """
        input_path = self._input_path
        if input_path is None or not input_path.is_dir():
            return []

        def _label_suffix(filename):
            """
            Build the per-file data-label suffix by stripping any (compression) extension.
            """
            if filename.lower().endswith('.gz'):
                filename = Path(filename).stem
            return str(Path(filename).stem)

        return [{'path': path,
                 'product_type': product_type,
                 'format': _MOS_PRODUCTS[product_type]['format'],
                 'suffix': _label_suffix(path.name)}
                for path, product_type in _iter_input_files(input_path)
                if product_type in _MOS_PRODUCTS]

    @property
    def _viewer_select_by_product_type(self):
        """
        Viewer selection/creation component for each product type in the input directory.
        """
        return {product_type: getattr(self, _MOS_PRODUCTS[product_type]['viewer_traitlet_prefix'])
                for product_type in self.product_types}

    @property
    def targets(self):
        return [{'type': 'viewer',
                 'icon': 'mdi-window-maximize',
                 'label': _MOS_PRODUCTS[product_type]['viewer_label']}
                for product_type in self.product_types]

    @property
    def default_data_label_prefix(self):
        # default to the name of the directory being imported
        input_path = self._input_path
        name = input_path.name if input_path is not None else ''
        return name if name else 'MOS'

    @property
    def output(self):
        return self.input

    def _resolve_viewers(self, viewer_select):
        """
        Resolve a viewer selection component into a list of existing viewer labels,
        creating the requested new viewer (once) if applicable.

        TODO: this code (for creating a new viewer) is quite similar to code in
          add_results_from_plugin in template_mixin.py. Follow-up work should
          implement logic to avoid this duplication.
        """
        if viewer_select.create_new.selected:
            if viewer_select.new_label.invalid_msg:
                raise ValueError(viewer_select.new_label.invalid_msg)

            viewer_reference = viewer_select.create_new.selected_item.get('reference')
            viewer_label = viewer_select.new_label.value.strip()
            viewer_cls = viewer_registry.members.get(viewer_reference).get('cls')
            self._app._on_new_viewer(NewViewerMessage(viewer_cls, data=None, sender=self.app),
                                     vid=viewer_label,
                                     name=viewer_label,
                                     open_data_menu_if_empty=False)

            # subsequent files of this product type go into the viewer just created
            viewer_select.create_new.selected = ''
            viewer_select.selected = [viewer_label]

        selected = viewer_select.selected
        return list(selected) if isinstance(selected, (list, tuple)) else [selected]

    def _report_import_summary(self, failures):
        """
        Summarize the import in a single popup/banner. Individual failures have already
        been reported (with their tracebacks) as they happened.
        """
        n_files = len(self.mos_files)
        if len(failures):
            self._loader_message(f"{len(failures)} of {n_files} files could not be imported "
                                 f"({', '.join(failures)}).",
                                 color='warning', popup=True)
        else:
            self._loader_message(f"{n_files} files imported.", color='success')

    def _show_single_layer_per_viewer(self, preexisting_labels, imported_labels):
        """
        Match the behavior of the original mosviz configuration by leaving only the
        first of the newly imported entries visible in each viewer. All entries
        remain loaded in the viewer and can be toggled back on from its data menu.
        """
        # map viewer label to the entries already loaded in the viewer before import
        # to avoid hiding any data the user previously loaded
        for viewer_label, preexisting in preexisting_labels.items():
            viewer = self._app._jdaviz_helper.viewers.get(viewer_label)
            if viewer is None:
                continue
            data_menu = viewer.data_menu
            if not hasattr(data_menu, 'set_layer_visibility'):
                # e.g. table viewers don't support toggling layer visibility
                continue
            # the first (alphabetically) imported entry remains visible. Anything
            # else added by this import (including auto-extracted spectra) is hidden
            loaded = data_menu.data_labels_loaded
            imported = imported_labels.get(viewer_label, [])
            keep_visible = next((label for label in imported if label in loaded), None)
            for label in loaded:
                if label == keep_visible:
                    continue
                if label in preexisting and label not in imported:
                    # an entry that was overwritten by this import is both
                    # preexisting and imported, and must be treated as imported,
                    # otherwise re-importing a directory leaves every entry visible
                    continue
                # TODO: There's a synchronization issue between layer visibility state and the
                #   rendered view (specifically for 1D spectra). Users will need to manually toggle
                #   visibility in the data menu to refresh the viewer state.
                data_menu.set_layer_visibility(label, visible=False)

    def _import_file(self, file_info, viewers_by_product_type, data_label_prefix,
                     failures, imported_labels):
        """
        Import a single MOS product by deferring to the existing single-file
        importer for its format, tracking failures and (per-viewer) the labels of
        the entries that were successfully imported.
        """
        filename = file_info['path'].name
        product_type = file_info['product_type']
        data_label = f"{data_label_prefix}_{file_info['suffix']}"
        kwargs = {}
        if product_type == 'spectrum2d':
            # MOS products are expected to provide their own 1D spectra, so
            # extraction is skipped unless explicitly requested by the user
            kwargs['auto_extract'] = self.auto_extract_2d
            if self.auto_extract_2d:
                kwargs['ext_viewer'] = viewers_by_product_type.get('spectrum1d', [])

        try:
            self._app._jdaviz_helper.load(
                str(file_info['path']),
                loader='file',
                format=file_info['format'],
                data_label=data_label,
                viewer=viewers_by_product_type[product_type],
                ignore_invalid_kwargs=True,
                **kwargs)
        except Exception as e:  # nosec
            failures.append(filename)
            self._loader_message(f"Failed to import '{filename}': {e}",
                                 color='error', traceback=e)
        else:
            for viewer_label in viewers_by_product_type[product_type]:
                imported_labels[viewer_label].append(data_label)

    @with_spinner('import_spinner')
    def __call__(self):
        if self.data_label_invalid_msg:
            raise ValueError(self.data_label_invalid_msg)

        # create any requested new viewers up-front so that all files of a given
        # product type end up in the same viewer
        viewers_by_product_type = {
            product_type: self._resolve_viewers(viewer_select)
            for product_type, viewer_select in self._viewer_select_by_product_type.items()
        }

        self._clear_loader_messages()
        failures = []
        data_label_prefix = self.data_label_value.strip()

        def _viewer_data_labels(viewer_label):
            """
            Labels of the data entries currently loaded.
            """
            viewer = self._app._jdaviz_helper.viewers.get(viewer_label)
            if viewer is None:
                return []
            return list(viewer.data_menu.data_labels_loaded)

        # record what was already in each viewer so that only the newly imported
        # entries have their visibility managed below
        preexisting_labels = {viewer_label: _viewer_data_labels(viewer_label)
                              for viewer_labels in viewers_by_product_type.values()
                              for viewer_label in viewer_labels}
        imported_labels = {viewer_label: [] for viewer_label in preexisting_labels}

        # auto-extraction requires the 2D Spectral Extraction plugin to see the
        # newly loaded 2D spectrum, which is not the case while within
        # ``batch_load``, so those imports are deferred until after the batch
        def _defer(file_info):
            return self.auto_extract_2d and file_info['product_type'] == 'spectrum2d'

        batched = [file_info for file_info in self.mos_files if not _defer(file_info)]
        deferred = [file_info for file_info in self.mos_files if _defer(file_info)]

        # TODO: we artificially suppress snackbars here to avoid overwhelming the user
        #  with a popup for every file, but we should implement a less hacky
        #  solution as follow-up effort
        original_queue = self._app.state.snackbar_queue

        class NoPopupQueue:
            """Wrapper to suppress snackbar UI popups while preserving logger history."""
            def __init__(self, wrapped_queue):
                self.wrapped_queue = wrapped_queue

            def put(self, app_state, logger_plugin, snackbar_msg, **kwargs):
                # Suppress UI popup by overriding the popup kwarg
                kwargs['popup'] = False
                return self.wrapped_queue.put(app_state, logger_plugin, snackbar_msg, **kwargs)

        self._app.state.snackbar_queue = NoPopupQueue(original_queue)

        try:
            with self._app._jdaviz_helper.batch_load():
                for file_info in batched:
                    self._import_file(file_info, viewers_by_product_type, data_label_prefix,
                                      failures, imported_labels)

            for file_info in deferred:
                self._import_file(file_info, viewers_by_product_type, data_label_prefix,
                                  failures, imported_labels)

        finally:
            self._app.state.snackbar_queue = original_queue

        self._show_single_layer_per_viewer(preexisting_labels, imported_labels)
        self._report_import_summary(failures)
