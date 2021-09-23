<template>
  <v-card flat tile>
    <v-card>
      <v-card-text>
        <v-container>
          <v-row>
            <v-col>
              <v-select
                :items="link_types"
                @change="link_type_selected"
                label="Link type"
                hint="Type of linking to be done."
                persistent-hint
              ></v-select>
            </v-col>
          </v-row>
        </v-container>
        <v-container>
          <v-row>
            <v-col>
              <v-select
                :items="wcs_fallback_schemes"
                @change="wcs_fallback_scheme_selected"
                label="WCS fallback scheme"
                hint="If WCS linking fails, fall back to linking by pixels or not at all."
                persistent-hint
              ></v-select>
            </v-col>
          </v-row>
        </v-container>
        <v-container>
          <v-row>
            <v-col>
              <v-select
                :items="wcs_use_affine_options"
                @change="affine_option_selected"
                label="Use affine transform"
                hint="Use affine transform for WCS, if possible."
                persistent-hint
              ></v-select>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-divider></v-divider>
      <v-card-actions>
        <div class="flex-grow-1"></div>
        <v-row
          justify="left"
          align="center"
          no-gutters
        >
        <v-btn color="primary" text @click="do_link">Link</v-btn>
        </v-row>
      </v-card-actions>
    </v-card>
  </v-card>
</template>
