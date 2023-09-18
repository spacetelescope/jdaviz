<template>
  <j-tray-plugin
    description="Re-link images by WCS or pixels, or change the viewer orientation."
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#link-control'"
    :popout_button="popout_button"
    :disabled_msg='disabled_msg'>

    <div style="display: grid"> <!-- overlay container -->
      <div style="grid-area: 1/1">
        <v-row>
        <v-radio-group
          label="Link type"
          hint="Type of linking to be done."
          v-model="link_type_selected"
          @change="delete_subsets($event)"
          persistent-hint
          row>
          <v-radio
            v-for="item in link_type_items"
            :key="item.label"
            :label="item.label"
            :value="item.label"
          ></v-radio>
        </v-radio-group>
        <div v-if="need_clear_subsets">
          <v-alert type='warning' style="margin-left: -12px; margin-right: -12px">
              Existing subsets will be deleted on changing link type.
          </v-alert>
        </div>
        </v-row>

        <v-row>
        <v-switch
          label="Fast approximation"
          hint="Use fast approximation for image alignment if possible (accurate to <1 pixel)."
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

          <j-plugin-section-header>Select orientation</j-plugin-section-header>
          <plugin-viewer-select
            :items="viewer_items"
            :selected.sync="viewer_selected"
            :multiselect=false
            :label="'Viewer'"
            :show_if_single_entry="multiselect"
            :hint="'Select the viewer to set orientation'"
          />
          <plugin-layer-select
            :items="layer_items"
            :selected.sync="layer_selected"
            :multiselect=false
            :show_if_single_entry="true"
            :label="'Orientation in viewer'"
            :hint="'Select the viewer orientation'"
          />
          <v-row>
            <span style="line-height: 36px">Presets:</span>
            <j-tooltip tooltipcontent="Default orientation">
              <v-btn icon @click="select_default_orientation">
                <v-icon>mdi-restore</v-icon>
              </v-btn>
            </j-tooltip>
            <j-tooltip tooltipcontent="north up, east left">
              <v-btn icon @click="set_north_up_east_left">
                <img :src="icon_nuel" width="24" class="invert-if-dark" style="opacity: 0.65"/>
              </v-btn>
            </j-tooltip>
            <j-tooltip tooltipcontent="north up, east right">
              <v-btn icon @click="set_north_up_east_right">
                <img :src="icon_nuer" width="24" class="invert-if-dark" style="opacity: 0.65"/>
              </v-btn>
            </j-tooltip>
          </v-row>
        </div>

        <div style="grid-area: 1/1">
        </div>
        <div v-if="link_type_selected == 'WCS'">

          <j-plugin-section-header>Add orientation options</j-plugin-section-header>

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
                    label="Rotate on add"
                    hint="Select this orientation when added"
                    v-model="set_on_create"
                    persistent-hint>
                  </v-switch>
                </v-row>
                <v-row>
                  <v-switch
                    label="East increases left of north"
                    hint="Use the East-left convention"
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
                  <v-btn color="primary" color="accent" text :disabled="rotation_angle===''" @click="create_new_orientation_from_data">Add orientation</v-btn>
                </v-row>
        </div>

      </div>
      <div v-if="need_clear_markers"
            class="text-center"
            style="grid-area: 1/1; 
                   z-index:2;
                   margin-left: -24px;
                   margin-right: -24px;
                   padding-top: 60px;
                   background-color: rgb(0 0 0 / 80%)">
         <v-card color="transparent" elevation=0 >
           <v-card-text width="100%">
             <div class="white--text">
               Markers must be cleared before re-linking
             </div>
           </v-card-text>

           <v-card-actions>
             <v-row justify="end">
               <v-btn tile small color="accent" class="mr-4" @click="reset_markers" >Clear Markers</v-btn>
             </v-row>
           </v-card-actions>
         </v-card>
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
