<template>
    <div v-if="pixel" style="white-space: nowrap;">
        <b v-if="pixel">Pixel </b>{{ pixel }}&nbsp;&nbsp;<b v-if="value">Value </b>{{ value }}<br>
        <b v-if="world">World </b>{{ world }}<br>
        <b v-if="world">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</b>{{ world_deg }}<br>
    </div>
</template>
