<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#collapse'">Collapse a spectral cube along one axis.</j-docs-link>
    </v-row>

    <v-row>
      <v-select
        :items="data_items"
        v-model="selected_data_item"
        label="Data"
        hint="Select the data set to use in collapse."
        persistent-hint
      ></v-select>
    </v-row>

    <v-row>
      <v-select
        :items="funcs"
        v-model="selected_func"
        label="Method"
        hint="Select the method to use in the collapse."
        persistent-hint
      ></v-select>
    </v-row>

    <div>
      <v-row>
        <mxn-subset-select 
          :spectral_subset_items="spectral_subset_items"
          :selected_subset.sync="selected_subset"
          hint="Select spectral region to apply the collapse."
        />
      </v-row>

      <v-row class="row-no-outside-padding">
        <v-col>
          <v-text-field
            label="Lower spectral bound"
            v-model="spectral_min"
            hint="Set lower bound."
            persistent-hint
          >
          </v-text-field>
        </v-col>
        <v-col cols = 2>
          <span>{{ spectral_unit }}</span>
        </v-col>
      </v-row>

      <v-row class="row-no-outside-padding">
        <v-col>
          <v-text-field
            label="Upper spectral bound"
            v-model="spectral_max"
            hint="Set upper bound."
            persistent-hint
          >
          </v-text-field>
        </v-col>
        <v-col cols = 2>
          <span>{{ spectral_unit }}</span>
        </v-col>
      </v-row>

      <v-row>
        <v-select
          :items="viewers"
          v-model="selected_viewer"
          label='Plot in Viewer'
          hint='Collapsed cube will replace plot in the specified viewer.  Will also be available in the data dropdown in all image viewers.'
          persistent-hint
        ></v-select>
      </v-row>

    </div>

    <v-row justify="end">
      <j-tooltip tipid='plugin-collapse-apply'>
        <v-btn color="accent" text @click="collapse">Apply</v-btn>
      </j-tooltip>
    </v-row>
  </j-tray-plugin>
</template>
