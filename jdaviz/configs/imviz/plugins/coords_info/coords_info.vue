<template>
  <div v-if="pixel" style="white-space: nowrap;">
    <table>
      <tr>
        <td colspan="4">
          <b v-if="pixel">Pixel </b>{{ pixel }}&nbsp;&nbsp;<b v-if="value">Value </b>{{ value }}
        </td>
      </tr>
      <tr>
        <td width="42"><b v-if="world_ra">World</b></td>
        <td width="115">{{ world_ra }}</td>
        <td width="120">{{ world_dec }}</td>
        <td><div v-if="world_ra">(ICRS)</div></td>
      </tr>
      <tr>
        <td width="42"></td>
        <td width="115">{{ world_ra_deg }}</td>
        <td width="120">{{ world_dec_deg }}</td>
        <td><div v-if="world_ra">(deg)</div></td>
      </tr>
    </table>
  </div>
</template>
