<script setup lang="ts">
/**
 * 生产构建首页
 * 示例页只在 dev/test 注册；生产访问 /demo/* 会回到这里（§2.3 U4）
 */
</script>

<template>
  <main class="home-page">
    <h1>首页</h1>
    <p>IMS 工作台入口。示例页仅在开发环境提供。</p>
  </main>
</template>

<style lang="scss" scoped>
.home-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  background-color: var(--bg);
  color: var(--text);
  text-align: center;

  h1 {
    font-size: 24px;
    font-weight: 600;
  }

  p {
    font-size: 14px;
    color: var(--text2);
  }
}
</style>
