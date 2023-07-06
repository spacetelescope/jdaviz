<template>
  <j-tray-plugin
    description='Tools for selecting and interacting with subsets.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#subset-tools'"
    :popout_button="popout_button">

    <v-row align=center>
      <v-col cols=10 justify="left">
        <plugin-subset-select 
          :items="subset_items"
          :selected.sync="subset_selected"
          :show_if_single_entry="true"
          label="Subset"
          hint="Select subset to edit."
        />
      </v-col>

      <v-col justify="center" cols=2>
        <j-tooltip tipid='g-subset-mode'>
          <g-subset-mode></g-subset-mode>
        </j-tooltip>
      </v-col>
    </v-row>

    <!-- Sub-plugin for recentering of spatial subset (Imviz only) -->
    <v-row v-if="config=='imviz' && is_centerable">
      <v-expansion-panels accordion v-model="subplugins_opened">
        <v-expansion-panel>
          <v-expansion-panel-header >
            <span style="padding: 6px">Recenter</span>
          </v-expansion-panel-header>
          <v-expansion-panel-content>
            <plugin-dataset-select
             :items="dataset_items"
             :selected.sync="dataset_selected"
             :show_if_single_entry="true"
             label="Data"
             hint="Select the data for centroiding."
            />
            <v-row justify="end" no-gutters>
              <v-btn color="primary" text @click="recenter_subset">Recenter</v-btn>
            </v-row>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-row>

    <!-- Show all subregions of a subset, including Glue state and subset type. -->
    <div v-for="(region, index) in subset_definitions">
       <j-plugin-section-header style="margin: 0px; margin-left: -12px; text-align: left; font-size: larger; font-weight: bold">
       Subregion {{ index }}</j-plugin-section-header>
       <v-row class="row-no-outside-padding">
        <div style="margin-top: 4px">
            {{ subset_types[index] }} applied with
        </div>
        <div style="margin-top: -2px; padding-bottom: 8px">
            <div v-if="index === 0">
              <img :src="icon_replace" width="20"/>
              replace mode
            </div>
            <div v-else-if="glue_state_types[index] === 'AndState'">
              <img :src="icon_and" width="20"/>
              and mode
            </div>
            <div v-else-if="glue_state_types[index] === 'OrState'">
              <img :src="icon_or" width="20"/>
              add mode
            </div>
            <div v-else-if="glue_state_types[index] === 'AndNotState'">
              <img :src="icon_andnot" width="20"/>
              remove mode
            </div>
            <div v-else-if="glue_state_types[index] === 'XorState'">
              <img :src="icon_xor" width="20"/>
              xor mode
            </div>
        </div>
      </v-row>

      <v-row v-for="(item, index2) in region" class="row-no-outside-padding">
        <v-text-field
          :label="item.name"
          v-model.number="item.value"
          type="number"
          style="padding-top: 0px; margin-top: 0px"
          :suffix="item.unit ? item.unit.replace('Angstrom', 'A') : ''"
        ></v-text-field>
      </v-row>
    </div>

    <v-row justify="end">
      <j-tooltip v-if="can_simplify" tooltipcontent="Convert composite subset to use only add mode to connect subregions">
        <v-btn color="primary" text @click="simplify_subset">Simplify</v-btn>
      </j-tooltip>
      <v-btn color="primary" text @click="update_subset">Update</v-btn>
    </v-row>
  </j-tray-plugin>
</template>
