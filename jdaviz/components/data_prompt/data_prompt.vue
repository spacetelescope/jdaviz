
<template>
    <v-dialog v-model="dialog" persistent max-width="600px">
      <v-row>
        <v-col>

        <v-card class='d-flex flex-column mx-auto my-12' tile max-width=600>
            <div class='headline blue lighten-4'>
                <v-card-title >Data Prompt</v-card-title>
                <v-card-subtitle >{{ filename}} </v-card-subtitle>
            </div>
            <v-card-text>
                <v-alert dense outlined prominent type='error' v-if='status == "error"'> {{ status_msg }} </v-alert>
                <v-alert dense outlined prominent type='success' v-else-if='status == "success"'> {{ status_msg }} </v-alert>
                <v-alert dense outlined prominent type='warning' v-else> {{ status_msg }} </v-alert>
            </v-card-text>

            <v-divider></v-divider>

            <v-row dense>
                <v-col>
                    <v-card class='mx-auto' tile>
                        <v-card-title>Product Info</v-card-title>
                        <v-card-text>
                            <v-list disabled two-line dense>
                                <v-list-item-group>
                                    <v-list-item v-for='product in products'>
                                        <v-list-item-content>
                                            <v-list-item-title><p class="font-weight-black">{{ product.title}}:</p></v-list-item-title>
                                            <v-list-item-subtitle>{{ product.subtitle }}</v-list-item-subtitle>
                                        </v-list-item-content>
                                    </v-list-item>
                                </v-list-item-group>
                            </v-list>
                        </v-card-text>
                    </v-card>
                </v-col>
                <v-col>
                    <v-card class='mx-auto' tile>
                        <v-card-title>Jdaviz Configuration</v-card-title>
                        <v-card-text>
                            <v-list disabled two-line dense>
                                <v-list-item-group>
                                    <v-list-item v-for='config in configs'>
                                        <v-list-item-content>
                                            <v-list-item-title><p class="font-weight-black">{{ config.ltitle}}:</p></v-list-item-title>
                                            <v-list-item-subtitle>{{ config.lsubtitle }}</v-list-item-subtitle>
                                        </v-list-item-content>
                                        <v-list-item-content>
                                            <v-list-item-title><p class="font-weight-black">{{ config.rtitle}}:</p></v-list-item-title>
                                            <v-list-item-subtitle>{{ config.rsubtitle }}</v-list-item-subtitle>
                                        </v-list-item-content>
                                    </v-list-item>
                                </v-list-item-group>
                            </v-list>
                        </v-card-text>
                    </v-card>
                </v-col>
            </v-row>

            <v-divider></v-divider>

            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn color="primary" text @click="close">Close</v-btn>
            </v-card-actions>
        </v-card>
        </v-col>
      </v-row>

    </v-dialog>
</template>