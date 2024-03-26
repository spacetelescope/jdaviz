<template>
  <j-tray-plugin
    description='Export data or plots from the app to a file.'
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#export'"
    :popout_button="popout_button">

    <j-multiselect-toggle
      v-if="dev_multi_support"
      :multiselect.sync="multiselect"
      :icon_checktoradial="icon_checktoradial"
      :icon_radialtocheck="icon_radialtocheck"
    ></j-multiselect-toggle>

    <j-plugin-section-header style="margin-top: 12px">Viewers</j-plugin-section-header>
    <plugin-inline-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      :multiselect="multiselect"
      :single_select_allow_blank="true"
    >
    </plugin-inline-select>
    <v-row v-if="viewer_selected.length > 0" class="row-min-bottom-padding">
      <v-select
        :menu-props="{ left: true }"
        attach
        v-model="viewer_format_selected"
        :items="viewer_format_items.map(i => i.label)"
        label="Format"
        hint="Image format for exporting viewers."
        persistent-hint
      >
      </v-select>
    </v-row>
    <div v-if="viewer_selected.length > 0 && viewer_format_selected === 'mp4'" class="row-min-bottom-padding">
      <div v-if="movie_enabled">
        <v-row class="row-min-bottom-padding">
          <v-col>
            <v-text-field
              v-model.number="i_start"
              class="mt-0 pt-0"
              type="number"
              :rules="[() => i_start>=0 || 'Must be at least zero.']"
              label="Start"
              hint="Start Slice"
              persistent-hint
            ></v-text-field>
          </v-col>
          <v-col>
            <v-text-field
              v-model.number="i_end"
              class="mt-0 pt-0"
              type="number"
              :rules="[() => i_end>i_start || 'Must be larger than Start Slice.']"
              label="End"
              hint="End Slice"
               persistent-hint
            ></v-text-field>
          </v-col>
        </v-row>
        <v-row class="row-min-bottom-padding">
          <v-col>
            <v-text-field
              v-model.number="movie_fps"
              class="mt-0 pt-0"
              type="number"
              :rules="[() => movie_fps>0 || 'Must be positive.']"
              label="FPS"
              hint="Frame rate"
               persistent-hint
            ></v-text-field>
          </v-col>
        </v-row>
      </div>
      <div v-else>
        <v-alert type='warning' style="margin-left: -12px; margin-right: -12px">
          opencv-python required to export to movie
        </v-alert>
      </div>
    </div>

    <div v-if="dev_dataset_support && dataset_items.length > 0">
      <j-plugin-section-header style="margin-top: 12px">Data</j-plugin-section-header>
      <plugin-inline-select
        :items="dataset_items"
        :selected.sync="dataset_selected"
        :multiselect="multiselect"
        :single_select_allow_blank="true"
      >
      </plugin-inline-select>
    </div>

      <div v-if="subset_items.length > 0">
        <j-plugin-section-header style="margin-top: 12px">Subsets</j-plugin-section-header>
          <v-subheader style="font-size: 10px; padding-top: 3px; padding-bottom: 3px;">Export subset as astropy region.</v-subheader>
        <div class="section-description">
        <plugin-inline-select
          :items="subset_items"
          :selected.sync="subset_selected"
          :multiselect="multiselect"
          :single_select_allow_blank="true"
        >
        </plugin-inline-select>
      </div>

    <v-row v-if="subset_invalid_msg.length > 0">
      <span class="v-messages v-messages__message text--secondary" style="color: red !important">
                {{subset_invalid_msg}}
      </span>
    </v-row>

      <v-row v-if="subset_selected" class="row-min-bottom-padding">
        <v-select
          :menu-props="{ left: true }"
          attach
          v-model="subset_format_selected"
          :items="subset_format_items.map(i => i.label)"
          label="Format"
          hint="Format for exporting subsets."
          persistent-hint
        >
        </v-select>
      </v-row>

    <div v-if="table_items.length > 0">
      <j-plugin-section-header style="margin-top: 12px">Plugin Tables</j-plugin-section-header>
      <plugin-inline-select
        :items="table_items"
        :selected.sync="table_selected"
        :multiselect="multiselect"
        :single_select_allow_blank="true"
      >
      </plugin-inline-select>
      <v-row v-if="table_selected.length > 0" class="row-min-bottom-padding">
        <v-select
          :menu-props="{ left: true }"
          attach
          v-model="table_format_selected"
          :items="table_format_items.map(i => i.label)"
          label="Format"
          hint="File format for exporting plugin tables."
          persistent-hint
        >
        </v-select>
      </v-row>
    </div>

    <div v-if="dev_plot_support && plot_items.length > 0">
      <j-plugin-section-header style="margin-top: 12px">Plugin Plots</j-plugin-section-header>
      <plugin-inline-select
        :items="plot_items"
        :selected.sync="plot_selected"
        :multiselect="multiselect"
        :single_select_allow_blank="true"
      >
      </plugin-inline-select>
    </div>

    <j-plugin-section-header style="margin-top: 12px">Export To</j-plugin-section-header>

    <v-row>
        <v-text-field
        v-model="filename"
        label="Filename"
        hint="Export to a file on disk"
        :rules="[() => !!filename || 'This field is required']"
        persistent-hint>
        </v-text-field>
    </v-row>

    <v-row justify="end">
      <j-tooltip v-if="movie_recording" tooltipcontent="Interrupt recording and delete movie file">
          <plugin-action-button
             :results_isolated_to_plugin="true"
             @click="interrupt_recording"
             :disabled="!movie_recording"
          >
            <v-icon>stop</v-icon>
          </plugin-action-button>
      </j-tooltip>

      <plugin-action-button
        :results_isolated_to_plugin="true"
        @click="export_from_ui"
        :spinner="spinner"
        :disabled="filename.length === 0 || 
                   movie_recording ||
                   subset_invalid_msg.length > 0 || 
                   (viewer_selected.length > 0 && viewer_format_selected == 'mp4' && !movie_enabled)"
      >
        Export
      </plugin-action-button>
    </v-row>

  </j-tray-plugin>
</template>
