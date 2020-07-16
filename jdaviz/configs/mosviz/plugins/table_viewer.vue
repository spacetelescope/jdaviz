<template>
  <v-data-table
    v-model="state.selected_row"
    :headers="state.headers"
    :items="state.items"
    class="elevation-1"
    show-select
  >
<!--    <template v-slot:item.calories="{ item }">-->
<!--      <v-chip :color="get_color(item.calories)" dark>{{ item.calories }}</v-chip>-->
<!--    </template>-->
<!--    <template v-slot:item.spec1d="{ item }">-->
<!--        <v-select-->
<!--          :items="dc_items"-->
<!--      ></v-select>-->
<!--      </template>-->
<!--      <template v-slot:item.spec2d="{ item }">-->

<!--            <v-text-field-->
<!--              v-model="item.cutout"-->
<!--              label="Edit"-->
<!--              single-line-->
<!--              counter-->
<!--            ></v-text-field>-->
<!--      </template>-->
<!--      <template v-slot:item.cutout="{ item }">-->
<!--        <v-edit-dialog-->
<!--          :return-value.sync="item.cutout"-->
<!--        > {{ item.cutout }}-->
<!--          <template v-slot:input>-->
<!--              <v-select :items="dc_items" v-model="selected_dc_item"></v-select>-->
<!--              <v-select :items="comp_items" v-model="selected_comp_item"></v-select>-->
<!--          </template>-->
<!--        </v-edit-dialog>-->
<!--      </template>-->
  </v-data-table>
</template>