<script setup lang="ts">
/**
 * IMS 应用根组件
 * 已登录停在壳路径时仍套 AppLayout，用来放「尚未分配权限」提示。
 */
import { RouterView, type RouteLocationNormalizedLoaded } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

function isBare(route: RouteLocationNormalizedLoaded): boolean {
  if (route.meta.menuless) return true
  if (route.meta.public && !(route.meta.shell && authStore.isLoggedIn)) return true
  return false
}
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <component :is="Component" v-if="isBare(route)" />
    <AppLayout v-else>
      <component :is="Component" />
    </AppLayout>
  </RouterView>
</template>

<style>
/* 全局样式已在 main.ts 中引入 */
</style>
