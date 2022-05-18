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
    <j-plugin-section-header v-if="linewidth_sync.in_subscribed_states">Profile Line</j-plugin-section-header>
    <glue-state-sync-wrapper v-if="config === 'cubeviz'" :sync="collapse_func_sync" :multiselect="multiselect" @unmix-state="unmix_state('function')">
      <v-select
        :items="collapse_func_sync.choices"
        v-model="collapse_func_value"
        label="Collapse Function"
        hint="Function to use when collapsing the spectrum from the cube"
        persistent-hint
      ></v-select>
    </glue-state-sync-wrapper>

    <v-row v-if="linewidth_sync.in_subscribed_states">
      <span>TODO: line color (needs to be able to filter on layer type)</span>
    </v-row>
    
    <glue-state-sync-wrapper :sync="linewidth_sync" :multiselect="multiselect" @unmix-state="unmix_state('linewidth')">
      <glue-float-field label="Line Width" :value.sync="linewidth_value" />
    </glue-state-sync-wrapper>

    <v-row v-if="linewidth_sync.in_subscribed_states">
      <span>TODO: uncertainty (needs to handle custom implementation)</span>
    </v-row>

    <!-- IMAGE -->
    <!-- IMAGE:STRETCH -->
    <j-plugin-section-header v-if="stretch_sync.in_subscribed_states">Stretch</j-plugin-section-header>
    <glue-state-sync-wrapper :sync="stretch_sync" :multiselect="multiselect" @unmix-state="unmix_state('stretch')">
      <v-select
        :items="stretch_sync.choices"
        v-model="stretch_value"
        label="Stretch"
        class="no-hint"
        dense
      ></v-select>
    </glue-state-sync-wrapper>

    <glue-state-sync-wrapper :sync="stretch_perc_sync" :multiselect="multiselect" @unmix-state="unmix_state('stretch_perc')">
      <v-select
        :items="stretch_perc_sync.choices"
        v-model="stretch_perc_value"
        label="Stretch Percentile"
        class="no-hint"
        dense
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

      <v-row v-if="color_mode_value === 'Colormaps'">
        <span>TODO: colormap options</span>
      </v-row>
      <v-row v-else>
        <span>TODO: color picker</span>
      </v-row>

      <v-row>
        <span>TODO: contrast, bias, opacity</span>
      </v-row>
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

    <row v-if="contour_visible_sync.in_subscribed_states && contour_visible_value">
      <span>TODO: contour options</span>
    </row>

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
