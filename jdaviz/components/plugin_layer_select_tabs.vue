<template>
  <div>
    <v-row>
      <v-col v-for="(item, index) in items">
        <v-btn :rounded="item.is_subset" :color="!item.mixed_color ? item.color : 'gray'" @click="() => {if (!multiselect){$emit('update:selected', item.label)} else if(selected.indexOf(item.label) === -1) {$emit('update:selected', selected.concat(item.label))} else {$emit('update:selected', selected.filter(select => select != item.label))} }">{{ item.icon }}</v-btn>


      </v-col>
    </v-row>
    <v-row>
      <span>{{ selected }}</span>
    </v-row>
 </div>
</template>

<script>
module.exports = {
  props: ['items', 'selected', 'multiselect']
};
</script>
