<script setup lang="ts">
/**
 * IMS 应用根组件
 */
import { RouterView } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <!-- 公开页面（登录等）不使用布局 -->
    <template v-if="route.meta.public || route.meta.menuless">
      <component :is="Component" />
    </template>
    <!-- 业务页面使用布局 -->
    <template v-else>
      <AppLayout>
        <component :is="Component" />
      </AppLayout>
    </template>
  </RouterView>
</template>

<style>
/* 全局样式已在 main.ts 中引入 */
</style>
