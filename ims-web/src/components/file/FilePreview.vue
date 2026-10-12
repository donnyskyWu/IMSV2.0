<script setup lang="ts">
/**
 * FilePreview 文件预览
 * 依据: FP-C17-02
 * - 图片: 灯箱预览
 * - PDF/Office: iframe 或提示下载
 * - 其他: 下载链接
 */
import { ref, computed } from 'vue'
import { Document, Picture, VideoPlay, Headset, Download } from '@element-plus/icons-vue'
import { useResponsive } from '@/utils/responsive'

interface FileItem {
  name: string
  url: string
  type?: string
  size?: number
}

interface Props {
  files: FileItem[]
  showName?: boolean
  showSize?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showName: true,
  showSize: true,
})

const { isMobile } = useResponsive()

// 预览弹窗
const previewVisible = ref(false)
const previewUrl = ref('')
const previewType = ref('')

// 获取文件图标
function getFileIcon(file: FileItem) {
  const ext = file.name.split('.').pop()?.toLowerCase() || ''
  const type = file.type?.toLowerCase() || ''

  if (type.startsWith('image/') || ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext)) {
    return Picture
  }
  if (type.startsWith('video/') || ['mp4', 'webm', 'avi', 'mov'].includes(ext)) {
    return VideoPlay
  }
  if (type.startsWith('audio/') || ['mp3', 'wav', 'ogg'].includes(ext)) {
    return Headset
  }
  return Document
}

// 判断文件类型
function getMediaType(file: FileItem): 'image' | 'video' | 'pdf' | 'other' {
  const ext = file.name.split('.').pop()?.toLowerCase() || ''
  const type = file.type?.toLowerCase() || ''

  if (type.startsWith('image/') || ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext)) {
    return 'image'
  }
  if (type.startsWith('video/') || ['mp4', 'webm'].includes(ext)) {
    return 'video'
  }
  if (type === 'application/pdf' || ext === 'pdf') {
    return 'pdf'
  }
  return 'other'
}

// 格式化文件大小
function formatSize(bytes?: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

// 预览文件
function handlePreview(file: FileItem) {
  const mediaType = getMediaType(file)
  if (mediaType === 'other') {
    // 直接下载
    handleDownload(file)
    return
  }

  previewUrl.value = file.url
  previewType.value = mediaType
  previewVisible.value = true
}

// 下载文件
function handleDownload(file: FileItem) {
  const link = document.createElement('a')
  link.href = file.url
  link.download = file.name
  link.click()
}
</script>

<template>
  <div class="file-preview" :class="{ 'file-preview--mobile': isMobile }">
    <div
      v-for="(file, index) in files"
      :key="index"
      class="file-item"
      @click="handlePreview(file)"
    >
      <!-- 图片缩略图 -->
      <div
        v-if="getMediaType(file) === 'image'"
        class="file-thumb"
      >
        <img :src="file.url" :alt="file.name" />
      </div>

      <!-- 其他文件图标 -->
      <div v-else class="file-icon">
        <el-icon :size="24">
          <component :is="getFileIcon(file)" />
        </el-icon>
      </div>

      <!-- 文件信息 -->
      <div v-if="showName" class="file-info">
        <span class="file-name">{{ file.name }}</span>
        <span v-if="showSize && file.size" class="file-size">
          {{ formatSize(file.size) }}
        </span>
      </div>

      <!-- 下载按钮 -->
      <el-button
        text
        size="small"
        class="download-btn"
        @click.stop="handleDownload(file)"
      >
        <el-icon><Download /></el-icon>
      </el-button>
    </div>

    <!-- 预览弹窗 -->
    <el-dialog
      v-model="previewVisible"
      :width="isMobile ? '100%' : '80%'"
      :fullscreen="isMobile"
      :show-close="true"
      append-to-body
    >
      <!-- 图片 -->
      <img
        v-if="previewType === 'image'"
        :src="previewUrl"
        class="preview-image"
      />

      <!-- 视频 -->
      <video
        v-else-if="previewType === 'video'"
        :src="previewUrl"
        controls
        class="preview-video"
      />

      <!-- PDF -->
      <iframe
        v-else-if="previewType === 'pdf'"
        :src="previewUrl"
        class="preview-pdf"
      />
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.file-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background-color: var(--hover);
  border-radius: var(--r-s);
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: var(--line);
  }
}

.file-thumb {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  overflow: hidden;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.file-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background-color: var(--card);
  border-radius: 4px;
  color: var(--text2);
}

.file-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.file-size {
  font-size: 12px;
  color: var(--text2);
}

.download-btn {
  margin-left: auto;
}

// 预览内容
.preview-image {
  max-width: 100%;
  max-height: 80vh;
  display: block;
  margin: 0 auto;
}

.preview-video {
  width: 100%;
  max-height: 80vh;
}

.preview-pdf {
  width: 100%;
  height: 80vh;
  border: none;
}

// 移动端
.file-preview--mobile {
  .file-item {
    width: 100%;
  }

  .file-name {
    max-width: 150px;
  }
}
</style>
