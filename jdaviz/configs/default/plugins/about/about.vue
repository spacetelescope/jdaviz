<template>
  <j-tray-plugin
    :description="docs_description"
    :scroll_to.sync="scroll_to">

    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'" linktext="Jdaviz Documentation">
      </j-docs-link>
    </v-row>

    <v-row>
      <v-text-field class="v-messages v-messages__message text--secondary"
        v-model="jdaviz_version"
        label="Version"
        hint="Version of installed Jdaviz."
        readonly>
      </v-text-field>
    </v-row>

    <v-row v-for="pkg in downstream_packages" :key="pkg.name">
      <v-text-field class="v-messages v-messages__message text--secondary"
        :value="pkg.version"
        :label="pkg.name + ' Version'"
        :hint="'Version of installed ' + pkg.name + '.'"
        readonly>
      </v-text-field>
    </v-row>

    <div v-if="not_is_latest">
      <v-row>
        <span class="v-messages v-messages__message text--secondary" style="color: red !important">
          A newer version ({{ jdaviz_pypi }}) is available from PyPI.
        </span>
      </v-row>
      <v-row>
        <j-docs-link link="https://pypi.org/project/jdaviz/" linktext="Go to PyPI">
          Please update Jdaviz and restart your session.
        </j-docs-link>
      </v-row>
    </div>

    <v-row>
      <j-docs-link link="https://github.com/spacetelescope/jdaviz/blob/main/CHANGES.rst" linktext="Change Log">
        To see list of changes, go to your version section in the

      </j-docs-link>
    </v-row>

    <v-row>
      <j-docs-link link="https://jwsthelp.stsci.edu" linktext="JWST Help Desk">
        For further assistance, please contact the

      </j-docs-link>
    </v-row>

  </j-tray-plugin>
</template>
