<script setup lang="ts">
import { RouterView } from 'vue-router'
import DefaultAppBar from "./components/AppBar.vue"

</script>

<template>
  <v-app>
    <!-- TOPBAR -->
    <default-app-bar />

    <!-- BODY -->
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>
