<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#plot-options'">Viewer and data/layer options.</j-docs-link>
    </v-row>
  
    <v-row justify="end">
      <v-btn
        icon
        @click="() => {multiselect = !multiselect}"
      >
        <v-icon>{{multiselect ? 'mdi-checkbox-multiple-marked-outline' : 'mdi-checkbox-marked-outline'}}</v-icon>
      </v-btn>
    </v-row>

    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      :multiselect="multiselect"
      :label="multiselect ? 'Viewers' : 'Viewer'"
      :show_if_single_entry="multiselect"
      :hint="multiselect ? 'Select viewers to set options simultaneously' : 'Select the viewer to set options.'"
    />

    <div>
      <plugin-layer-select
        :items="layer_items"
        :selected.sync="layer_selected"
        :multiselect="multiselect"
        :show_if_single_entry="true"
        :label="multiselect ? 'Layers': 'Layer'"
        :hint="multiselect ? 'Select layers to set options simultaneously' : 'Select the data or subset to set options.'"
      />
    </div>

    <!-- PROFILE -->
    <j-plugin-section-header v-if="line_width_sync.in_subscribed_states">Profile Line</j-plugin-section-header>
    <glue-state-sync-wrapper v-if="config === 'cubeviz'" :sync="collapse_func_sync" :multiselect="multiselect" @unmix-state="unmix_state('function')">
      <v-select
        :items="collapse_func_sync.choices"
        v-model="collapse_func_value"
        label="Collapse Function"
        hint="Function to use when collapsing the spectrum from the cube"
        persistent-hint
      ></v-select>
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper :sync="line_color_sync" :multiselect="multiselect" @unmix-state="unmix_state('line_color')">
      <div>
        <v-subheader class="pl-0 slider-label">Line Color</v-subheader>
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
    
    <glue-state-sync-wrapper :sync="line_width_sync" :multiselect="multiselect" @unmix-state="unmix_state('line_width')">
      <glue-float-field label="Line Width" :value.sync="line_width_value" />
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper :sync="line_opacity_sync" :multiselect="multiselect" @unmix-state="unmix_state('line_opacity')">
      <div>
        <v-subheader class="pl-0 slider-label">Line Opacity</v-subheader>
        <glue-throttled-slider wait="300" max="1" step="0.01" :value.sync="line_opacity_value" hide-details class="no-hint" />
      </div>
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper v-if="config !== 'cubeviz'" :sync="uncertainty_sync" :multiselect="multiselect" @unmix-state="unmix_state('uncertainty')">
      <v-switch
        v-model="uncertainty_value"
        label="Plot uncertainties"
        />
    </glue-state-sync-wrapper>

    <!-- IMAGE -->
    <!-- IMAGE:STRETCH -->
    <j-plugin-section-header v-if="stretch_sync.in_subscribed_states">Stretch</j-plugin-section-header>
    <glue-state-sync-wrapper :sync="stretch_sync" :multiselect="multiselect" @unmix-state="unmix_state('stretch')">
      <v-select
        :items="stretch_sync.choices"
        v-model="stretch_value"
        label="Stretch"
        class="no-hint"
      ></v-select>
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper :sync="stretch_perc_sync" :multiselect="multiselect" @unmix-state="unmix_state('stretch_perc')">
      <v-select
        :items="stretch_perc_sync.choices"
        v-model="stretch_perc_value"
        label="Stretch Percentile"
        class="no-hint"
      ></v-select>
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper :sync="stretch_min_sync" :multiselect="multiselect" @unmix-state="unmix_state('stretch_min')">
      <glue-float-field label="Stretch Min" :value.sync="stretch_min_value" />
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper :sync="stretch_max_sync" :multiselect="multiselect" @unmix-state="unmix_state('stretch_max')">
      <glue-float-field label="Stretch Max" :value.sync="stretch_max_value" />
    </glue-state-sync-wrapper>

    <!-- IMAGE:BITMAP -->
    <j-plugin-section-header v-if="bitmap_visible_sync.in_subscribed_states">Image</j-plugin-section-header>
    <glue-state-sync-wrapper :sync="bitmap_visible_sync" :multiselect="multiselect" @unmix-state="unmix_state('bitmap')">
      <span>
        <v-btn icon @click.stop="bitmap_visible_value = !bitmap_visible_value">
          <v-icon>mdi-eye{{ bitmap_visible_value ? '' : '-off' }}</v-icon>
        </v-btn>
        Show image
      </span>
    </glue-state-sync-wrapper>

    <div v-if="bitmap_visible_sync.in_subscribed_states && bitmap_visible_value">
      <glue-state-sync-wrapper :sync="color_mode_sync" :multiselect="multiselect" @unmix-state="unmix_state('color_mode')">
        <v-select
          :items="color_mode_sync.choices"
          v-model="color_mode_value"
          label="Color Mode"
          hint="Whether each layer gets a single color or colormap"
          persistent-hint
          dense
        ></v-select>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper v-if="color_mode_value === 'Colormaps'" :sync="bitmap_cmap_sync" :multiselect="multiselect" @unmix-state="unmix_state('bitmap_cmap')">
        <v-select
          :items="bitmap_cmap_sync.choices"
          v-model="bitmap_cmap_value"
          label="Colormap"
          dense
        ></v-select>
      </glue-state-sync-wrapper>
      <glue-state-sync-wrapper v-else :sync="bitmap_color_sync" :multiselect="multiselect" @unmix-state="unmix_state('bitmap_color')">
        <div>
          <v-subheader class="pl-0 slider-label">Image Color</v-subheader>
          <v-menu>
            <template v-slot:activator="{ on }">
                <span class="color-menu"
                      :style="`background:${bitmap_color_value}`"
                      @click.stop="on.click"
                >&nbsp;</span>
            </template>
            <div @click.stop="" style="text-align: end; background-color: white">
                <v-color-picker :value="bitmap_color_value"
                                @update:color="throttledSetValue('bitmap_color_value', $event.hexa)"></v-color-picker>
            </div>
          </v-menu>
        </div>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper :sync="bitmap_opacity_sync" :multiselect="multiselect" @unmix-state="unmix_state('bitmap_opacity')">
        <div>
          <v-subheader class="pl-0 slider-label">opacity</v-subheader>
          <glue-throttled-slider wait="300" max="1" step="0.01" :value.sync="bitmap_opacity_value" hide-details class="no-hint" />
        </div>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper :sync="bitmap_contrast_sync" :multiselect="multiselect" @unmix-state="unmix_state('bitmap_contrast')">
        <div>
          <v-subheader class="pl-0 slider-label">contrast</v-subheader>
          <glue-throttled-slider wait="300" max="4" step="0.01" :value.sync="bitmap_contrast_value" hide-details />
        </div>
      </glue-state-sync-wrapper>

      <glue-state-sync-wrapper :sync="bitmap_bias_sync" :multiselect="multiselect" @unmix-state="unmix_state('bitmap_bias')">
        <div>
          <v-subheader class="pl-0 slider-label">bias</v-subheader>
          <glue-throttled-slider wait="300" max="1" step="0.01" :value.sync="bitmap_bias_value" hide-details />
        </div>
      </glue-state-sync-wrapper>
    </div>

    <!-- IMAGE:CONTOUR -->
    <j-plugin-section-header v-if="contour_visible_sync.in_subscribed_states">Contours</j-plugin-section-header>
    <glue-state-sync-wrapper :sync="contour_visible_sync" :multiselect="multiselect" @unmix-state="unmix_state('contour')">
      <span>
        <v-btn icon @click.stop="contour_visible_value = !contour_visible_value">
          <v-icon>mdi-eye{{ contour_visible_value ? '' : '-off' }}</v-icon>
        </v-btn>
        Show contours
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
          <glue-float-field label="contour min" :value.sync="contour_min_value" />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper :sync="contour_max_sync" :multiselect="multiselect" @unmix-state="unmix_state('contour_max')">
          <glue-float-field label="contour max" :value.sync="contour_max_value" />
        </glue-state-sync-wrapper>

        <glue-state-sync-wrapper :sync="contour_nlevels_sync" :multiselect="multiselect" @unmix-state="unmix_state('contour_nlevels')">
          <glue-float-field label="number of contour levels" :value.sync="contour_nlevels_value" />
        </glue-state-sync-wrapper>
      </div>
      <div v-else>
        <glue-state-sync-wrapper :sync="contour_custom_levels_sync" :multiselect="multiselect" @unmix-state="unmix_state('contour_levels')">
          <v-text-field 
            label="contour levels"
            :value="contour_custom_levels_txt"
            @focus="contour_custom_levels_focus"
            @blur="contour_custom_levels_blur"
            @input="contour_custom_levels_set_value"/>
        </glue-state-sync-wrapper>
      </div>
    </div>

    <!-- GENERAL:AXES -->
    <j-plugin-section-header v-if="show_axes_sync.in_subscribed_states">Axes</j-plugin-section-header>
    <glue-state-sync-wrapper :sync="show_axes_sync" :multiselect="multiselect" @unmix-state="unmix_state('show_axes')">
      <v-switch
        v-model="show_axes_value"
        label="Show axes"
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

<style>
.color-menu {
    font-size: 16px;
    padding-left: 16px;
    border: 2px solid rgba(0,0,0,0.54);
}
</style>
