<script setup lang="ts">
import { RouterView } from 'vue-router'

const flags: Record<string, string> = {
  de: '🇩🇪',
  en: '🇬🇧',
}
</script>

<template>
  <div class="locale-changer" style="background-color: black">
    <select v-model="$i18n.locale">
      <option v-for="locale in $i18n.availableLocales" :key="`locale-${locale}`" :value="locale">
        {{ flags[locale] || '🌐' }} {{ locale.toUpperCase() }}
      </option>
    </select>
  </div>
  <RouterView />
</template>
