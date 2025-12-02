<template>
  <j-tray-plugin
    plugin_key="Cross Dispersion Profile"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description"
    :uses_active_status="uses_active_status"
    :keep_active.sync="keep_active"
    @plugin-ping="plugin_ping($event)"
    :popout_button="popout_button"
    :disabled_msg="disabled_msg"
    :scroll_to.sync="scroll_to">

    <v-row v-if="plot_available" style="padding: 0px">
      <jupyter-widget :widget="plot_widget"/>
    </v-row>

    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="false"
      label="Data"
      api_hint="plg.dataset ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select the data to compute the profile."
    />

    <v-row>
      <span v-if="api_hints_enabled" class="api-hint" style="font-size: 10px">
        plg.pixel =
      </span>
      <v-col cols="9" style="padding: 0px">
        <v-slider
          :min="0"
          :max="max_pix"
          v-model.number="pixel"
          density="compact"
          hint="Pixel on spectral axis."
          persistent-hint
        >
        </v-slider>
      </v-col>

      <v-col cols="3" style="padding: 7px">
        <v-text-field
          v-model.number="pixel"
          type="number"
          style="width: 60px"
          label="Pixel"
          hide-details
          dense
          single-line
        />
      </v-col>
    </v-row>

    <plugin-switch
      :value.sync="use_full_width"
      label="Use full cross-dispersion width."
      api_hint="plg.use_full_width = "
      :api_hints_enabled="api_hints_enabled"
      style="font-size: 10px;"
    />

    <div v-if="!use_full_width">
      <v-row>
        <span v-if="api_hints_enabled" class="api-hint" style="font-size: 10px">
          plg.y_pixel =
        </span>
        <v-col cols="9" style="padding: 0px">
          <v-slider
            :min="0"
            :max="max_y_pix"
            v-model.number="y_pixel"
            density="compact"
            hint="Center of profile on cross-dispersion axis."
            persistent-hint
          >
          </v-slider>
        </v-col>

        <v-col cols="3" style="padding: 7px">
          <v-text-field
            v-model.number="y_pixel"
            type="number"
            style="width: 60px"
            label="Pixel"
            hide-details
            dense
            single-line
          />
        </v-col>
    </v-row>

      <v-row>
        <span v-if="api_hints_enabled" class="api-hint" style="font-size: 10px">
          plg.width =
        </span>
        <v-col cols="9" style="padding: 0px">
          <v-slider
            :min="0"
            :max="max_y_pix"
            v-model.number="width"
            density="compact"
            hint="Width in cross-dispersion axis, in pixels."
            persistent-hint
          >
          </v-slider>
        </v-col>

        <v-col cols="3" style="padding: 7px">
          <v-text-field
            v-model.number="width"
            type="number"
            style="width: 60px"
            label="Pixel"
            hide-details
            dense
            single-line
          />
        </v-col>
      </v-row>
    </div>

  </j-tray-plugin>
</template>
