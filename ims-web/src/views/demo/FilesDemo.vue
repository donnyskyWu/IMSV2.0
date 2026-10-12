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
import { toast } from '@/utils/toast'
import { useDownloadStore } from '@/stores/download'
import { checkFileFormat } from '@/api/file'

// 上传的文件
const uploadedFiles = ref<string[]>([])

// 预览文件列表
const previewFiles = ref([
  { name: '合同文档.pdf', url: '/mock/contract.pdf', type: 'application/pdf', size: 1024000 },
  { name: '产品图片.jpg', url: 'https://picsum.photos/400/300', type: 'image/jpeg', size: 256000 },
  { name: '数据报表.xlsx', url: '/mock/report.xlsx', type: 'application/vnd.ms-excel', size: 512000 },
  { name: '跨租户合同.pdf', url: '/mock/other-tenant.pdf', type: 'application/pdf', size: 1024, unavailable: true },
])

// 导入对话框
const importVisible = ref(false)

// 下载任务
const downloadStore = useDownloadStore()
const importedRows = ref(0)

// 文件变化
function handleFileChange(files: unknown[]) {
  console.log('Files changed:', files)
  uploadedFiles.value = files.map((f: { name: string }) => f.name)
}

// 导入成功
function handleImportSuccess(result: { failed?: number; success?: number }) {
  if (result && !result.failed && result.success) {
    importedRows.value += result.success
  }
}

function handleExport() {
  toast.success('已开始导出')
  downloadStore.start('订单数据导出.xlsx')
}

function handleExportFail() {
  downloadStore.fail('导出服务暂不可用')
}

async function checkFakeFormat() {
  try {
    await checkFileFormat()
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '文件格式不正确')
  }
}
</script>

<template>
  <AppLayout>
    <div class="files-demo">
      <PageHeader title="文件组件演示" sub-title="FP-P-08 / FP-C17~C18" />

      <div class="demo-section">
        <h3 class="section-title">1. 文件上传 (FileUpload)</h3>
        <FileUpload
          class="limit-100"
          :max-count="3"
          :max-size="100"
          accept=".pdf,.jpg,.png,.xlsx"
          tip="单个文件不超过 100MB"
          @change="handleFileChange"
        />
        <el-button class="fake-format" @click="checkFakeFormat">校验伪造格式</el-button>
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
        <h3 class="section-title">4. 导出</h3>
        <el-button @click="handleExport">导出</el-button>
        <el-button @click="handleExportFail">导出失败</el-button>
        <p class="imported-count">列表 {{ importedRows }} 条</p>
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
