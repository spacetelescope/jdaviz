<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#line-analysis'">
        Return statistics for a single spectral line.  See the <j-external-link link="https://specutils.readthedocs.io/en/stable/analysis.html" linktext="specutils docs"/> for more details.
      </j-docs-link>
    </v-row>

    <j-plugin-section-header>Line</j-plugin-section-header>
    <v-row>
      <j-docs-link>Choose a region that defines the spectral line.</j-docs-link>
    </v-row>

    <v-row v-if="dc_items.length > 1">
      <v-select
        :items="dc_items"
        v-model="selected_spectrum"
        label="Data"
        hint="Select the data set to be analysed."
        persistent-hint
      ></v-select>
    </v-row>

    <v-row>
      <v-select
        :items="spectral_subset_items"
        v-model="selected_subset"
        label="Spectral Region"
        hint="Select spectral region that defines the line."
        persistent-hint
      ></v-select>
    </v-row>

    <j-plugin-section-header>Continuum</j-plugin-section-header>
    <v-row>
      <j-docs-link>
        {{selected_subset=='Entire Spectrum' ? "Since using the entire spectrum, the end points will be used to fit a linear continuum." : "Choose a region to fit a linear line as the underlying continuum."}}  
        {{selected_continuum=='Surrounding' && selected_subset!='Entire Spectrum' ? "Choose a width in number of data points to consider on each side of the line region defined above." : null}}
        When this plugin is opened, a visual indicator will show on the spectrum plot showing the continuum fitted as a thick line, and interpolated into the line region as a thin line.
      </j-docs-link>
    </v-row>

    <v-row>
      <v-select
        :items="continuum_subset_items"
        v-model="selected_continuum"
        label="Spectral Region"
        :rules="[() => selected_continuum!==selected_subset || 'Must not match line selection.']"
        hint="Select spectral region to fit linear line to represent the continuum."
        persistent-hint
      ></v-select>
    </v-row>

    <v-row v-if="selected_continuum=='Surrounding' && selected_subset!='Entire Spectrum'">
      <!-- DEV NOTE: if changing the validation rules below, also update the logic to clear the results
           in line_analysis.py  -->
      <v-text-field
        label="Width"
        type="number"
        v-model.number="width"
        step="0.1"
        :rules="[() => width!=='' || 'This field is required.',
                 () => width<=10 || 'Width must be <= 10.',
                 () => width>=1 || 'Width must be >= 1.']"
        hint="Width, relative to the overall line spectral region, to fit the linear continuum (excluding the region containing the line).  If 1, will use endpoints within line region only."
        persistent-hint
      >
      </v-text-field>
    </v-row>

    <j-plugin-section-header>Results</j-plugin-section-header>
    <div style="display: grid"> <!-- overlay container -->
      <div style="grid-area: 1/1">
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
      <div v-if="results_computing"
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
