<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#aper-phot-simple'">
        Perform aperture photometry for a single region.
      </j-docs-link>
    </v-row>

    <v-row>
      <v-select
        :items="dc_items"
        @change="data_selected"
        label="Data"
        hint="Select data for photometry."
        persistent-hint
      ></v-select>
    </v-row>

    <v-row>
      <v-select
        :items="subset_items"
        @change="subset_selected"
        label="Subset"
        hint="Select subset region for photometry."
        persistent-hint
      ></v-select>
    </v-row>

    <v-row>
      <v-text-field
        label="Background value"
        v-model="background_value"
        hint="Background to subtract, same unit as data"
        persistent-hint
      >
      </v-text-field>
    </v-row>

    <v-row>
      <v-text-field
        label="Pixel area"
        v-model="pixel_area"
        hint="Pixel area in arcsec squared, only used if sr in data unit"
        persistent-hint
      >
      </v-text-field>
    </v-row>

    <v-row>
      <v-text-field
        label="Counts conversion factor"
        v-model="counts_factor"
        hint="Factor to convert data unit to counts, in unit of flux/counts"
        persistent-hint
      >
      </v-text-field>
    </v-row>

    <v-row>
      <v-text-field
        label="Flux scaling"
        v-model="flux_scaling"
        hint="Same unit as data, used in -2.5 * log(flux / flux_scaling)"
        persistent-hint
      >
      </v-text-field>
    </v-row>

    <v-row justify="end">
      <v-btn color="primary" text @click="do_aper_phot">Calculate</v-btn>
    </v-row>


    <div v-if="result_available">
      <j-plugin-section-header>Results</j-plugin-section-header>
      <v-row>
        <v-col cols=6><U>Result</U></v-col>
        <v-col cols=6><U>Value</U></v-col>
      </v-row>
      <v-row
        v-for="item in results"
        :key="item.function">
        <v-col cols=6>
          {{  item.function  }}
        </v-col>
        <v-col cols=6>{{ item.result }}</v-col>
      </v-row>
    </div>
  </j-tray-plugin>
</template>
