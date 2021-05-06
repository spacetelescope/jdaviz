
<template>
    <v-dialog v-model="dialog" persistent max-width="600px">
      <v-row>
        <v-col>

        <v-card class='d-flex flex-column mx-auto my-12'>
            <v-card-title class='headline blue lighten-4'>Data Prompt: {{ filename }}</v-card-title>
            <v-card-text>
                <v-alert dense outlined prominent type='error' v-if='status == "error"'> {{ status_msg }} </v-alert>
                <v-alert dense outlined prominent type='success' v-else-if='status == "success"'> {{ status_msg }} </v-alert>
                <v-alert dense outlined prominent type='warning' v-else> {{ status_msg }} </v-alert>
            </v-card-text>

            <v-divider></v-divider>

            <v-card-text class='d-flex'>
                <v-row>
                    <v-col><p class="font-weight-black">Mission:</p> {{ header['TELESCOP'] }}</v-col>
                    <v-col><p class="font-weight-black">Instrument:</p> {{ header['INSTRUME'] }}</v-col>
                </v-row>
                <v-row>
                    <v-col><p class="font-weight-black">Exposure Type:</p>{{ header['EXP_TYPE'] }}</v-col>
                    <v-col><p class="font-weight-black">Template:</p>{{ header['TEMPLATE'] }}</v-col>
                </v-row>
            </v-card-text>

            <v-divider></v-divider>

            <v-card-text class='d-flex'>
                <v-row>
                    <v-col><p class="font-weight-black">Data Format:</p>{{ data_format }}</v-col>
                    <v-col><p class="font-weight-black">Current Config:</p>{{ current }}</v-col>
                </v-row>
                <v-row>
                    <v-col><p class="font-weight-black">Suggested Format:</p>{{ suggested_format }}</v-col>
                    <v-col><p class="font-weight-black">Suggested Config:</p>{{ suggested_config }}</v-col>
                </v-row>
                <v-row>
                    <v-col><p class="font-weight-black">Config:</p>{{ config }}</v-col>
                </v-row>
            </v-card-text>

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