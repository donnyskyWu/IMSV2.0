<script setup lang="ts">
/**
 * 文件演示页 (FP-P-08)
 * 依据: FP-C17-01~02, FP-C18-01~03
 * 包含: FileUpload、FilePreview、ImportDialog、ExportButton、DownloadBar
 */
import { ref } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import FileUpload from '@/components/file/FileUpload.vue'
import FilePreview from '@/components/file/FilePreview.vue'
import ImportDialog from '@/components/file/ImportDialog.vue'
import ExportButton from '@/components/file/ExportButton.vue'
import DownloadBar from '@/components/file/DownloadBar.vue'

// 上传的文件
const uploadedFiles = ref<string[]>([])

// 预览文件列表
const previewFiles = ref([
  { name: '合同文档.pdf', url: '/mock/contract.pdf', type: 'application/pdf', size: 1024000 },
  { name: '产品图片.jpg', url: 'https://picsum.photos/400/300', type: 'image/jpeg', size: 256000 },
  { name: '数据报表.xlsx', url: '/mock/report.xlsx', type: 'application/vnd.ms-excel', size: 512000 },
])

// 导入对话框
const importVisible = ref(false)

// 下载任务
const downloadTasks = ref([
  { id: '1', name: '订单数据导出.xlsx', progress: 100, status: 'completed' as const, url: '/mock/export.xlsx' },
])
const showDownloadBar = ref(false)

// 文件变化
function handleFileChange(files: unknown[]) {
  console.log('Files changed:', files)
  uploadedFiles.value = files.map((f: { name: string }) => f.name)
}

// 导入成功
function handleImportSuccess(result: unknown) {
  console.log('Import success:', result)
}

// 导出
function handleExport(option: unknown) {
  console.log('Export:', option)
  // 模拟下载任务
  downloadTasks.value = [
    { id: '1', name: '数据导出.xlsx', progress: 0, status: 'downloading' as const },
  ]
  showDownloadBar.value = true

  // 模拟进度
  let progress = 0
  const timer = setInterval(() => {
    progress += 20
    downloadTasks.value[0].progress = progress
    if (progress >= 100) {
      clearInterval(timer)
      downloadTasks.value[0].status = 'completed'
      downloadTasks.value[0].url = '/mock/export.xlsx'
    }
  }, 500)
}
</script>

<template>
  <AppLayout>
    <div class="files-demo">
      <PageHeader title="文件组件演示" sub-title="FP-P-08 / FP-C17~C18" />

      <div class="demo-section">
        <h3 class="section-title">1. 文件上传 (FileUpload)</h3>
        <FileUpload
          :max-count="3"
          :max-size="5"
          accept=".jpg,.png,.pdf,.xlsx"
          tip="支持 jpg、png、pdf、xlsx 格式，单个文件不超过 5MB"
          @change="handleFileChange"
        />
        <div v-if="uploadedFiles.length > 0" class="demo-result">
          已上传: {{ uploadedFiles.join(', ') }}
        </div>
      </div>

      <div class="demo-section">
        <h3 class="section-title">2. 文件预览 (FilePreview)</h3>
        <FilePreview :files="previewFiles" />
      </div>

      <div class="demo-section">
        <h3 class="section-title">3. 导入对话框 (ImportDialog)</h3>
        <el-button type="primary" @click="importVisible = true">打开导入对话框</el-button>
        <ImportDialog
          v-model="importVisible"
          title="导入用户数据"
          @success="handleImportSuccess"
        />
      </div>

      <div class="demo-section">
        <h3 class="section-title">4. 导出按钮 (ExportButton)</h3>
        <ExportButton @export="handleExport" />
        <span class="demo-tip">点击后会显示下载进度条</span>
      </div>

      <div class="demo-section">
        <h3 class="section-title">5. 下载进度条 (DownloadBar)</h3>
        <el-button @click="showDownloadBar = true">显示下载进度条</el-button>
        <DownloadBar
          :tasks="downloadTasks"
          :visible="showDownloadBar"
          @close="showDownloadBar = false"
        />
      </div>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.files-demo {
  max-width: 800px;
}

.demo-section {
  margin-bottom: 32px;
  padding: 24px;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);

  &:last-child {
    margin-bottom: 0;
  }
}

.section-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 500;
  color: var(--text);
}

.demo-result {
  margin-top: 16px;
  padding: 12px;
  background-color: var(--hover);
  border-radius: 4px;
  font-size: 13px;
  color: var(--text2);
}

.demo-tip {
  margin-left: 12px;
  font-size: 13px;
  color: var(--text2);
}
</style>
