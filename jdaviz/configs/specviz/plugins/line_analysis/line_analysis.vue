<template>
  <v-card flat tile>
    <v-card>
      <v-card-text>
        <v-container>
          <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#line-analysis'">
            Return statistics for a single spectral line.  The results are meaningful only when the continuum is properly normalized or subtracted, depending on the function you are interested in. See the <j-external-link link="https://specutils.readthedocs.io/en/stable/analysis.html" linktext="specutils docs"/> for more details.
          </j-docs-link>
          <v-row>
            <v-col>
              <v-select
                :items="dc_items"
                @change="data_selected"
                label="Data"
                hint="Select the data set to be fitted."
                persistent-hint
              ></v-select>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-divider></v-divider>

      <v-card-text v-if="result_available">
        <v-container>
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
        </v-container>
      </v-card-text>
      <v-divider></v-divider>
    </v-card>
  </v-card>
</template>
