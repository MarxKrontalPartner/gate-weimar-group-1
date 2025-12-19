<script lang="ts" setup>
import { useRouter } from "vue-router"
import logoLight from '@/assets/MKP_Logo_Webseite.svg'
import logoDark from '@/assets/MKP_Logo_Webseite_inverted.svg'

const props = defineProps(['isDark'])

</script>

<template>
  <div id="app-bar" :class="{ 'dark-mode': isDark }">
    <div class="uk-position-left" id="logo_container">
      <img :src="logoDark" alt="Logo_dark" width="280px" v-if="isDark">
      <img :src="logoLight" alt="Logo_light" width="280px" v-else>
    </div>
    
    </div>
</template>

<style scoped>
#app-bar {
  background-color: white; 
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 64px;
  z-index: 10;
  transition: background-color 0.3s ease; 
  box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2);
}

#app-bar.dark-mode {
  background-color: var(--mkpDarkNav); 
}

#logo_container {
  margin-left: 20px;
  margin-top: 12px;
  height: 50px;
  width: auto;
}
</style>
