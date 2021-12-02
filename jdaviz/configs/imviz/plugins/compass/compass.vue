<template>
  <div v-if="data_label">DATA: {{ data_label }}
  <img v-if="img_data" :src="`data:image/png;base64,${img_data}`" />
  </div>
</template>
