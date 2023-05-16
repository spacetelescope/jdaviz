from ipyvuetify import VuetifyTemplate

__all__ = ['StyleWidget']


class StyleWidget(VuetifyTemplate):
    def __init__(self, template_file, *args, **kwargs):
        self.template_file = template_file
        super().__init__(*args, **kwargs)
