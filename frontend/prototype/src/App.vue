<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppBar from './components/AppBar.vue'
import { provide, ref } from 'vue'
const isDark = ref(false)
const toggleTheme = () => {
  isDark.value = !isDark.value
}

provide('isDark', isDark)
</script>

<template>
  <div class="main-layout" :class="{ 'dark-theme': isDark }">
    <AppBar :is-dark="isDark" @toggle-theme="toggleTheme" />

    <RouterView />
  </div>
</template>

<style scoped>
.main-layout {
  width: 100vw;
  height: 100vh;
}
</style>
