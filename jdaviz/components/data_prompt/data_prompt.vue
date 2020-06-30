
<template>
    <v-dialog v-model="dialog" persistent max-width="500px">
      <v-row>
        <v-col>

      <v-card class="mx-auto my-12">
        <v-card-title class="headline blue lighten-4">Data Prompt</v-card-title>
        <v-card-text>Trying to load format "{{ data_format }}" using a "{{ current }}" configuration?</v-card-text>
        <v-divider></v-divider>
        <v-list dense>
          <v-list-item-grp dense>
            <v-list-item dense>
              <v-list-item-content><p class="font-weight-black">Data Format:</p>{{ data_format }}</v-list-item-content>
              <v-list-item-content class='align-end'><p class="font-weight-black">Recommended Config:</p>{{ config }}</v-list-item-content>
            </v-list-item>
            <v-list-item dense>
              <v-list-item-content><p class="font-weight-black">Current Config:</p>{{ current }}</v-list-item-content>
              <v-list-item-content class='align-end'><p class="font-weight-black">Status:</p>{{ status }}</v-list-item-content>
            </v-list-item>
          </v-list-item-grp>
        </v-list>
        <v-divider></v-divider>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="close">Close</v-btn>
          <v-btn color="primary" text @click="load_data">Load Anyway</v-btn>
        </v-card-actions>
      </v-card>

        </v-col>
      </v-row>

    </v-dialog>
</template>
