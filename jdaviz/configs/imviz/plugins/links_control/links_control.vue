<template>
  <j-tray-plugin
    description='Re-link images by WCS or pixels.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#link-control'"
    :popout_button="popout_button">

    <div style="display: grid"> <!-- overlay container -->
      <div style="grid-area: 1/1">
        <v-row>
          <v-radio-group 
            label="Link type"
            hint="Type of linking to be done."
            v-model="link_type_selected"
            persistent-hint
            row>
            <v-radio
              v-for="item in link_type_items"
              :key="item.label"
              :label="item.label"
              :value="item.label"
            ></v-radio>
           </v-radio-group>
        </v-row>

        <v-row v-if="false">
          <v-switch
            label="Fallback on Pixels"
            hint="If WCS linking fails, fallback to linking by pixels."
            v-model="wcs_use_fallback"
            persistent-hint>
          </v-switch>
        </v-row>

        <v-row v-if="link_type_selected == 'WCS'">
          <v-switch
            label="Fast approximation"
            hint="Use fast approximation for image alignment if possible (accurate to <1 pixel)."
            v-model="wcs_use_affine"
            persistent-hint>
          </v-switch>
        </v-row>
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
  </j-tray-plugin>
</template>

<style>

/* addresses https://github.com/pllim/jdaviz/pull/3#issuecomment-926820530 */
div[role=radiogroup] > legend {
  width: 100%;
}

</style>
