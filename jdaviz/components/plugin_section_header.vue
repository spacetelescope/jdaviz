<template>
  <div class="strike text--secondary">
     <span>
       <slot></slot>
     </span>
  </div>
</template>


<style scoped>
.strike {
    display: block;
    text-align: center;
    overflow: hidden;
    white-space: nowrap; 
    margin-left: -12px;
    margin-right: -12px;
    margin-top: 40px;
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
    background: rgba(0, 0, 0, 0.15);
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
