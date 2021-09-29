<template>
  <v-card flat tile>
    <!-- <v-divider></v-divider> -->
    <v-container>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#slit-overlay'">Add a slit to the image viewer</j-docs-link>
      <v-row>
        <v-col>
          <v-card-actions>
            <div class="flex-grow-1">
              <v-row>
                <v-switch
                  label="Visible"
                  hint="Show slit in the image viewer."
                  v-model="visible"
                  @click.native="change_visible"
                  persistent-hint>
                </v-switch>
              </v-row>
            </div>
          </v-card-actions>
        </v-col>
      </v-row>
    </v-container>

  </v-card>
</template>
