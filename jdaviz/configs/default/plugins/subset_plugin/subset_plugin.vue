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
    <v-row v-if="config=='imviz' && is_editable">
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

    <!-- Composite region cannot be edited, so just grab first element. -->
    <div v-if="is_editable">
      <v-row v-for="(item, index2) in subset_definitions[0]"
       class="pt-0 pb-0 mt-0 mb-0">
        <v-text-field
          :label="item.name"
          v-model.number="item.value"
          type="number"
        ></v-text-field>
      </v-row>

      <v-row justify="end" no-gutters>
        <v-btn color="primary" text @click="update_subset">Update</v-btn>
      </v-row>
    </div>

    <div v-if="show_region_info">
      <j-plugin-section-header>Subset Region Definition</j-plugin-section-header>
      <div v-if="subset_definitions.length">
        <v-row v-for="(subset_definition, index) in subset_definitions" no-gutters>
          <v-col>
            <v-row class="pt-0 pb-0 mt-0 mb-0">
              <v-col>Subset type:</v-col>
              <v-col>{{ subset_types[index] }}</v-col>
            </v-row>
            <v-row v-for="(item, index2) in subset_definition"
             class="pt-0 pb-0 mt-0 mb-0" no-gutters>
              <v-col>{{ item.name }}:</v-col>
              <v-col>
                <j-number-uncertainty
                  :value="item.orig"
                  :defaultDigs="6"
                ></j-number-uncertainty>
              </v-col>
            </v-row>
          </v-col>
        </v-row>
      </div>
    </div>
  </j-tray-plugin>
</template>
