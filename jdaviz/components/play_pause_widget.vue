<template>
  <v-toolbar-items :class="{active: activeInterval}">
    <j-tooltip tipid='table-play-pause-toggle'>
      <v-btn icon @click="togglePlayPause" color="white">
        <v-icon>mdi-play-pause</v-icon>
      </v-btn>
    </j-tooltip>
    <j-tooltip tipid='table-play-pause-delay'>
      <v-text-field
        v-model="delaySeconds"
        type="number"
        min="1"
        max="60"
        @change="changeDelay"
        @mousedown="changeDelay"
        class="mt-0 pt-0 theme--dark"
        style="width: 60px"
        hide-details
        single-line
        filled
        dense
      />
    </j-tooltip>
  </v-toolbar-items>
</template>

<script>

//var activeInterval = null;

module.exports = {
  data: function () {
    return {
      activeInterval: null,
      delaySeconds: 2
    }
  },
  props: [],
  methods: {
    eachIteration() {
      this.$emit('event')
    },
    clearActiveInterval() {
      if (this.activeInterval) {
        clearInterval(this.activeInterval)
      }
      this.activeInterval = null
    },
    createNewInterval() {
      this.activeInterval = setInterval(() => this.eachIteration(), this.delaySeconds*1000)
    },
    changeDelay(event) {
      if (this.delaySeconds <= 0) {
        // reject zero and negative values
        this.delaySeconds = 1
      }
      if (this.activeInterval !== null) {
        // then we want to clear the current interval and immediately create a new one,
        // while leaving it in the play state
        this.clearActiveInterval()
        this.createNewInterval()     
      }
    },
    togglePlayPause() {
      if (this.activeInterval === null) {
        // make sure to call IMMEDIATELY for feedback that something is happening
        this.eachIteration()
        this.createNewInterval()
      } else {
        this.clearActiveInterval()
      }

    },
  }
};
</script>
