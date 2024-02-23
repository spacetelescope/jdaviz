<template>
  <div :class="active ? 'strike strike-active': 'strike'">
     <span>
       <slot></slot>
     </span>
  </div>
</template>

<script>
module.exports = {
  props: ['active'],
};
</script>


<style scoped>
.strike {
    display: block;
    text-align: center;
    overflow: hidden;
    white-space: nowrap; 
    margin-left: -12px;
    margin-right: -12px;
    margin-top: 36px;
    margin-bottom: 8px;
}

.strike > span {
    position: relative;
    display: inline-block;
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

.strike-active > span:before,
.strike-active > span:after {
    background: #c75d2c;  /* active orange */
}

.strike > span:before {
    right: 100%;
    margin-right: 15px;
}

.strike > span:after {
    left: 100%;
    margin-left: 15px;
}
</style>
