<template>
  <v-treeview :items="items"
              hoverable
              activatable
              dense
              @update:active="selected = $event"
  ></v-treeview>
</template>
