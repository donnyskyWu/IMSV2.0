<script setup lang="ts">
/**
 * 侧栏节点。目录继续展开，叶子才作为可点菜单。
 * 公司资产是三级：公司资产 → 资源管理 → 页面。版本 v1.0 · 2026-10-13
 */
import type { MenuItem } from '@/types'

defineProps<{ item: MenuItem }>()
</script>

<template>
  <el-sub-menu v-if="item.children?.length" :index="item.id">
    <template #title>
      <el-icon v-if="item.icon">
        <component :is="item.icon" />
      </el-icon>
      <span>{{ item.name }}</span>
    </template>
    <SidebarMenuTree v-for="child in item.children" :key="child.id" :item="child" />
  </el-sub-menu>
  <el-menu-item v-else :index="item.path || item.id">
    <el-icon v-if="item.icon">
      <component :is="item.icon" />
    </el-icon>
    <span>{{ item.name }}</span>
  </el-menu-item>
</template>
