<script setup lang="ts">
/**
 * 登录后的兜底页（FP-B1-LG-08）
 * 菜单叶子路径尚未登记，或菜单为空时进入这里。
 * 无菜单时的说明由 AppLayout 展示，本页不伪造组织 / 岗位页面。
 */
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <div class="account-home" :data-user-id="authStore.user?.id || ''">
    <h1>{{ authStore.user?.nickname || '已登录' }}</h1>
  </div>
</template>

<style lang="scss" scoped>
.account-home {
  padding: 8px 0;

  h1 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: var(--text);
  }
}
</style>
