<template>
  <j-tray-plugin
    description='Show instrument footprints.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#footprints'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :popout_button="popout_button">


  </j-tray-plugin>
</template>
