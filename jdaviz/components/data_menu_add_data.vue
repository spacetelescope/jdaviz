<template>
  <v-menu
    absolute
    offset-y
    left
  >
    <template v-slot:activator="{ on, attrs }">
      <j-tooltip tooltipcontent="Add data or subset to viewer">
        <v-btn
          icon
          v-bind="attrs"
          v-on="on"
        >
          <v-icon>mdi-plus</v-icon>
        </v-btn>
      </j-tooltip>
    </template>
    <v-list dense style="width: 200px">
      <v-subheader class="strike" v-if="dataset_items.length > 0"><span>Load Data</span></v-subheader>
      <v-list-item
        v-for="item in dataset_items"
      >
        <v-list-item-content>
          <j-tooltip tooltipcontent="add data to viewer">
            <span
              style="cursor: pointer; width: 100%"
              @click="() => {$emit('add-data', item.label)}"
            >
              {{  item.label }}
            </span>
          </j-tooltip>
        </v-list-item-content>
      </v-list-item>
      <v-subheader class="strike"><span>Create Subset</span></v-subheader>
      <v-list-item
      >
        <v-list-item-content style="display: inline-block">
          <j-tooltip
            v-for="tool in subset_tools"
            span_style="display: inline-block"
            :tooltipcontent="'Create new '+tool.name+' subset'"
          >
            <v-btn 
              icon
              @click="() => {$emit('create-subset', tool.name)}"
            >
              <img :src="tool.img" width="20"/>
            </v-btn>
          </j-tooltip>
        </v-list-item-content>
      </v-list-item>
    </v-list>
  </v-menu>

</template>

<script>
module.exports = {
  props: ['dataset_items', 'subset_tools'],
};
</script>

<style scoped>
.strike {
    display: block;
    text-align: center;
    height: 28px !important;
}

.strike > span {
    position: relative;
    display: inline-block;
    text-transform: uppercase;
    font-weight: bold;
}

.strike > span:before,
.strike > span:after {
    content: "";
    position: absolute;
    top: 50%;
    width: 9999px;
    height: 1px;
    background: gray;
}

.strike > span:before {
    right: 100%;
    margin-right: 6px;
}

.strike > span:after {
    left: 100%;
    margin-left: 6px;
}
</style>