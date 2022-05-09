<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+
                          '/plugins.html#subset-tools'">
        Tools for selecting and interacting with subsets.
      </j-docs-link>
    </v-row>
  
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

    <div v-if="show_region_info">
      <j-plugin-section-header>Subset Region Definition</j-plugin-section-header>
      <v-row>
        <v-col>Subset Type: </v-col>
        <v-col>{{ subset_classname }}</v-col>
      </v-row>
      <div v-if="has_subset_details">
        <v-row v-for="(val, key, index) in subset_definition">
          <v-col>{{ key }}:</v-col> 
          <v-col>
            <j-number-uncertainty
              :value="val"
              :defaultDigs="6"
            ></j-number-uncertainty>
          </v-col>
        </v-row>
      </div>
      <div v-else>
        <v-row>Could not retrieve subset parameters for this subset type</v-row>
      </div>
    </div>
  </j-tray-plugin>
</template>
