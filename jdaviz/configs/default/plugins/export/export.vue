<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Export"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#export'"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <j-multiselect-toggle
      v-if="dev_multi_support"
      :multiselect.sync="multiselect"
      :icon_checktoradial="icon_checktoradial"
      :icon_radialtocheck="icon_radialtocheck"
    ></j-multiselect-toggle>

    <div v-if="viewer_items.length > 0">
      <span class="export-category">Viewers</span>
      <v-row>
        <span class="category-content v-messages v-messages__message text--secondary">Export viewer plot as an image.</span>
      </v-row>
      <plugin-inline-select
        :items="viewer_items"
        :selected.sync="viewer_selected"
        :multiselect="multiselect"
        :single_select_allow_blank="false"
        api_hint="plg.viewer ="
        :api_hints_enabled="api_hints_enabled"
      >
      </plugin-inline-select>
      <v-row class="row-min-bottom-padding">
        <div class="category-content">
          <plugin-select
            :items="viewer_format_items.map(i => i.label)"
            :selected.sync="viewer_format_selected"
            label="Format"
            api_hint="plg.viewer_format ="
            :api_hints_enabled="api_hints_enabled"
            hint="Image format for exporting viewers."
            :disabled="viewer_selected.length == 0"
          />
          <div v-if="viewer_selected.length > 0 && ['png', 'mp4'].includes(viewer_format_selected)">
            <v-row>
              <plugin-switch
                :value.sync="image_custom_size"
                label="Custom Resolution"
                api_hint="plg.image_custom_size = "
                :api_hints_enabled="api_hints_enabled"
                hint="Set custom size/resolution for the exported image."
              />
            </v-row>
            <v-row v-if="image_custom_size">
              <v-text-field
                ref="image_width"
                type="number"
                :label="api_hints_enabled ? 'plg.image_width =' : 'Width'"
                :class="api_hints_enabled ? 'api-hint' : null"
                v-model.number="image_width"
                hint="Width in pixels"
                persistent-hint
                :rules="[() => image_width !== '' || 'This field is required',
                        () => image_width >=0 || 'Width must be positive']"
              ></v-text-field>
            </v-row>
            <v-row v-if="image_custom_size">
              <v-text-field
                ref="image_height"
                type="number"
                :label="api_hints_enabled ? 'plg.image_height =' : 'Height'"
                :class="api_hints_enabled ? 'api-hint' : null"
                v-model.number="image_height"
                hint="Height in pixels"
                persistent-hint
                :rules="[() => image_height !== '' || 'This field is required',
                        () => image_height >=0 || 'Height must be positive']"
              ></v-text-field>
            </v-row>
          </div>

        </div>
      </v-row>
      <v-row v-if="viewer_invalid_msg.length > 0">
        <span class="category-content v-messages v-messages__message text--secondary" style="color: red !important">
                  {{viewer_invalid_msg}}
        </span>
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
    </div>

    <div v-if="dataset_items.length > 0 && serverside_enabled">
      <span class="export-category">Generated Data</span>
      <v-row>
        <span class="category-content v-messages v-messages__message text--secondary">Export data generated by plugins.</span>
      </v-row>
      <plugin-inline-select
        :items="dataset_items"
        :selected.sync="dataset_selected"
        :multiselect="multiselect"
        :single_select_allow_blank="false"
        api_hint="plg.dataset ="
        :api_hints_enabled="api_hints_enabled"
      >
      </plugin-inline-select>

      <v-row v-if="data_invalid_msg.length > 0">
        <span class="category-content v-messages v-messages__message text--secondary" style="color: red !important">
                  {{data_invalid_msg}}
        </span>
      </v-row>
      <v-row class="row-min-bottom-padding">
        <div class="category-content">
          <plugin-select
            :items="dataset_format_items.map(i => i.label)"
            :selected.sync="dataset_format_selected"
            label="Format"
            api_hint="plg.dataset_format ="
            :api_hints_enabled="api_hints_enabled"
            hint="Format for exporting datasets."
            :disabled="dataset_selected.length == 0"
          />
        </div>
      </v-row>
    </div>

    <div v-if="subset_items.length > 0 && serverside_enabled">
      <span class="export-category">Subsets</span>
      <v-row>
        <span class="category-content v-messages v-messages__message text--secondary">Export spatial subset as astropy region or spectral subset as specutils SpectralRegion.</span>
      </v-row>
      <plugin-inline-select
        :items="subset_items"
        :selected.sync="subset_selected"
        :multiselect="multiselect"
        :single_select_allow_blank="false"
        api_hint="plg.subset ="
        :api_hints_enabled="api_hints_enabled"
      >
      </plugin-inline-select>

      <v-row v-if="subset_invalid_msg.length > 0">
        <span class="category-content v-messages v-messages__message text--secondary" style="color: red !important">
                  {{subset_invalid_msg}}
        </span>
      </v-row>

      <v-row class="row-min-bottom-padding">
        <div class="category-content">
          <plugin-select
            :items="subset_format_items.map(i => i.label)"
            :selected.sync="subset_format_selected"
            label="Format"
            api_hint="plg.subset_format ="
            :api_hints_enabled="api_hints_enabled"
            hint="Format for exporting subsets."
            :disabled="subset_selected == null || subset_selected.length == 0"
          />
        </div>
      </v-row>

      <v-row v-if="subset_format_invalid_msg.length > 0">
        <span class="category-content v-messages v-messages__message text--secondary" style="color: red !important">
          {{subset_format_invalid_msg}}
        </span>
      </v-row>

    </div>

    <div v-if="plugin_table_items.length > 0 && serverside_enabled">
      <span class="export-category">Plugin Tables</span>
      <v-row>
        <span class="category-content v-messages v-messages__message text--secondary">Export table from a plugin to a file.</span>
      </v-row>
      <plugin-inline-select
        :items="plugin_table_items"
        :selected.sync="plugin_table_selected"
        :multiselect="multiselect"
        :single_select_allow_blank="false"
        api_hint="plg.table ="
        :api_hints_enabled="api_hints_enabled"
      >
      </plugin-inline-select>
      <v-row class="row-min-bottom-padding">
        <div class="category-content">
          <plugin-select
            :items="plugin_table_format_items.map(i => i.label)"
            :selected.sync="plugin_table_format_selected"
            label="Format"
            api_hint="plg.table_format ="
            :api_hints_enabled="api_hints_enabled"
            hint="File format for exporting plugin tables."
            :disabled="plugin_table_selected.length == 0"
          />
        </div>
      </v-row>
    </div>

    <div v-if="plugin_plot_items.length > 0">
      <span class="export-category">Plugin Plots</span>
      <v-row>
        <span class="category-content v-messages v-messages__message text--secondary">Export plot from a plugin as an image.</span>
      </v-row>
      <plugin-inline-select
        :items="plugin_plot_items"
        :selected.sync="plugin_plot_selected"
        :multiselect="multiselect"
        :single_select_allow_blank="false"
        api_hint="plg.plugin_plot ="
        :api_hints_enabled="api_hints_enabled"
      >
      </plugin-inline-select>
      <jupyter-widget
          v-if='plugin_plot_selected_widget.length > 0'
          style="position: absolute; left: -100%"
          :widget="plugin_plot_selected_widget"/>
      <v-row class="row-min-bottom-padding">
        <div class="category-content">
          <plugin-select
            :items="plugin_plot_format_items.map(i => i.label)"
            :selected.sync="plugin_plot_format_selected"
            label="Format"
            api_hint="plg.plugin_plot_format ="
            :api_hints_enabled="api_hints_enabled"
            hint="File format for exporting plugin plots."
            :disabled="plugin_plot_selected.length == 0"
          />
        </div>
      </v-row>
    </div>

    <v-row v-if="serverside_enabled" class="row-no-outside-padding row-min-bottom-padding">
      <v-col>
        <v-text-field
          :value="default_filepath"
          label="Filepath"
          hint="Filepath export location."
          persistent-hint
          disabled
        ></v-text-field>
      </v-col>
    </v-row>

    <div style="display: grid; position: relative"> <!-- overlay container -->
    <div style="grid-area: 1/1">

    <plugin-auto-label
      :value.sync="filename_value"
      :default="filename_default"
      :auto.sync="filename_auto"
      :invalid_msg="filename_invalid_msg"
      label="Filename"
      :api_hint="'plg.filename = \''+filename_value+'\''"
      :api_hints_enabled="api_hints_enabled"
      hint="Export to a file on disk."
    ></plugin-auto-label>

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
        :api_hints_enabled="api_hints_enabled"
        :disabled="filename_value.length === 0 ||
                   movie_recording ||
                   subset_invalid_msg.length > 0 ||
                   data_invalid_msg.length > 0 ||
                   subset_format_invalid_msg.length > 0 ||
                   viewer_invalid_msg.length > 0 ||
                   (viewer_selected.length > 0 && viewer_format_selected == 'mp4' && !movie_enabled)"
      >
        {{ api_hints_enabled ?
          'plg.export()'
          :
          'Export'
        }}
      </plugin-action-button>
    </div>

      <v-overlay
        absolute
        opacity=0.5
        :value="overwrite_warn"
        :zIndex=3
        style="grid-area: 1/1;
               margin-left: -24px;
               margin-right: -24px">

      <v-card color="transparent" elevation=0 >
        <v-card-text width="100%">
          <div class="white--text">
            A file with this name is already on disk. Overwrite?
          </div>
        </v-card-text>

        <v-card-actions>
          <v-row justify="end">
            <v-btn tile small color="primary" class="mr-2" @click="overwrite_warn=false">Cancel</v-btn>
            <v-btn tile small color="accent" class="mr-4" @click="overwrite_from_ui">Overwrite</v-btn>
          </v-row>
        </v-card-actions>
      </v-card>

      </v-overlay>
    </div>

    </v-row>

  </j-tray-plugin>
</template>

<style scoped>
  .export-category {
    margin-top: 24px;
    margin-left: 20px;
    margin-right: 20px;
    display: block;
    text-align: center;
    overflow: hidden;
    white-space: nowrap;
    text-transform: uppercase;
    color: gray;
    font-weight: 500;
  }
  .category-content {
    margin-left: 32px;
    width: 100%;
    padding-right: 24px;
  }

</style>
