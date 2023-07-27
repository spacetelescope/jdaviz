<template>
  <j-tray-plugin
    description='Viewer and data/layer options.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#plot-options'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :popout_button="popout_button">

    <v-row>
      <v-expansion-panels popout>
        <v-expansion-panel>
          <v-expansion-panel-header v-slot="{ open }">
            <span style="padding: 6px">Settings</span>
          </v-expansion-panel-header>
          <v-expansion-panel-content>
            <v-row>
              <v-switch
                v-model="show_viewer_labels"
                label="Show labels in viewers"
                hint="Whether to show viewer/layer labels on each viewer"
                persistent-hint
              ></v-switch>
            </v-row>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-row>

    <v-row>
      <div style="width: calc(100% - 32px)">
      </div>
      <div style="width: 32px">
        <j-tooltip tipid='plugin-plot-options-multiselect-toggle'>
          <v-btn
            icon
            style="opacity: 0.7"
            @click="() => {multiselect = !multiselect}"
          >
            <img :src="multiselect ? icon_checktoradial : icon_radialtocheck" width="24" class="invert-if-dark"/>
          </v-btn>
        </j-tooltip>
      </div>
    </v-row>

    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      :multiselect="multiselect"
      :label="multiselect ? 'Viewers' : 'Viewer'"
      :show_if_single_entry="multiselect"
      :hint="multiselect ? 'Select viewers to set options simultaneously' : 'Select the viewer to set options.'"
    />

    <plugin-layer-select
      :items="layer_items"
      :selected.sync="layer_selected"
      :multiselect="multiselect"
      :show_if_single_entry="true"
      :label="multiselect ? 'Layers': 'Layer'"
      :hint="multiselect ? 'Select layers to set options simultaneously' : 'Select the data or subset to set options.'"
    />

    <j-plugin-section-header v-if="layer_selected.length && (line_visible_sync.in_subscribed_states || subset_visible_sync.in_subscribed_states)">Layer Visibility</j-plugin-section-header>
    <glue-state-sync-wrapper :sync="marker_visible_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_visible')">
      <span>
        <v-btn icon @click.stop="marker_visible_value = !marker_visible_value">
          <v-icon>mdi-eye{{ marker_visible_value ? '' : '-off' }}</v-icon>
        </v-btn>
        Show Marker
      </span>
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper :sync="line_visible_sync" :multiselect="multiselect" @unmix-state="unmix_state('line_visible')">
      <span>
        <v-btn icon @click.stop="line_visible_value = !line_visible_value">
          <v-icon>mdi-eye{{ line_visible_value ? '' : '-off' }}</v-icon>
        </v-btn>
        Show Line
      </span>
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper :sync="subset_visible_sync" :multiselect="multiselect" @unmix-state="unmix_state('subset_visible')">
      <span>
        <v-btn icon @click.stop="subset_visible_value = !subset_visible_value">
          <v-icon>mdi-eye{{ subset_visible_value ? '' : '-off' }}</v-icon>
        </v-btn>
        Show Subset
      </span>
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper v-if="subset_visible_value" :sync="subset_color_sync" :multiselect="multiselect" @unmix-state="unmix_state('subset_color')">
      <div>
        <v-subheader class="pl-0 slider-label" style="height: 12px">Subset Color</v-subheader>
        <v-menu>
          <template v-slot:activator="{ on }">
              <span class="color-menu"
                    :style="`background:${subset_color_value}`"
                    @click.stop="on.click"
              >&nbsp;</span>
          </template>
          <div @click.stop="" style="text-align: end; background-color: white">
              <v-color-picker :value="subset_color_value"
                              @update:color="throttledSetValue('subset_color_value', $event.hexa)"></v-color-picker>
          </div>
        </v-menu>
      </div>
    </glue-state-sync-wrapper>


    <!-- PROFILE/LINE -->
    <j-plugin-section-header v-if="(line_visible_sync.in_subscribed_states && line_visible_value) || collapse_func_sync.in_subscribed_states">Line</j-plugin-section-header>
    <glue-state-sync-wrapper v-if="config === 'cubeviz'" :sync="collapse_func_sync" :multiselect="multiselect" @unmix-state="unmix_state('function')">
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="collapse_func_sync.choices"
        v-model="collapse_func_value"
        label="Collapse Function"
        hint="Function to use when collapsing the spectrum from the cube"
        persistent-hint
      ></v-select>
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper v-if="line_visible_value" :sync="line_color_sync" :multiselect="multiselect" @unmix-state="unmix_state('line_color')">
      <div>
        <v-subheader class="pl-0 slider-label" style="height: 12px">Line Color</v-subheader>
        <v-menu>
          <template v-slot:activator="{ on }">
              <span class="color-menu"
                    :style="`background:${line_color_value}`"
                    @click.stop="on.click"
              >&nbsp;</span>
          </template>
          <div @click.stop="" style="text-align: end; background-color: white">
              <v-color-picker :value="line_color_value"
                              @update:color="throttledSetValue('line_color_value', $event.hexa)"></v-color-picker>
          </div>
        </v-menu>
      </div>
    </glue-state-sync-wrapper>
    
    <glue-state-sync-wrapper v-if="line_visible_value" :sync="line_width_sync" :multiselect="multiselect" @unmix-state="unmix_state('line_width')">
      <glue-float-field label="Line Width" :value.sync="line_width_value" />
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper v-if="line_visible_value" :sync="line_opacity_sync" :multiselect="multiselect" @unmix-state="unmix_state('line_opacity')">
      <div>
        <v-subheader class="pl-0 slider-label" style="height: 12px">Line Opacity</v-subheader>
        <glue-throttled-slider wait="300" max="1" step="0.01" :value.sync="line_opacity_value" hide-details class="no-hint" />
      </div>
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper v-if="line_visible_value" :sync="line_as_steps_sync" :multiselect="multiselect" @unmix-state="unmix_state('line_as_steps')">
      <v-switch
        v-model="line_as_steps_value"
        label="Plot profile as steps"
        />
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper v-if="config !== 'cubeviz' && line_visible_value" :sync="uncertainty_visible_sync" :multiselect="multiselect" @unmix-state="unmix_state('uncertainty_visible')">
      <v-switch
        v-model="uncertainty_visible_value"
        label="Plot uncertainties"
        />
    </glue-state-sync-wrapper>

    <!-- MARKER/SCATTER -->
    <div v-if="marker_visible_sync.in_subscribed_states">
      <j-plugin-section-header>Marker</j-plugin-section-header>
      <glue-state-sync-wrapper v-if="marker_visible_value" :sync="marker_fill_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_fill')">
        <v-switch
          v-model="marker_fill_value"
          label="Fill Marker"
          />
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="marker_visible_value" :sync="marker_opacity_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_opacity')">
        <div>
          <v-subheader class="pl-0 slider-label" style="height: 12px">Opacity</v-subheader>
          <glue-throttled-slider wait="300" max="1" step="0.01" :value.sync="marker_opacity_value" hide-details class="no-hint" />
        </div>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="marker_visible_value" :sync="marker_size_mode_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_size_mode')">
        <v-select
          attach
          :menu-props="{ left: true }"
          :items="marker_size_mode_sync.choices"
          v-model="marker_size_mode_value"
          label="Size Mode"
          class="no-hint"
        ></v-select>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="marker_visible_value && marker_size_mode_value==='Fixed'" :sync="marker_size_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_size')">
        <div>
          <v-subheader class="pl-0 slider-label" style="height: 12px">Size</v-subheader>
          <glue-throttled-slider wait="300" max="10" step="0.1" :value.sync="marker_size_value" hide-details class="no-hint" />
        </div>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="marker_visible_value" :sync="marker_size_scale_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_size_scale')">
        <div>
          <v-subheader class="pl-0 slider-label" style="height: 12px">Scale</v-subheader>
          <glue-throttled-slider wait="300" max="10" step="0.1" :value.sync="marker_size_scale_value" hide-details class="no-hint" />
        </div>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="marker_visible_value && marker_size_mode_value!=='Fixed'" :sync="marker_size_col_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_size_col')">
        <v-select
          attach
          :menu-props="{ left: true }"
          :items="marker_size_col_sync.choices"
          v-model="marker_size_col_value"
          label="Column"
          class="no-hint"
        ></v-select>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="marker_visible_value && marker_size_mode_value!=='Fixed'" :sync="marker_size_vmin_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_size_vmin')">
        <v-text-field
          ref="marker_size_vmin"
          type="number"
          label="vmin"
          v-model.number="marker_size_vmin_value"
          type="number"
          step="0.01"
        ></v-text-field>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="marker_visible_value && marker_size_mode_value!=='Fixed'" :sync="marker_size_vmax_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_size_vmax')">
        <v-text-field
          ref="marker_size_vmax"
          type="number"
          label="vmax"
          v-model.number="marker_size_vmax_value"
          type="number"
          step="0.01"
        ></v-text-field>
      </glue-state-sync-wrapper>


      <glue-state-sync-wrapper v-if="marker_visible_value" :sync="marker_color_mode_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_color_mode')">
        <v-select
          attach
          :menu-props="{ left: true }"
          :items="marker_color_mode_sync.choices"
          v-model="marker_color_mode_value"
          label="Color Mode"
          class="no-hint"
        ></v-select>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="marker_visible_value && marker_color_mode_value==='Fixed'" :sync="marker_color_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_color')">
        <div>
          <v-subheader class="pl-0 slider-label" style="height: 12px">Color</v-subheader>
          <v-menu>
            <template v-slot:activator="{ on }">
                <span class="color-menu"
                      :style="`background:${marker_color_value}`"
                      @click.stop="on.click"
                >&nbsp;</span>
            </template>
            <div @click.stop="" style="text-align: end; background-color: white">
                <v-color-picker :value="marker_color_value"
                                @update:color="throttledSetValue('marker_color_value', $event.hexa)"></v-color-picker>
            </div>
          </v-menu>
        </div>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="marker_visible_value && marker_color_mode_value!=='Fixed'" :sync="marker_color_col_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_color_col')">
        <v-select
          attach
          :menu-props="{ left: true }"
          :items="marker_color_col_sync.choices"
          v-model="marker_color_col_value"
          label="Column"
          class="no-hint"
        ></v-select>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="marker_visible_value && marker_color_mode_value!=='Fixed'" :sync="marker_colormap_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_colormap')">
        <v-select
          attach
          :menu-props="{ left: true }"
          :items="marker_colormap_sync.choices"
          v-model="marker_colormap_value"
          label="Colormap"
          class="no-hint"
        ></v-select>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="marker_visible_value && marker_color_mode_value!=='Fixed'" :sync="marker_colormap_vmin_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_colormap_vmin')">
        <v-text-field
          ref="marker_colormap_vmin"
          type="number"
          label="vmin"
          v-model.number="marker_colormap_vmin_value"
          type="number"
          step="0.01"
        ></v-text-field>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="marker_visible_value && marker_color_mode_value!=='Fixed'" :sync="marker_colormap_vmax_sync" :multiselect="multiselect" @unmix-state="unmix_state('marker_colormap_vmax')">
        <v-text-field
          ref="marker_colormap_vmax"
          type="number"
          label="vmax"
          v-model.number="marker_colormap_vmax_value"
          type="number"
          step="0.01"
        ></v-text-field>
      </glue-state-sync-wrapper>
    </div>


    <!-- IMAGE -->
    <!-- IMAGE:STRETCH -->
    <j-plugin-section-header v-if="stretch_function_sync.in_subscribed_states">Stretch</j-plugin-section-header>
    <glue-state-sync-wrapper :sync="stretch_function_sync" :multiselect="multiselect" @unmix-state="unmix_state('stretch_function')">
      <v-select
        attach
        :menu-props="{ left: true }"
        :items="stretch_function_sync.choices"
        v-model="stretch_function_value"
        label="Stretch Function"
        class="no-hint"
      ></v-select>
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper :sync="stretch_preset_sync" :multiselect="multiselect" @unmix-state="unmix_state('stretch_preset')">
      <v-select
        attach
        :menu-props="{ left: true }"
        :items="stretch_preset_sync.choices"
        v-model="stretch_preset_value"
        label="Stretch Percentile Preset"
        class="no-hint"
      ></v-select>
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper :sync="stretch_vmin_sync" :multiselect="multiselect" @unmix-state="unmix_state('stretch_vmin')">
      <glue-float-field label="Stretch VMin" :value.sync="stretch_vmin_value" />
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper :sync="stretch_vmax_sync" :multiselect="multiselect" @unmix-state="unmix_state('stretch_vmax')">
      <glue-float-field label="Stretch VMax" :value.sync="stretch_vmax_value" />
    </glue-state-sync-wrapper>

    <v-row v-if="stretch_function_sync.in_subscribed_states">
      <!-- z-index to ensure on top of the jupyter widget with negative margin-top -->
      <v-text-field
          ref="stretch_hist_nbins"
          type="number"
          label="Number of Bins"
          v-model.number="stretch_hist_nbins"
          hint="The amount of bins used in the histogram."
          persistent-hint
          :rules="[() => stretch_hist_nbins !== '' || 'This field is required',
                   () => stretch_hist_nbins > 0 || 'Number of Bins must be greater than zero']"
      ></v-text-field>
      <v-switch
        v-model="stretch_hist_zoom_limits"
        class="hide-input"
        label="Limit histogram to current zoom limits"
        style="z-index: 1"
      ></v-switch>
      <!-- NOTE: height defined here should match that in the custom CSS rules
           below for the bqplot class -->
      <jupyter-widget :widget="stretch_histogram" class="stretch-hist" style="width: 100%; height: 320px; margin-top: -60px; margin-bottom: -40px" />
    </v-row>

    <!-- IMAGE:IMAGE -->
    <j-plugin-section-header v-if="image_visible_sync.in_subscribed_states">Image</j-plugin-section-header>
    <glue-state-sync-wrapper :sync="image_visible_sync" :multiselect="multiselect" @unmix-state="unmix_state('image_visible')">
      <span>
        <v-btn icon @click.stop="image_visible_value = !image_visible_value">
          <v-icon>mdi-eye{{ image_visible_value ? '' : '-off' }}</v-icon>
        </v-btn>
        Show Image
      </span>
    </glue-state-sync-wrapper>

    <div v-if="image_visible_sync.in_subscribed_states && image_visible_value">
      <glue-state-sync-wrapper :sync="image_color_mode_sync" :multiselect="multiselect" @unmix-state="unmix_state('image_color_mode')">
        <v-select
          attach
          :menu-props="{ left: true }"
          :items="image_color_mode_sync.choices"
          v-model="image_color_mode_value"
          label="Color Mode"
          hint="Whether each layer gets a single color or colormap"
          persistent-hint
          dense
        ></v-select>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="image_color_mode_value === 'Colormaps'" :sync="image_colormap_sync" :multiselect="multiselect" @unmix-state="unmix_state('image_colormap')">
        <v-select
          attach
          :menu-props="{ left: true }"
          :items="image_colormap_sync.choices"
          v-model="image_colormap_value"
          label="Colormap"
          dense
        ></v-select>
      </glue-state-sync-wrapper>
      <glue-state-sync-wrapper v-else :sync="image_color_sync" :multiselect="multiselect" @unmix-state="unmix_state('image_color')">
        <div>
          <v-subheader class="pl-0 slider-label" style="height: 12px">Image Color</v-subheader>
          <v-menu>
            <template v-slot:activator="{ on }">
                <span class="color-menu"
                      :style="`background:${image_color_value}`"
                      @click.stop="on.click"
                >&nbsp;</span>
            </template>
            <div @click.stop="" style="text-align: end; background-color: white">
                <v-color-picker :value="image_color_value"
                                @update:color="throttledSetValue('image_color_value', $event.hexa)"></v-color-picker>
            </div>
          </v-menu>
        </div>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper :sync="image_opacity_sync" :multiselect="multiselect" @unmix-state="unmix_state('image_opacity')">
        <div>
          <v-subheader class="pl-0 slider-label" style="height: 12px">Opacity</v-subheader>
          <glue-throttled-slider wait="300" max="1" step="0.01" :value.sync="image_opacity_value" hide-details class="no-hint" />
        </div>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper :sync="image_contrast_sync" :multiselect="multiselect" @unmix-state="unmix_state('image_contrast')">
        <div>
          <v-subheader class="pl-0 slider-label" style="height: 12px">Contrast</v-subheader>
          <glue-throttled-slider wait="300" max="4" step="0.01" :value.sync="image_contrast_value" hide-details />
        </div>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper :sync="image_bias_sync" :multiselect="multiselect" @unmix-state="unmix_state('image_bias')">
        <div>
          <v-subheader class="pl-0 slider-label" style="height: 12px" style="height: 12px">Bias</v-subheader>
          <glue-throttled-slider wait="300" max="1" step="0.01" :value.sync="image_bias_value" hide-details />
        </div>
      </glue-state-sync-wrapper>
    </div>

    <!-- IMAGE:CONTOUR -->
    <j-plugin-section-header v-if="contour_visible_sync.in_subscribed_states">Contours</j-plugin-section-header>
    <div style="display: grid"> <!-- overlay container -->
      <div style="grid-area: 1/1">        
        <glue-state-sync-wrapper :sync="contour_visible_sync" :multiselect="multiselect" @unmix-state="unmix_state('contour_visible')">
          <span>
            <v-btn icon @click.stop="contour_visible_value = !contour_visible_value">
              <v-icon>mdi-eye{{ contour_visible_value ? '' : '-off' }}</v-icon>
            </v-btn>
            Show Contours
          </span>
        </glue-state-sync-wrapper>

        <div v-if="contour_visible_sync.in_subscribed_states && contour_visible_value">
          <glue-state-sync-wrapper :sync="contour_mode_sync" :multiselect="multiselect" @unmix-state="unmix_state('contour_mode')">
            <v-btn-toggle dense v-model="contour_mode_value" style="margin-right: 8px; margin-top: 8px">
                <v-tooltip bottom>
                    <template v-slot:activator="{ on }">
                        <v-btn v-on="on" small value="Linear">
                            <v-icon>mdi-call-made</v-icon>
                        </v-btn>
                    </template>
                    <span>linear</span>
                </v-tooltip>

                <v-tooltip bottom>
                    <template v-slot:activator="{ on }">
                        <v-btn v-on="on" small value="Custom">
                            <v-icon>mdi-wrench</v-icon>
                        </v-btn>
                    </template>
                    <span>custom</span>
                </v-tooltip>
            </v-btn-toggle>
          </glue-state-sync-wrapper>

          <div v-if="contour_mode_value === 'Linear'">
            <glue-state-sync-wrapper :sync="contour_min_sync" :multiselect="multiselect" @unmix-state="unmix_state('contour_min')">
              <glue-float-field label="Contour Min" :value.sync="contour_min_value" />
            </glue-state-sync-wrapper>

            <glue-state-sync-wrapper :sync="contour_max_sync" :multiselect="multiselect" @unmix-state="unmix_state('contour_max')">
              <glue-float-field label="Contour Max" :value.sync="contour_max_value" />
            </glue-state-sync-wrapper>

            <glue-state-sync-wrapper :sync="contour_nlevels_sync" :multiselect="multiselect" @unmix-state="unmix_state('contour_nlevels')">
              <glue-float-field label="Number of Contour Levels" :value.sync="contour_nlevels_value" />
            </glue-state-sync-wrapper>
          </div>
          <div v-else>
            <glue-state-sync-wrapper :sync="contour_custom_levels_sync" :multiselect="multiselect" @unmix-state="unmix_state('contour_levels')">
              <v-text-field 
                label="Contour Levels"
                :value="contour_custom_levels_txt"
                @focus="contour_custom_levels_focus"
                @blur="contour_custom_levels_blur"
                @input="contour_custom_levels_set_value"/>
            </glue-state-sync-wrapper>
          </div>
        </div>
      </div>
      <div v-if="contour_spinner"
           class="text-center"
           style="grid-area: 1/1; 
                  z-index:2;
                  margin-left: -24px;
                  margin-right: -24px;
                  padding-top: 60px;
                  background-color: rgb(0 0 0 / 20%)">
        <v-progress-circular
          indeterminate
          color="spinner"
          size="50"
          width="6"
        ></v-progress-circular>
      </div>
    </div>
    <!-- GENERAL:AXES -->
    <j-plugin-section-header v-if="axes_visible_sync.in_subscribed_states && config !== 'imviz'">Axes</j-plugin-section-header>
    <glue-state-sync-wrapper v-if="config !== 'imviz'":sync="axes_visible_sync" :multiselect="multiselect" @unmix-state="unmix_state('axes_visible')">
      <v-switch
        v-model="axes_visible_value"
        label="Show Axes"
        />
    </glue-state-sync-wrapper>

  </j-tray-plugin>
</template>

<script>
module.exports = {
  created() {
    this.contour_custom_levels_user_editing = false
    this.throttledSetValue = _.throttle(
      (name, v) => { this.set_value({name: name, value: v}) },
      100);
  },
  watch: {
    contour_custom_levels_value() {
      if (!this.contour_custom_levels_user_editing) {
        this.contour_custom_levels_txt_update_from_value()
      }
    }
  },
  methods: {
    contour_custom_levels_focus(e) {
      this.contour_custom_levels_user_editing = true
    },
    contour_custom_levels_blur(e) {
      this.contour_custom_levels_user_editing = false
      this.contour_custom_levels_txt_update_from_value();
    },
    contour_custom_levels_txt_update_from_value() {
      this.contour_custom_levels_txt = this.contour_custom_levels_value.join(', ')
    },
    contour_custom_levels_set_value(e) {
      this.contour_custom_levels_txt = e
      this.contour_custom_levels_value = e.split(',').filter(n => n.trim().length).map(n => Number(n)).filter(n => !isNaN(n))
    }
  },
}
</script>

<style scoped>
.color-menu {
    font-size: 16px;
    padding-left: 16px;
    border: 2px solid rgba(0,0,0,0.54);
}
.stretch-hist > .bqplot {
  height: 320px !important;
}
</style>
