<template>
  <div v-if="pixel" style="white-space: nowrap; line-height: 14pt; margin: 0; position: absolute; top: 50%; transform: translateY(-50%); -ms-transform: translateY(-50%);">
    <table>
      <tr>
        <td colspan="4">
          <b v-if="pixel">Pixel </b>{{ pixel }}&nbsp;&nbsp;<b v-if="value">Value </b>{{ value }}
        </td>
      </tr>
      <tr>
        <td width="42"><b>{{ world_label_prefix }}</b></td>
        <td width="115">{{ world_ra }}</td>
        <td width="120">{{ world_dec }}</td>
        <td>{{ world_label_icrs }}</td>
      </tr>
      <tr>
        <td width="42"></td>
        <td width="115">{{ world_ra_deg }}</td>
        <td width="120">{{ world_dec_deg }}</td>
        <td>{{ world_label_deg }}</td>
      </tr>
    </table>
  </div>
</template>
