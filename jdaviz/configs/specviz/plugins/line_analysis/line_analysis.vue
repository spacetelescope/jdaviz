<template>
  <v-card flat tile>
    <v-card>
      <v-card-text>
        <v-container>
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

      <v-card-text>
        <v-container>
          <v-row>
            <v-col cols=6><U>Function</U></v-col>
            <v-col cols=6><U>Result</U></v-col>
          </v-row>
          <v-row 
            v-if="result_available"
            v-for="item in results"
            :key="item.function">
            <v-col cols=6>{{  item.function  }} </v-col>
            <v-col cols=6>{{ item.result }}</v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-divider></v-divider>
    </v-card>
  </v-card>
</template>
