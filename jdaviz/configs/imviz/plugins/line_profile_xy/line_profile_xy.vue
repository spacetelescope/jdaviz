<template>
  <j-tray-plugin
    description='Press l to plot line profiles across X and Y under cursor. You can also manually enter X, Y and then click PLOT.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#line-profiles'"
    :popout_button="popout_button">

    <v-row>
      <v-select
        attach
        :menu-props="{ left: true }"
        :items="viewer_items"
        v-model="selected_viewer"
        label="Viewer"
        hint="Select a viewer to plot."
        persistent-hint
      ></v-select>
    </v-row>

    <v-row no-gutters>
      <v-col>
        <v-text-field
          v-model='selected_x'
          type="number"
          label="X"
          hint="Value of X"
        ></v-text-field>
      </v-col>
    </v-row>

    <v-row no-gutters>
      <v-col>
        <v-text-field
          v-model='selected_y'
          type="number"
          label="Y"
          hint="Value of Y"
        ></v-text-field>
      </v-col>
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
