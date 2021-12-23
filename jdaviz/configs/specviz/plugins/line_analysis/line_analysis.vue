<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#line-analysis'">
        Return statistics for a single spectral line.  The results are meaningful only when the continuum is properly normalized or subtracted, depending on the function you are interested in. See the <j-external-link link="https://specutils.readthedocs.io/en/stable/analysis.html" linktext="specutils docs"/> for more details.
      </j-docs-link>
    </v-row>

    <v-row>
      <v-select
        :items="dc_items"
        v-model="selected_spectrum"
        label="Data"
        hint="Select the data set to be fitted."
        persistent-hint
      ></v-select>
    </v-row>

    <v-row>
      <v-select
        :items="spectral_subset_items"
        v-model="selected_subset"
        label="Spectral Region"
        hint="Select spectral region to apply the collapse."
        persistent-hint
      ></v-select>
    </v-row>

    <div v-if="result_available">
      <j-plugin-section-header>Results</j-plugin-section-header>
      <v-row>
        <v-col cols=6><U>Function</U></v-col>
        <v-col cols=6><U>Result</U></v-col>
      </v-row>
      <v-row 
        v-for="item in results"
        :key="item.function">
        <v-col cols=6>
          {{  item.function  }}
          <j-tooltip :tooltipcontent="'specutils '+item.function+' documentation'">
            <a v-bind:href="'https://specutils.readthedocs.io/en/stable/api/specutils.analysis.'+item.function.toLowerCase().replaceAll(' ', '_')+'.html'" 
              target="__blank" 
              style="color: #A75000">
              <v-icon x-small color="#A75000">mdi-open-in-new</v-icon>
            </a> 
          </j-tooltip>
        </v-col>
        <v-col cols=6>{{ item.result }}</v-col>
      </v-row>
    </div>
  </j-tray-plugin>
</template>
