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

    <v-row v-if="has_angle">
      <v-col>
        <v-text-field
          ref="new_subset_angle"
          label="New Angle"
          v-model="new_subset_angle"
          hint="New angle in degrees for subset."
          persistent-hint
        ></v-text-field>
      </v-col>
    </v-row>

    <v-row v-if="has_angle" justify="end">
      <v-btn color="primary" text @click="update_subset">Update</v-btn>
    </v-row>

    <div v-if="show_region_info">
      <j-plugin-section-header>Subset Region Definition</j-plugin-section-header>
      </v-row>
      <div v-if="subset_definitions.length">
        <v-row v-for="(subset_definition, index) in subset_definitions">
          <v-col>
            <v-row v-for="(val, key, index2) in subset_types[index]"
             class="pt-0 pb-0 mt-0 mb-0">
              <v-col>{{ key }}:</v-col>
              <v-col>{{ val }}</v-col>
            </v-row>
            <v-row v-for="(val, key, index2) in subset_definition"
             class="pt-0 pb-0 mt-0 mb-0">
              <v-col>{{ key }}:</v-col>
              <v-col>
                <j-number-uncertainty
                  :value="val"
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
