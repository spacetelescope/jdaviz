from jdaviz.core.registries import tools, trays, viewers
import ipyvuetify as v
from traitlets import Unicode
from ipywidgets import Widget
from glue_jupyter.bqplot.profile import BqplotProfileView
from glue_jupyter.utils import validate_data_argument
from glue_jupyter.matplotlib.profile import ProfileJupyterViewer


def test_toolbar_registry_template():
    # Define a new registry class object
    @tools('j-test-tool-template')
    class TestTool(v.VuetifyTemplate):
        template = Unicode("""
        <v-btn>
            Press Me
        <v-btn>
        """).tag(sync=True)

    test_tool = tools.members.get('j-test-tool-template')()

    assert isinstance(test_tool, Widget)
    assert 'j-test-tool-template' in tools.members


def test_toolbar_registry_widget():
    @tools('j-test-tool-widget')
    class TestTool(v.Btn):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.children = ["Press Me"]

    test_tool = tools.members.get('j-test-tool-widget')()

    assert isinstance(test_tool, Widget)
    assert 'j-test-tool-widget' in tools.members
    assert test_tool.children[0] == 'Press Me'


def test_tray_registry_template():
    @trays('j-test-tray-template', label="Tray Template", icon='save')
    class TestTray(v.VuetifyTemplate):
        template = Unicode("""
          <v-card
            max-width="344"
            class="mx-auto"
          >
            <v-card-title>I'm a title</v-card-title>
            <v-card-text>I'm card text</v-card-text>
            <v-card-actions>
              <v-btn text>Click</v-btn>
            </v-card-actions>
          </v-card>
        """).tag(sync=True)

    test_tray = trays.members.get('j-test-tray-template').get('cls')()

    assert isinstance(test_tray, Widget)
    assert 'j-test-tray-template' in trays.members


def test_tray_registry_widget():
    @trays('j-test-tray-widget', label="Tray Template", icon='save')
    class TestTray(v.Card):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.max_width = 344

            self.children = [
                v.CardTitle(children=["I'm a title"]),
                v.CardText(children=["I'm card text."]),
                v.CardActions(children=[
                    v.Btn(text=True,
                          children=[
                              "Click"
                          ])
                ])
            ]

    test_tray = trays.members.get('j-test-tray-widget').get('cls')()

    assert isinstance(test_tray, Widget)
    assert 'j-test-tray-widget' in trays.members
    assert test_tray.max_width == 344
