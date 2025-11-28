<template>
  <!-- App Bar with primary color -->
  <v-app-bar elevation="2">
    <span width="280px" v-if="theme.global.current.value.dark">
      <v-img :src="logoDark" />
    </span>
    <span width="280px" v-else>
      <v-img :src="logoLight" />
    </span>

    <!-- Spacer -->
    <v-spacer />

    <!-- Toggle button to switch themes -->
    <v-btn icon @click="toggleTheme" color="background">
      <v-icon class="text-primary"> mdi-theme-light-dark</v-icon>
    </v-btn>
    <v-btn icon @click="router.push('/')" color="background">
      <v-icon class="text-primary"> mdi-home-outline</v-icon>
    </v-btn>
  </v-app-bar>
</template>

<script lang="ts" setup>
import { useTheme } from 'vuetify'
import { useRouter } from "vue-router"
import logoLight from '@/assets/MKP_Logo_Webseite.svg'
import logoDark from '@/assets/MKP_Logo_Webseite_inverted.svg'

const theme = useTheme()
const router = useRouter()

function toggleTheme() {
  theme.global.name.value = theme.global.current.value.dark ? 'mkpLightTheme' : 'mkpDarkTheme'
}


</script>

<!-- <style lang="scss" scoped> -->
<style scoped>
.v-img {
  height: 30px !important;
  width: 250px !important;
  min-width: 250px !important;
}

.v-icon {
  min-height: 50px;
  min-width: 50px;
}

/* Button Hover-Effekte */
.v-btn:hover {
  background-color: rgba(var(--v-theme-primary), 0.15) !important;
}

/* Smooth Transition für Hover */
.v-btn {
  transition: background-color 0.2s ease !important;
}
</style>
