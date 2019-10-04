from jdaviz.core.registries import tools
from traitlets import Unicode, List, Int
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['OpenSessionButton', 'SaveSessionButton', 'ImportDataButton', 'ExportDataButton']


@tools('g-open-session')
class OpenSessionButton(TemplateMixin):
    template = Unicode("""
    <v-btn text>
        <v-icon left>folder</v-icon>
        Open Session
    </v-btn>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@tools('g-save-session')
class SaveSessionButton(TemplateMixin):
    template = Unicode("""
    <v-btn text>
        <v-icon left>save</v-icon>
        Save Session
    </v-btn>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@tools('g-import-data')
class ImportDataButton(TemplateMixin):
    template = Unicode("""
    <v-btn text>
        <v-icon left>cloud_download</v-icon>
        Import Data
    </v-btn>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@tools('g-export-data')
class ExportDataButton(TemplateMixin):
    template = Unicode("""
    <v-btn text>
        <v-icon left>save_alt</v-icon>
        Export Data
    </v-btn>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@tools('g-active-subset')
class ActiveSubsetDropdown(TemplateMixin):
    subsets = List([]).tag(sync=True)

    template = Unicode("""
    <span>
        <v-divider vertical></v-divider>
        <v-overflow-btn
            :items="subsets"
            label="Overflow Btn"
            target="#dropdown-example"
            hide-details
            class="pa-0"
            overflow
        ></v-overflow-btn>
        <v-divider vertical></v-divider>
    </span>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@tools('g-selection-state')
class SelectStateButtonGroup(TemplateMixin):
    toggle_one = Int(0).tag(sync=True)
    template = Unicode("""
    <v-btn-toggle light v-model="toggle_one" mandatory>
      <v-btn text>
        <v-icon>cloud_download</v-icon>
      </v-btn>
      <v-btn text>
        <v-icon>cloud_download</v-icon>
      </v-btn>
      <v-btn text>
        <v-icon>cloud_download</v-icon>
      </v-btn>
      <v-btn text>
        <v-icon>cloud_download</v-icon>
      </v-btn>
    </v-btn-toggle>
    """).tag(sync=True)
