<script setup lang="ts">
/**
 * 文件演示页 (FP-P-08)
 */
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
</script>

<template>
  <AppLayout>
    <div class="files-demo">
      <PageHeader title="文件演示" sub-title="FP-P-08" />
      <div class="placeholder">
        <p>文件组件演示区域</p>
        <p>包含: FileUpload、FilePreview、ImportDialog、ExportButton + DownloadBar</p>
      </div>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.files-demo {
  max-width: 800px;
}

.placeholder {
  padding: 60px 20px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
  text-align: center;
  color: var(--text2);
}
</style>
