<template>
  <div class="plugin-table-component">
    <v-row style="margin: 0px 0px -8px 0px !important">
      <div class="row-select">
        <v-select
          class="no-hint"
          v-model="headers_visible"
          :items="headers_avail"
          @change="$emit('update:headers_visible', $event)"
          label="Columns"
          multiple
        >
        <template v-slot:selection="{ item, index }">
          <span
            v-if="index === 0"
            class="grey--text text-caption"
          >
            ({{ headers_visible.length}} selected)
          </span>
        </template>
        <template v-slot:prepend-item>
          <v-list-item
            ripple
            @mousedown.prevent
            @click="() => {if (headers_visible.length < headers_avail.length) { headers_visible = headers_avail} else {headers_visible = []}}"
          >
            <v-list-item-action>
              <v-icon>
                {{ headers_visible.length == headers_avail.length ? 'mdi-close-box' : headers_visible.length ? 'mdi-minus-box' : 'mdi-checkbox-blank-outline' }}
              </v-icon>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title>
                {{ headers_visible.length < headers_avail.length ? "Select All" : "Clear All" }}
              </v-list-item-title>
            </v-list-item-content>
          </v-list-item>
          <v-divider class="mt-2"></v-divider>
        </template>
        </v-select>
      </div>
      <div style="line-height: 64px; width=32px" class="only-show-in-tray">
        <j-plugin-popout :popout_button="popout_button"></j-plugin-popout>
      </div>
    </v-row>

    <v-row style="margin: 0px 0px 8px 0px !important">
      <v-data-table
        dense
        :headers="headers_visible_sorted.map(item => {return {'text': item, 'value': item}})"
        :items="items"
        class="elevation-1 width-100"
      ></v-data-table>
    </v-row>

    <v-row v-if="clear_table" justify="end">
      <v-btn
        color="primary"
        text
        @click="clear_table"
        >Clear Table
      </v-btn>
    </v-row>
  </div>
</template>

<script>
module.exports = {
  computed: {
    headers_visible_sorted() {
      return this.headers_avail.filter(item => this.headers_visible.indexOf(item) !== -1);
    },
  }
};
</script>


<style scoped>
  .v-data-table {
    width: 100% !important
  }

  .only-show-in-tray {
    display: none;
  }
  .tray-plugin .only-show-in-tray {
    display: inline-block;
  }

  .row-select {
    width: 100%;
  }
  .tray-plugin .row-select {
    width: calc(100% - 40px)
  }

  .plugin-table-component {
    margin: 12px;
  }
  .tray-plugin .plugin-table-component {
    margin: 0px -12px 0px -12px;
  }

</style>
