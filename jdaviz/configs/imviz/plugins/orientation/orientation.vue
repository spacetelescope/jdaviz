<template>
  <j-tray-plugin
    :description="docs_description || 'Rotate the viewer orientation or choose to align images by pixels.'"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#imviz-orientation'"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to"
    :disabled_msg='disabled_msg'>

    <div style="display: grid"> <!-- overlay container -->
      <div style="grid-area: 1/1; margin-top: -36px">
        <j-plugin-section-header>Align Layers</j-plugin-section-header>

        <v-alert v-if="!wcs_linking_available" type='warning' style="margin-left: -12px; margin-right: -12px">
          Please add at least one data with valid WCS to align by sky (WCS).
        </v-alert>

        <v-alert v-if="need_clear_astrowidget_markers" type='warning' style="margin-left: -12px; margin-right: -12px">
          Astrowidget markers must be cleared before changing alignment/linking options.
          <v-row justify="end" style="margin-right: 2px; margin-top: 16px">
            <v-btn @click="reset_astrowidget_markers">Clear Markers</v-btn>
          </v-row>
        </v-alert>

        <v-alert v-if="plugin_markers_exist" type='warning' style="margin-left: -12px; margin-right: -12px">
          Marker positions may not be pixel-perfect when changing alignment/linking options.
        </v-alert>

        <v-alert v-if="need_clear_subsets" type='warning' style="margin-left: -12px; margin-right: -12px">
          Existing subsets will be deleted on changing alignment/linking options.
          <v-row justify="end" style="margin-right: 2px; margin-top: 16px">
            <v-btn @click="delete_subsets">Clear Subsets</v-btn>
          </v-row>
        </v-alert>

        <v-row class="row-min-bottom-padding">
          <v-radio-group
            label="Align by"
            hint="Align individual image layers by pixels or on the sky by WCS."
            v-model="link_type_selected"
            @change="delete_subsets($event)"
            :disabled="!wcs_linking_available || need_clear_astrowidget_markers || need_clear_subsets"
            persistent-hint
            row>
            <v-radio
              v-for="item in link_type_items"
              :key="item.label"
              :label="item.label == 'WCS' ? 'WCS (Sky)' : item.label"
              :value="item.label"
            ></v-radio>
          </v-radio-group>
        </v-row>

        <v-row>
          <v-switch
            label="Fast approximation"
            hint="Use fast approximation for WCS image alignment, if possible (accurate to <1 pixel)."
            v-model="wcs_use_affine"
            v-if="link_type_selected == 'WCS'"
            persistent-hint>
          </v-switch>
        </v-row>

        <v-row v-if="false">
          <v-switch
            label="Fallback on Pixels"
            hint="If WCS linking fails, fallback to linking by pixels."
            v-model="wcs_use_fallback"
            persistent-hint>
          </v-switch>
        </v-row>

        <div v-if="link_type_selected == 'WCS'">

          <j-plugin-section-header>Orientation</j-plugin-section-header>
          <plugin-viewer-select
            :items="viewer_items"
            :selected.sync="viewer_selected"
            :multiselect="false"
            :label="'Viewer'"
            :show_if_single_entry="multiselect"
            :hint="'Select the viewer to set orientation'"
          />
          <plugin-layer-select
            :items="orientation_layer_items"
            :selected.sync="orientation_layer_selected"
            :multiselect="false"
            :icons="icons"
            :show_if_single_entry="true"
            :label="'Orientation in viewer'"
            :hint="'Select the viewer orientation'"
          />
          <v-row>
            <span style="line-height: 36px">Presets:</span>
            <!-- NOTE: changes to icons here should be manually reflected in layer_icons in app.py -->
            <j-tooltip tooltipcontent="Default orientation">
              <v-btn icon @click="select_default_orientation">
                <v-icon>mdi-image-outline</v-icon>
              </v-btn>
            </j-tooltip>
            <j-tooltip tooltipcontent="north up, east left">
              <v-btn icon @click="select_north_up_east_left">
                <img :src="icons['nuel']" width="24" class="invert-if-dark" style="opacity: 0.65"/>
              </v-btn>
            </j-tooltip>
            <j-tooltip tooltipcontent="north up, east right">
              <v-btn icon @click="select_north_up_east_right">
                <img :src="icons['nuer']" width="24" class="invert-if-dark" style="opacity: 0.65"/>
              </v-btn>
            </j-tooltip>
          </v-row>

          <v-row>
            <v-expansion-panels accordion>
              <v-expansion-panel>
                <v-expansion-panel-header v-slot="{ open }">
                  <span style="padding: 6px">Create Custom Orientation</span>
                </v-expansion-panel-header>
                <v-expansion-panel-content class="plugin-expansion-panel-content">
                  <v-row>
                    <v-text-field
                      v-model.number="rotation_angle"
                      type="number"
                      label="Rotation angle"
                      hint="Degrees counterclockwise from default orientation"
                      :rules="[() => rotation_angle !== '' || 'This field is required']"
                      persistent-hint
                    ></v-text-field>
                  </v-row>
                  <v-row>
                    <v-switch
                      label="East-left convention"
                      hint="Place East 90 degrees counterclockwise from North"
                      v-model="east_left"
                      persistent-hint>
                    </v-switch>
                  </v-row>

                  <plugin-auto-label
                    :value.sync="new_layer_label"
                    :default="new_layer_label_default"
                    :auto.sync="new_layer_label_auto"
                    label="Name for orientation option"
                    hint="Label for this new orientation option."
                  ></plugin-auto-label>
                  <v-row justify="end">
                    <j-tooltip tooltipcontent="Add orientation option and apply to viewer">
                      <v-btn color="primary" color="accent" text :disabled="rotation_angle===''" @click="add_orientation">Add orientation</v-btn>
                    </j-tooltip>
                  </v-row>
                </v-expansion-panel-content>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-row>

        </div>
        <div v-else>
          <v-alert type='info' style="margin-left: -12px; margin-right: -12px">
            Orientation and rotation options are only available when aligned by WCS (Sky).
          </v-alert>
        </div>
      </div>
      <div v-if="linking_in_progress"
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
  </j-tray-plugin>
</template>

<style>

/* addresses https://github.com/pllim/jdaviz/pull/3#issuecomment-926820530 */
div[role=radiogroup] > legend {
  width: 100%;
}
</style>
