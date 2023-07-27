<template>
  <j-tray-plugin
    description='Press l to plot line profiles across X and Y under cursor. You can also manually enter X, Y and then click PLOT.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#line-profiles'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :popout_button="popout_button">

    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      label="Viewer"
      :show_if_single_entry="false"
      hint="Select a viewer to plot."
      persistent-hint
    />

    <v-row>
      <v-text-field
        v-model='selected_x'
        type="number"
        label="X"
        hint="Value of X"
      ></v-text-field>
    </v-row>

    <v-row>
      <v-text-field
        v-model='selected_y'
        type="number"
        label="Y"
        hint="Value of Y"
      ></v-text-field>
    </v-row>

    <v-row justify="end">
      <v-btn color="primary" text @click="draw_plot">Plot</v-btn>
    </v-row>

    <v-row v-if="plot_available">
      <jupyter-widget :widget="plot_across_x_widget"/>
      <br/>
      <jupyter-widget :widget="plot_across_y_widget"/>
    </v-row>

  </j-tray-plugin>
</template>
