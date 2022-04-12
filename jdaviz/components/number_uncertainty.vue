<template>
  <span>
    {{ valueTrunc }} {{ uncertainty ? "&#177; " + uncertTrunc : null}} {{ unit }}
  </span>
</template>

<script>

module.exports = {
  data: function () {
    const maxDecs = this.maxDecs || 5;
    return {
      // default to passed values, whenever value or uncertainty are changed
      // updateTruncatedValues will overwrite the displayed values
      maxDecs: maxDecs,
      valueTrunc: this.value,
      uncertTrunc: this.uncertainty
    }
  },
  methods: {
    updateTruncatedValues() {
      if (this.uncertainty !== '') {
        // then uncertainty was provided, so let's round both the uncertainty and value
        // to show up to the second significant digit in the uncertainty.
        var nDecs = 2 - Math.log10(parseFloat(this.uncertainty));
        if (nDecs > this.maxDecs) {
          nDecs = this.maxDecs
        } else if (nDecs < 0) {
          // NOTE: could support rounding of integers to less significant digits, but for now
          // we'll at least show all digits before the decimal.
          nDecs = 0
        }

        this.uncertTrunc = +parseFloat(this.uncertainty).toFixed(nDecs)
      }

      this.valueTrunc = +parseFloat(this.value).toFixed(nDecs);
    }
  },
  watch: {
    value() {
      this.updateTruncatedValues();
    },
    uncertainty() {
      this.updateTruncatedValues();
    }
  },
  props: ['value', 'uncertainty', 'unit', 'maxDecs'],
};
</script>
