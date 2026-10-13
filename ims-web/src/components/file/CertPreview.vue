<script setup lang="ts">
/**
 * 证件原图全屏层。无下载，禁止右键和拖拽。版本 v1.0 · 2026-10-13
 */
defineProps<{
  open: boolean
  watermarkText: string
  certNo: string
  previewUrl: string
}>()
const emit = defineEmits<{ (e: 'close'): void }>()

function block(event: Event) {
  event.preventDefault()
}
</script>

<template>
  <div v-if="open" class="cert-preview" data-testid="cert-preview" @click.self="emit('close')">
    <p class="cert-no">{{ certNo }}</p>
    <img
      class="cert-image"
      :src="previewUrl || undefined"
      alt="证件原图"
      draggable="false"
      @contextmenu="block"
      @dragstart="block"
    >
    <p class="watermark">{{ watermarkText }}</p>
    <button type="button" class="close-btn" @click="emit('close')">关闭</button>
  </div>
</template>

<style scoped>
.cert-preview {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgb(0 0 0 / 72%);
  color: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.cert-image {
  max-width: 80vw;
  max-height: 60vh;
  user-select: none;
  -webkit-user-drag: none;
}

.watermark {
  pointer-events: none;
}
</style>
