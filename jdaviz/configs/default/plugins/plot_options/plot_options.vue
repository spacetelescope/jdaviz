<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Plot Options"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#plot-options'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <!-- VIEWER OPTIONS -->
    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      :multiselect.sync="viewer_multiselect"
      :show_multiselect_toggle="viewer_multiselect || viewer_items.length > 1"
      :icon_checktoradial="icon_checktoradial"
      :icon_radialtocheck="icon_radialtocheck"
      :label="viewer_multiselect ? 'Viewers' : 'Viewer'"
      api_hint='plg.viewer = '
      api_hint_multiselect='plg.viewer.multiselect = '
      :api_hints_enabled="api_hints_enabled"
      :show_if_single_entry="viewer_multiselect"
      :hint="viewer_multiselect ? 'Select viewers to set options simultaneously' : 'Select the viewer to set options.'"
    />

    <v-row v-if="viewer_selected.length > 0">
      <v-expansion-panels accordion>
        <v-expansion-panel>
          <v-expansion-panel-header v-slot="{ open }">
            <span style="padding: 6px">Viewer bounds</span>
          </v-expansion-panel-header>
          <v-expansion-panel-content class="plugin-expansion-panel-content">
            <glue-state-sync-wrapper :sync="x_min_sync" :multiselect="viewer_multiselect" @unmix-state="unmix_state('x_min')">
              <glue-float-field
                ref="x_min"
                :label="api_hints_enabled ? 'plg.x_min =' : 'X Min'"
                :class="api_hints_enabled ? 'api-hint' : null"
                :value.sync="x_min_value"
                type="number"
                :step="x_bound_step"
                :suffix="display_units['spectral']"
              />
            </glue-state-sync-wrapper>
            <glue-state-sync-wrapper :sync="x_max_sync" :multiselect="viewer_multiselect" @unmix-state="unmix_state('x_max')">
              <glue-float-field
                ref="x_max"
                :label="api_hints_enabled ? 'plg.x_max =' : 'X Max'"
                :class="api_hints_enabled ? 'api-hint' : null"
                :value.sync="x_max_value"
                type="number"
                :step="x_bound_step"
                :suffix="display_units['spectral']"
              />
            </glue-state-sync-wrapper>
            <glue-state-sync-wrapper :sync="y_min_sync" :multiselect="viewer_multiselect" @unmix-state="unmix_state('y_min')">
              <glue-float-field
                ref="y_min"
                :label="api_hints_enabled ? 'plg.y_min =' : 'Y Min'"
                :class="api_hints_enabled ? 'api-hint' : null"
                :value.sync="y_min_value"
                type="number"
                :step="y_bound_step"
                :suffix="display_units['flux']"
              />
            </glue-state-sync-wrapper>
            <glue-state-sync-wrapper :sync="y_max_sync" :multiselect="viewer_multiselect" @unmix-state="unmix_state('y_max')">
              <glue-float-field
                ref="y_max"
                :label="api_hints_enabled ? 'plg.y_max =' : 'Y Max'"
                :class="api_hints_enabled ? 'api-hint' : null"
                :value.sync="y_max_value"
                type="number"
                :step="y_bound_step"
                :suffix="display_units['flux']"
              />
            </glue-state-sync-wrapper>
            <glue-state-sync-wrapper :sync="zoom_center_x_sync" :multiselect="viewer_multiselect" @unmix-state="unmix_state('zoom_center_x')">
              <glue-float-field
                ref="zoom_center_x"
                :label="api_hints_enabled ? 'plg.zoom_center_x =' : 'X Center'"
                :class="api_hints_enabled ? 'api-hint' : null"
                :value.sync="zoom_center_x_value"
                type="number"
                :step="zoom_step"
                :suffix="display_units['image'] || 'pix'"
              />
            </glue-state-sync-wrapper>
            <glue-state-sync-wrapper :sync="zoom_center_y_sync" :multiselect="viewer_multiselect" @unmix-state="unmix_state('zoom_center_y')">
              <glue-float-field
                ref="zoom_center_y"
                :label="api_hints_enabled ? 'plg.zoom_center_y =' : 'Y Center'"
                :class="api_hints_enabled ? 'api-hint' : null"
                :value.sync="zoom_center_y_value"
                type="number"
                :step="zoom_step"
                :suffix="display_units['image'] || 'pix'"
              />
            </glue-state-sync-wrapper>
            <glue-state-sync-wrapper :sync="zoom_radius_sync" :multiselect="viewer_multiselect" @unmix-state="unmix_state('zoom_radius')">
              <glue-float-field
                ref="zoom_radius"
                :label="api_hints_enabled ? 'plg.zoom_radius =' : 'Zoom-radius'"
                :class="api_hints_enabled ? 'api-hint' : null"
                :value.sync="zoom_radius_value"
                type="number"
                :step="zoom_step"
                :suffix="display_units['image'] || 'pix'"
              />
            </glue-state-sync-wrapper>
            <v-row justify="end">
              <plugin-action-button
                :results_isolated_to_plugin="false"
                :api_hints_enabled="api_hints_enabled"
                @click="reset_viewer_bounds"
              >
                {{api_hints_enabled ? 
                  'plg.reset_viewer_bounds()'
                  :
                  'Reset viewer bounds'
                }}
              </plugin-action-button>
            </v-row>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-row>

    <div v-if="image_color_mode_sync.in_subscribed_states">
      <glue-state-sync-wrapper :sync="image_color_mode_sync" :multiselect="viewer_multiselect" @unmix-state="unmix_state('image_color_mode')">
        <v-select
          attach
          :menu-props="{ left: true }"
          :items="image_color_mode_sync.choices"
          v-model="image_color_mode_value"
          :label="api_hints_enabled ? 'plg.image_color_mode = ' : 'Color Mode'"
          :class="api_hints_enabled ? 'api-hint' : null"
          hint="Whether each layer gets a single color or colormap."
          persistent-hint
          dense
        >
          <template v-slot:selection="{ item }">
            <span :class="api_hints_enabled ? 'api-hint' : null">
              {{ api_hints_enabled ?
                '\'' + item.text + '\''
                :
                item.text
              }}
            </span>
          </template>
          <template v-slot:item="{ item }">
            <span style="margin-top: 8px; margin-bottom: 0px">
                {{ item.text }}
              <v-row v-if="item.description" style="line-height: 1.0; margin: 0px; opacity: 0.85; font-size: 8pt">
                {{ item.description }}
              </v-row>
            </span>
          </template>
        </v-select>
      </glue-state-sync-wrapper>
    </div>

    <div v-if="image_color_mode_value === 'One color per layer' && !image_color_mode_sync['mixed']">
      <v-row justify="end">
        <j-tooltip tooltipcontent="Apply preset RGB colors, scaling, and opacities to visible layers">
          <plugin-action-button
            :spinner="apply_RGB_presets_spinner"
            :results_isolated_to_plugin="false"
            :class="api_hints_enabled ? 'api-hint' : null"
            @click="apply_RGB_presets"
          >
            {{ api_hints_enabled ?
              'plg.apply_RGB_presets()'
              :
              'Assign RGB Presets'
            }}
          </plugin-action-button>
        </j-tooltip>
      </v-row>
    </div>

    <!-- GENERAL:AXES -->
    <glue-state-sync-wrapper v-if="axes_visible_sync.in_subscribed_states && viewer_selected.length > 0 && config !== 'imviz'" :sync="axes_visible_sync" :multiselect="viewer_multiselect" @unmix-state="unmix_state('axes_visible')">
      <plugin-switch
        :value.sync="axes_visible_value"
        label="Show axes"
        api_hint="plg.axes_visible = "
        :api_hints_enabled="api_hints_enabled"
        />
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper v-if="uncertainty_visible_sync.in_subscribed_states" :sync="uncertainty_visible_sync" :multiselect="viewer_multiselect" @unmix-state="unmix_state('uncertainty_visible')">
      <plugin-switch
        :value.sync="uncertainty_visible_value"
        label="Plot uncertainties"
        api_hint='plg.uncertainty_visible = '
        :api_hints_enabled="api_hints_enabled"
        />
    </glue-state-sync-wrapper>

    <!-- LAYER OPTIONS -->
    <div v-if="api_hints_enabled">
      <v-row v-if="layer_items.length > 1">
        <span class="api-hint">
          plg.layer.multiselect = {{ boolToString(layer_multiselect) }}
        </span>
      </v-row>
      <v-row>
        <span class="api-hint">
          plg.layer = {{ layer_multiselect ? layer_selected : '\''+layer_selected+'\'' }}
        </span>
      </v-row>
    </div>

    <plugin-layer-select-tabs
      :items="layer_items"
      :selected.sync="layer_selected"
      :multiselect.sync="layer_multiselect"
      :show_multiselect_toggle="layer_multiselect || layer_items.length > 1"
      :icon_checktoradial="icon_checktoradial"
      :icon_radialtocheck="icon_radialtocheck"
      :colormode="image_color_mode_sync['mixed'] ? 'mixed' : image_color_mode_value"
      :cmap_samples="cmap_samples"
      label="Layers"
      hint="Select the data or subset to set options."
      style="margin-top: 36px"
    />
    <div v-if="layer_selected.length === 0" style="text-align: center">
      no layers selected
    </div>
    <div v-else class='layer-tab-selected' style="margin-left: -24px; padding-left: 24px; margin-top: -42px; margin-right: -24px; padding-right: 24px; border-bottom: 2px solid #00617E">
      <j-plugin-section-header v-if="layer_selected.length && (line_visible_sync.in_subscribed_states || subset_visible_sync.in_subscribed_states)">Layer Visibility</j-plugin-section-header>
      <glue-state-sync-wrapper :sync="marker_visible_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_visible')">
        <plugin-switch
          :value.sync="marker_visible_value"
          label="Show Scatter Layer"
          api_hint='plg.marker_visible = '
          :api_hints_enabled="api_hints_enabled"
          :use_eye_icon="true"
        />
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="!marker_visible_sync.in_subscribed_states" :sync="line_visible_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('line_visible')">
        <plugin-switch
          :value.sync="line_visible_value"
          label="Show Line"
          api_hint='plg.line_visible = '
          :api_hints_enabled="api_hints_enabled"
          :use_eye_icon="true"
        />
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper :sync="subset_visible_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('subset_visible')">
        <plugin-switch
          :value.sync="subset_visible_value"
          label="Show Subset"
          api_hint='plg.subset_visible = '
          :api_hints_enabled="api_hints_enabled"
          :use_eye_icon="true"
        />
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="subset_visible_value" :sync="subset_color_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('subset_color')">
        <plugin-color-picker
          label='Subset Color'
          api_hint="plg.subset_color = "
          :api_hints_enabled="api_hints_enabled"
          :value="subset_color_value"
          @color-update="throttledSetValue('subset_color_value', $event.hexa)"
        />
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="subset_visible_value" :sync="subset_opacity_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('subset_opacity')">
        <plugin-slider
            label='Subset Opacity'
            api_hint="plg.subset_opacity = "
            :api_hints_enabled="api_hints_enabled"
            wait="300"
            max="1"
            step="0.01" 
            :value.sync="subset_opacity_value"
          />
      </glue-state-sync-wrapper>


      <!-- PROFILE/LINE -->
      <j-plugin-section-header v-if="(line_visible_sync.in_subscribed_states && ((!marker_visible_sync.in_subscribed_states && line_visible_value) || (marker_visible_sync.in_subscribed_states && marker_visible_value)))">Line</j-plugin-section-header>
      <glue-state-sync-wrapper v-if="marker_visible_sync.in_subscribed_states && marker_visible_value" :sync="line_visible_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('line_visible')">
        <plugin-switch
          :value.sync="line_visible_value"
          label="Show Line"
          api_hint='plg.line_visible = '
          :api_hints_enabled="api_hints_enabled"
          :use_eye_icon="true"
        />
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="line_visible_value  && (!marker_visible_sync.in_subscribed_states || marker_visible_value)" :sync="line_color_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('line_color')">
        <plugin-color-picker
          label='Line Color'
          api_hint="plg.line_color = "
          :api_hints_enabled="api_hints_enabled"
          :value="line_color_value"
          @color-update="throttledSetValue('line_color_value', $event.hexa)"
        />
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="line_visible_value  && (!marker_visible_sync.in_subscribed_states || marker_visible_value)" :sync="line_width_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('line_width')">
        <glue-float-field
          :label="api_hints_enabled ? 'plg.line_width =' : 'Line Width'"
          :class="api_hints_enabled ? 'api-hint' : null"
          :value.sync="line_width_value"
        />
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="line_visible_value  && (!marker_visible_sync.in_subscribed_states || marker_visible_value)" :sync="line_opacity_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('line_opacity')">
        <plugin-slider
            label='Line Opacity'
            api_hint="plg.line_opacity = "
            :api_hints_enabled="api_hints_enabled"
            wait="300"
            max="1"
            step="0.01"
            :value.sync="line_opacity_value"
          />
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="line_visible_value  && (!marker_visible_sync.in_subscribed_states || marker_visible_value)" :sync="line_as_steps_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('line_as_steps')">
        <plugin-switch
          :value.sync="line_as_steps_value"
          label="Plot profile as steps"
          api_hint="plg.line_as_steps = "
          :api_hints_enabled="api_hints_enabled"
          />
      </glue-state-sync-wrapper>

      <!-- MARKER/SCATTER -->
      <div v-if="marker_visible_sync.in_subscribed_states  && (!marker_visible_sync.in_subscribed_states || marker_visible_value)">
        <j-plugin-section-header>Marker</j-plugin-section-header>
        <glue-state-sync-wrapper v-if="marker_visible_value" :sync="marker_fill_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_fill')">
          <plugin-switch
            :value.sync="marker_fill_value"
            label="Fill Marker"
            api_hint='plg.marker_fill = '
            :api_hints_enabled="api_hints_enabled"
            />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper v-if="marker_visible_value" :sync="marker_opacity_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_opacity')">
          <plugin-slider
            label='Opacity'
            api_hint="plg.marker_opacity = "
            :api_hints_enabled="api_hints_enabled"
            wait="300"
            max="1"
            step="0.01"
            :value.sync="marker_opacity_value"
          />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper v-if="marker_visible_value" :sync="marker_size_mode_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_size_mode')">
          <glue-state-select
            :items="marker_size_mode_sync.choices"
            :selected.syn="marker_size_mode_value"
            label="Size Mode"
            api_hint="plg.marker_size_mode = "
            :api_hints_enabled="api_hints_enabled"
          />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper v-if="marker_visible_value && marker_size_mode_value==='Fixed'" :sync="marker_size_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_size')">
          <plugin-slider
            label='Size'
            api_hint="plg.marker_size = "
            :api_hints_enabled="api_hints_enabled"
            wait="300"
            max="10"
            step="0.1"
            :value.sync="marker_size_value"
          />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper v-if="marker_visible_value" :sync="marker_size_scale_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_size_scale')">
          <plugin-slider
            label='Scale'
            api_hint="plg.marker_size_scale = "
            :api_hints_enabled="api_hints_enabled"
            wait="300"
            max="10"
            step="0.1"
            :value.sync="marker_size_scale_value"
          />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper v-if="marker_visible_value && marker_size_mode_value!=='Fixed'" :sync="marker_size_col_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_size_col')">
          <glue-state-select
            :items="marker_size_col_sync.choices"
            :selected.sync="marker_size_col_value"
            label="Column"
            api_hint="plg.marker_size_col = "
            :api_hints_enabled="api_hints_enabled"
          />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper v-if="marker_visible_value && marker_size_mode_value!=='Fixed'" :sync="marker_size_vmin_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_size_vmin')">
          <v-text-field
            ref="marker_size_vmin"
            :label="api_hints_enabled ? 'plg.marker_size_vmin =' : 'vmin'"
            :class="api_hints_enabled ? 'api-hint' : null"
            v-model.number="marker_size_vmin_value"
            type="number"
            step="0.01"
          ></v-text-field>
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper v-if="marker_visible_value && marker_size_mode_value!=='Fixed'" :sync="marker_size_vmax_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_size_vmax')">
          <v-text-field
            ref="marker_size_vmax"
            :label="api_hints_enabled ? 'plg.marker_size_vmax =' : 'vmax'"
            :class="api_hints_enabled ? 'api-hint' : null"
            v-model.number="marker_size_vmax_value"
            type="number"
            step="0.01"
          ></v-text-field>
        </glue-state-sync-wrapper>


        <glue-state-sync-wrapper v-if="marker_visible_value" :sync="marker_color_mode_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_color_mode')">
          <glue-state-select
            :items="marker_color_mode_sync.choices"
            :selected.sync="marker_color_mode_value"
            label="Color Mode"
            api_hint="plg.marker_color_mode = "
            :api_hints_enabled="api_hints_enabled"
          />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper v-if="marker_visible_value && marker_color_mode_value==='Fixed'" :sync="marker_color_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_color')">
          <plugin-color-picker
            label='Color'
            api_hint="plg.marker_color = "
            :api_hints_enabled="api_hints_enabled"
            :value="marker_color_value"
            @color-update="throttledSetValue('marker_color_value', $event.hexa)"
          />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper v-if="marker_visible_value && marker_color_mode_value!=='Fixed'" :sync="marker_color_col_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_color_col')">
          <glue-state-select
            :items="marker_color_col_sync.choices"
            :selected.sync="marker_color_col_value"
            label="Column"
            api_hint="plg.marker_color_col = "
            :api_hints_enabled="api_hints_enabled"
          />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper v-if="marker_visible_value && marker_color_mode_value!=='Fixed'" :sync="marker_colormap_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_colormap')">
          <glue-state-select
            :items="marker_colormap_sync.choices"
            :selected.sync="marker_colormap_value"
            label="Colormap"
            api_hint="plg.marker_colormap = "
            :api_hints_enabled="api_hints_enabled"
          />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper v-if="marker_visible_value && marker_color_mode_value!=='Fixed'" :sync="marker_colormap_vmin_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_colormap_vmin')">
          <v-text-field
            ref="marker_colormap_vmin"
            :label="api_hints_enabled ? 'plg.marker_colormap_vmin =' : 'vmin'"
            :class="api_hints_enabled ? 'api-hint' : null"
            v-model.number="marker_colormap_vmin_value"
            type="number"
            step="0.01"
          ></v-text-field>
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper v-if="marker_visible_value && marker_color_mode_value!=='Fixed'" :sync="marker_colormap_vmax_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('marker_colormap_vmax')">
          <v-text-field
            ref="marker_colormap_vmax"
            :label="api_hints_enabled ? 'plg.marker_colormap_vmax =' : 'vmax'"
            :class="api_hints_enabled ? 'api-hint' : null"
            v-model.number="marker_colormap_vmax_value"
            type="number"
            step="0.01"
          ></v-text-field>
        </glue-state-sync-wrapper>
      </div>

      <!-- IMAGE -->
      <!-- IMAGE:IMAGE -->
      <j-plugin-section-header v-if="image_visible_sync.in_subscribed_states">Image</j-plugin-section-header>
      <glue-state-sync-wrapper :sync="image_visible_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('image_visible')">
        <plugin-switch
          :value.sync="image_visible_value"
          label="Show Image"
          api_hint='plg.image_visible = '
          :api_hints_enabled="api_hints_enabled"
          :use_eye_icon="true"
        />
      </glue-state-sync-wrapper>

      <div v-if="image_visible_sync.in_subscribed_states && (image_visible_value || image_visible_sync['mixed'])">
        <glue-state-sync-wrapper v-if="image_color_mode_value === 'Colormaps' || image_color_mode_sync['mixed']" :sync="image_colormap_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('image_colormap')">
          <v-select
            attach
            :menu-props="{ left: true }"
            :items="image_colormap_sync.choices"
            v-model="image_colormap_value"
            :label="api_hints_enabled ? 'plg.image_colormap =' : 'Colormap'"
            :class="api_hints_enabled ? 'api-hint' : null"
            dense
          >
            <template v-slot:selection="{ item, index }">
              <span :class="api_hints_enabled ? 'api-hint' : null">
                {{ api_hints_enabled ?
                  '\'' + item.text + '\''
                  :
                  item.text
                }}
              </span>
            </template>
            <template v-slot:item="{ item }">
              <v-card :style="'background: '+ colorStyle(item, cmap_samples)" width="100%" class="d-flex justify-center align-center text-center">
                <span style="color: white; font-weight: bold; text-shadow: 0px 0px 3px black">{{ item.text }}</span>
              </v-card>
            </template>
          </v-select>
          <v-alert v-if="image_colormap_value == 'Random' && (
              stretch_function_value !== 'linear' || stretch_preset_value !== 100 ||
              image_bias_value !== 0.5 || image_contrast_value !== 1.0
              )" type='warning' style="margin-left: -12px; margin-right: -12px">
            For image segmentation maps, "Random" gives unique colors
            only when the stretch percentile is min/max, stretch function
            is linear, contrast is 1.0, and bias is 0.5. Click below
            to choose these settings.
            <v-row justify='end'>
            <plugin-action-button
              :results_isolated_to_plugin="true"
              @click="image_segmentation_map_presets"
            >
              Image segmentation map
            </plugin-action-button>
            </v-row>
          </v-alert>

        </glue-state-sync-wrapper>
        <glue-state-sync-wrapper v-if="image_color_mode_value !== 'Colormaps' || image_color_mode_sync['mixed']" :sync="image_color_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('image_color')">
          <plugin-color-picker
            label='Image Color'
            api_hint="plg.image_color = "
            :api_hints_enabled="api_hints_enabled"
            :value="image_color_value"
            @color-update="throttledSetValue('image_color_value', $event.hexa)"
          />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper :sync="image_opacity_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('image_opacity')">
          <plugin-slider
            label='Image Opacity'
            api_hint="plg.image_opacity = "
            :api_hints_enabled="api_hints_enabled"
            wait="300"
            max="1"
            step="0.01"
            :value.sync="image_opacity_value"
          />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper :sync="image_contrast_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('image_contrast')">
          <plugin-slider
            label='Contrast'
            api_hint="plg.image_contrast = "
            :api_hints_enabled="api_hints_enabled"
            wait="300"
            max="4"
            step="0.01"
            :value.sync="image_contrast_value"
          />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper :sync="image_bias_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('image_bias')">
          <plugin-slider
            label='Bias'
            api_hint="plg.image_bias = "
            :api_hints_enabled="api_hints_enabled"
            wait="300"
            max="1"
            step="0.01"
            :value.sync="image_bias_value"
          />
        </glue-state-sync-wrapper>
      </div>

      <!-- IMAGE:STRETCH -->
      <j-plugin-section-header v-if="stretch_function_sync.in_subscribed_states">Stretch</j-plugin-section-header>
      <glue-state-sync-wrapper :sync="stretch_function_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('stretch_function')">
        <glue-state-select
          :items="stretch_function_sync.choices"
          :selected.sync="stretch_function_value"
          label="Stretch Function"
          api_hint="plg.stretch_function = "
          :api_hints_enabled="api_hints_enabled"
        />
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper :sync="stretch_preset_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('stretch_preset')">
        <glue-state-select
          :items="stretch_preset_sync.choices"
          :selected.sync="stretch_preset_value"
          label="Stretch Percentile Preset"
          api_hint="plg.stretch_preset = "
          :api_hints_enabled="api_hints_enabled"
        />
      </glue-state-sync-wrapper>

      <!-- for multiselect, show vmin/max here, otherwise they'll be in the "more stretch options" expandable section -->
      <glue-state-sync-wrapper v-if="layer_multiselect" :sync="stretch_vmin_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('stretch_vmin')">
        <v-text-field
          ref="stretch_vmin"
          :label="api_hints_enabled ? 'plg.stretch_vmin =' : 'Stretch VMin'"
          :class="api_hints_enabled ? 'api-hint' : null"
          v-model.number="stretch_vmin_value"
          type="number"
          :step="stretch_vstep"
        ></v-text-field>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="layer_multiselect" :sync="stretch_vmax_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('stretch_vmax')">
        <v-text-field
          ref="stretch_vmax"
          :label="api_hints_enabled ? 'plg.stretch_vmax =' : 'Stretch VMax'"
          :class="api_hints_enabled ? 'api-hint' : null"
          v-model.number="stretch_vmax_value"
          type="number"
          :step="stretch_vstep"
        ></v-text-field>
      </glue-state-sync-wrapper>

      <div v-if="stretch_function_sync.in_subscribed_states && (!layer_multiselect || layer_selected.length <= 1)">
        <div style="display: grid"> <!-- overlay container -->
          <div style="grid-area: 1/1">
            <glue-state-sync-wrapper
                :sync="stretch_hist_sync"
                :multiselect="layer_multiselect"
                @unmix-state="unmix_state(['stretch_function', 'stretch_params',
                                           'stretch_vmin', 'stretch_vmax',
                                           'image_color_mode', 'image_color', 'image_colormap'])"
            >
              <jupyter-widget :widget="stretch_histogram_widget"/>
            </glue-state-sync-wrapper>
          </div>
          <div v-if="stretch_hist_spinner"
               class="text-center"
               style="grid-area: 1/1;
                      z-index:2;
                      margin-left: -24px;
                      margin-right: -24px;
                      padding-top: 240px;
                      background-color: rgb(0 0 0 / 20%)">
            <v-progress-circular
              indeterminate
              color="spinner"
              size="50"
              width="6"
            ></v-progress-circular>
          </div>

        <v-row>
          <v-expansion-panels accordion>
            <v-expansion-panel>
              <v-expansion-panel-header v-slot="{ open }">
                <span style="padding: 6px">More Stretch Options</span>
              </v-expansion-panel-header>
              <v-expansion-panel-content class="plugin-expansion-panel-content">
                <v-row>
                  <v-text-field
                      ref="stretch_hist_nbins"
                      :label="api_hints_enabled ? 'plg.stretch_hist_nbins =' : 'Number of Bins'"
                      :class="api_hints_enabled ? 'api-hint' : null"
                      v-model.number="stretch_hist_nbins"
                      type="number"
                      hint="The amount of bins used in the histogram."
                      persistent-hint
                      :rules="[() => stretch_hist_nbins !== '' || 'This field is required',
                               () => stretch_hist_nbins > 0 || 'Number of Bins must be greater than zero']"
                  ></v-text-field>
                </v-row>
                <v-row>
                  <plugin-switch
                    :value.sync="stretch_hist_zoom_limits"
                    class="hide-input"
                    label="Limit histogram to current zoom limits"
                    api_hint='plg.stretch_hist_zoom_limits ='
                    :api_hints_enabled="api_hints_enabled"
                    :disabled="viewer_multiselect && viewer_selected.length > 1"
                  />
                </v-row>
                <v-row>
                  <plugin-switch
                    :value.sync="stretch_curve_visible"
                    class="hide-input"
                    label="Show stretch function curve"
                    api_hint="plg.stretch_curve_visible ="
                    :api_hints_enabled="api_hints_enabled"
                  />
                </v-row>
                <glue-state-sync-wrapper :sync="stretch_vmin_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('stretch_vmin')">
                  <v-text-field
                    ref="stretch_vmin"
                    :label="api_hints_enabled ? 'plg.stretch_vmin =' : 'Stretch VMin'"
                    :class="api_hints_enabled ? 'api-hint' : null"
                    v-model.number="stretch_vmin_value"
                    type="number"
                    :step="stretch_vstep"
                  ></v-text-field>
                </glue-state-sync-wrapper>
                <glue-state-sync-wrapper :sync="stretch_vmax_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('stretch_vmax')">
                  <v-text-field
                    ref="stretch_vmax"
                    :label="api_hints_enabled ? 'plg.stretch_vmax =' : 'Stretch VMax'"
                    :class="api_hints_enabled ? 'api-hint' : null"
                    v-model.number="stretch_vmax_value"
                    type="number"
                    :step="stretch_vstep"
                  ></v-text-field>
                </glue-state-sync-wrapper>
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-row>

      </div>

      <!-- IMAGE:CONTOUR -->
      <j-plugin-section-header v-if="contour_visible_sync.in_subscribed_states">Contours</j-plugin-section-header>
      <div style="display: grid"> <!-- overlay container -->
        <div style="grid-area: 1/1">
          <glue-state-sync-wrapper :sync="contour_visible_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('contour_visible')">
            <plugin-switch
              :value.sync="contour_visible_value"
              label="Show Contours"
              api_hint='plg.contour_visible = '
              :api_hints_enabled="api_hints_enabled"
              :use_eye_icon="true"
            />
          </glue-state-sync-wrapper>

          <div v-if="contour_visible_sync.in_subscribed_states && contour_visible_value">
            <glue-state-sync-wrapper :sync="contour_mode_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('contour_mode')">
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
              <glue-state-sync-wrapper :sync="contour_min_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('contour_min')">
                <glue-float-field 
                  :label="api_hints_enabled ? 'plg.contour_min =' : 'Contour Min'"
                  :class="api_hints_enabled ? 'api-hint' : null"
                  :value.sync="contour_min_value"
                />
              </glue-state-sync-wrapper>

              <glue-state-sync-wrapper :sync="contour_max_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('contour_max')">
                <glue-float-field
                  :label="api_hints_enabled ? 'plg.contour_max = ' : 'Contour Max'"
                  :class="api_hints_enabled ? 'api-hint' : null"
                  :value.sync="contour_max_value"
                />
              </glue-state-sync-wrapper>

              <glue-state-sync-wrapper :sync="contour_nlevels_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('contour_nlevels')">
                <glue-float-field
                  :label="api_hints_enabled ? 'plg.contour_nlevels =' : 'Number of Contour Levels'"
                  :class="api_hints_enabled ? 'api-hint' : null"
                  :value.sync="contour_nlevels_value"
                />
              </glue-state-sync-wrapper>
            </div>
            <div v-else>
              <glue-state-sync-wrapper :sync="contour_custom_levels_sync" :multiselect="layer_multiselect" @unmix-state="unmix_state('contour_levels')">
                <v-text-field
                  :label="api_hints_enabled ? 'plg.contour_custom_levels =' : 'Contour Levels'"
                  :class="api_hints_enabled ? 'api-hint' : null"
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
    </div>

  </j-tray-plugin>
</template>

<script>
module.exports = {
  created() {
    this.contour_custom_levels_user_editing = false
    this.throttledSetValue = _.throttle(
      (name, v) => { this.set_value({name: name, value: v}) },
      600);
  },
  watch: {
    contour_custom_levels_value() {
      if (!this.contour_custom_levels_user_editing) {
        this.contour_custom_levels_txt_update_from_value()
      }
    }
  },
  methods: {
    boolToString(b) {
      if (b) {
        return 'True'
      } else {
        return 'False'
      }
    },
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
    },
    colorStyle(item, cmap_samples) {
      var cmap_strip_width = 2
      var colors = []
      var style = 'repeating-linear-gradient( 90deg, '
      colors = cmap_samples[item.value]
      for ([ci, color] of colors.entries()) {
        var start = ci*cmap_strip_width
        var end = (ci+1)*cmap_strip_width
        style += color + ' '+start+'%, ' + color + ' '+end+'%'
        if (ci !== colors.length-1) {
          style += ', '
        }
      }
      style += ')'
      return style
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

  .layer-tab-selected {
    background-color: rgba(0,0,0,0.1);
  }

  .theme--dark .layer-tab-selected {
    background-color: rgba(255,255,255,0.1);
  }

  .layer-tab-selected .strike:first-of-type {
    padding-top: 16px;
  }
</style>
