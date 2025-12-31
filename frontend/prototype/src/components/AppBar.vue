<script lang="ts" setup>
import logoLight from '@/assets/MKP_Logo_Webseite.svg'
import logoDark from '@/assets/MKP_Logo_Webseite_inverted.svg'
import CustomIcon from '../components/CustomIcon.vue'

const emit = defineEmits(['toggle-theme'])

const handleToggle = () => {
  emit('toggle-theme')
}

const props = defineProps(['isDark'])
</script>

<template>
  <div id="app-bar" :class="{ 'dark-mode': isDark }">
    <div class="uk-position-left" id="logo_container">
      <img :src="logoDark" class="logo-img" alt="Logo_dark" width="280px" v-if="props.isDark" />
      <img :src="logoLight" class="logo-img" alt="Logo_light" width="280px" v-else />
    </div>

    <div
      class="uk-position-right"
      id="toggle_container"
      style="cursor: pointer"
      @click="handleToggle"
    >
      <CustomIcon v-if="isDark" name="sun" />
      <CustomIcon v-else name="moon" />
    </div>
  </div>
</template>

<style scoped>
#app-bar {
  color: black;
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
  color: white;
  background-color: var(--mkpDarkNav);
}

#toggle_container {
  margin-top: 16px;
  margin-right: 16px;
}

#logo_container {
  margin-left: 20px;
  margin-top: 12px;
  height: 50px;
  width: auto;
}

.logo-img {
  user-select: none;
}
</style>
