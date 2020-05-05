<template>
  <v-card flat tile>
    <v-container>
      <v-row>
        <v-col class="py-0">
          <v-select
            :items="data_items"
            v-model="selected_data_item"
            label="Data"
            hint="Select the data set to use in collapse."
            persistent-hint
          ></v-select>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-select
            :items="axes"
            v-model="selected_axis"
            label="Axis"
            hint="Select the axis along with the data with be collapsed."
            persistent-hint
          ></v-select>
        </v-col>
        <v-col>
          <v-select
            :items="funcs"
            v-model="selected_func"
            label="Method"
            hint="Select the method to use in the collapse."
            persistent-hint
          ></v-select>
        </v-col>
      </v-row>
    </v-container>
    <!-- <v-divider></v-divider> -->

    <v-card-actions>
      <div class="flex-grow-1"></div>
      <v-btn color="primary" text @click="collapse">Apply</v-btn>
    </v-card-actions>
  </v-card>
</template>
