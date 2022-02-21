<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link>Viewer and data/layer options.</j-docs-link>
    </v-row>

    <v-row v-if="viewer_items.length > 1">
      <v-select
        :items="viewer_items"
        v-model="selected_viewers"
        label="Viewer"
        hint="Select the viewer(s) to set options."
        persistent-hint
        multiple
        chips
      >
        <template v-slot:selection="{ item, index }">
           <v-chip>
             <span>
              <v-icon style='margin-left: -10px; margin-right: 2px'>mdi-numeric-{{viewer_items.indexOf(item)+1}}-circle-outline</v-icon>
              {{ item.split("-viewer")[0] }}
            </span>
           </v-chip>
         </template>
         <template v-slot:prepend-item>
           <v-list-item
             ripple
             @mousedown.prevent
             @click="() => {if (selected_viewers.length < viewer_items.length) { selected_viewers = viewer_items} else {selected_viewers = []}}"
           >
             <v-list-item-action>
               <v-icon>
                 {{ selected_viewers.length == viewer_items.length ? 'mdi-close-box' : selected_viewers.length ? 'mdi-minus-box' : 'mdi-checkbox-blank-outline' }}
               </v-icon>
             </v-list-item-action>
             <v-list-item-content>
               <v-list-item-title>
                 {{ selected_viewers.length < viewer_items.length ? "Select All" : "Clear All" }}
               </v-list-item-title>
             </v-list-item-content>
           </v-list-item>
           <v-divider class="mt-2"></v-divider>
         </template>
    </v-select>
    </v-row>

    <div v-if="selected_viewers.length">
      <v-row>
        <v-select
          :items="layer_items"
          v-model="selected_layers"
          label="Layer"
          hint="Select the data or subset(s) to set options."
          persistent-hint
          multiple
          chips
        >
          <template v-slot:selection="{ item, index }">
             <v-chip>
               <span>
                <v-icon style='margin-left: -10px; margin-right: 2px'>mdi-alpha-{{String.fromCharCode(97 + layer_items.indexOf(item))}}-box-outline</v-icon>
                {{ item }}
              </span>
             </v-chip>
           </template>
           <template v-slot:prepend-item>
             <v-list-item
               ripple
               @mousedown.prevent
               @click="() => {if (selected_layers.length < layer_items.length) { selected_layers = layer_items} else {selected_layers = []}}"
             >
               <v-list-item-action>
                 <v-icon>
                   {{ selected_layers.length == layer_items.length ? 'mdi-close-box' : selected_layers.length ? 'mdi-minus-box' : 'mdi-checkbox-blank-outline' }}
                 </v-icon>
               </v-list-item-action>
               <v-list-item-content>
                 <v-list-item-title>
                   {{ selected_layers.length < layer_items.length ? "Select All" : "Clear All" }}
                 </v-list-item-title>
               </v-list-item-content>
             </v-list-item>
             <v-divider class="mt-2"></v-divider>
           </template>
        </v-select>
      </v-row>

      <v-row 
        v-if="viewer_state_items.indexOf('show_axes') !== -1" 
        class="row-no-outside-padding">
        <v-col cols="8">
            <v-switch
              v-model="show_axes"
              label="Show axes"
              />
        </v-col>
        <v-col cols="4" style="text-align: center">
          <v-icon v-for="index in show_axes_vs">mdi-numeric-{{index+1}}-circle-outline</v-icon>
        </v-col>
      </v-row>

      <v-row 
        v-if="viewer_state_items.indexOf('function') !== -1" 
        class="row-no-outside-padding">
        <v-col cols="8">
          <v-select
            :items="function_items"
            v-model="function_selected"
            label="Collapse Function"/>
        </v-col>
        <v-col cols="4" style="text-align: center">
          <v-icon v-for="index in function_vs">mdi-numeric-{{index+1}}-circle-outline</v-icon>
        </v-col>
      </v-row>

      <div v-if="layer_state_items.indexOf('linewidth') !== -1">
        <div style="display: grid"> <!-- overlay container -->
          <div style="grid-area: 1/1">
            <v-row class="row-no-outside-padding">
              <v-col cols="8">
                <glue-float-field label="Line Width" :value.sync="linewidth" />
              </v-col>
              <v-col cols="4" style="text-align: center">
                <v-icon v-for="index in linewidth_vs">mdi-alpha-{{String.fromCharCode(97 + index)}}-box-outline</v-icon>
              </v-col>
            </v-row>
          </div>
          <j-tooltip  v-if="linewidth_mixed" tipid='plugin-plot-options-mixed-state' spanStyle="display: grid; grid-area: 1/1">
            <div
              @click="() => {unmix_state('linewidth')}"
              class="text-center"
              style="z-index:2;
                     margin-left: -24px;
                     margin-right: -24px;
                     padding-top: 60px;
                     cursor: pointer;
                     background-color: rgb(0 0 0 / 20%)">
              <v-icon large dark style="bottom: 100%">mdi-link-off</v-icon>
            </div>
          </j-tooltip>
          </div>
        </div>
      </div>

      <div v-if="layer_state_items.indexOf('percentile') !== -1">
        <div style="display: grid"> <!-- overlay container -->
          <div style="grid-area: 1/1">
            <v-row class="row-no-outside-padding">
              <v-col cols="8">
                <v-select
                  :items="percentile_items"
                  v-model="percentile_selected"
                  label="Percentile"/>
              </v-col>
              <v-col cols="4" style="text-align: center">
                <v-icon v-for="index in percentile_vs">mdi-alpha-{{String.fromCharCode(97 + index)}}-box-outline</v-icon>
              </v-col>
            </v-row>
          </div>
          <j-tooltip  v-if="percentile_mixed" tipid='plugin-plot-options-mixed-state' spanStyle="display: grid; grid-area: 1/1">
            <div
              @click="() => {unmix_state('percentile')}"
              class="text-center"
              style="z-index:2;
                     margin-left: -24px;
                     margin-right: -24px;
                     padding-top: 60px;
                     cursor: pointer;
                     background-color: rgb(0 0 0 / 20%)">
              <v-icon large dark style="bottom: 100%">mdi-link-off</v-icon>
            </div>
          </j-tooltip>
          </div>
        </div>
      </div>




    </div>

  </j-tray-plugin>
</template>
