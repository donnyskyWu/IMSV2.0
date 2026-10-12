<script setup lang="ts">
/**
 * Chip / FilterChip 筛选标签
 * 依据: FP-C05-05, Q10 手机筛选条件展示
 * 移动端下用于显示已激活的筛选条件
 */
interface Props {
  label: string
  value?: string
  closable?: boolean
}

withDefaults(defineProps<Props>(), {
  closable: true,
})

const emit = defineEmits<{
  (e: 'close'): void
}>()
</script>

<template>
  <div class="chip" :class="{ 'chip--closable': closable }">
    <span class="chip__label">{{ label }}</span>
    <span v-if="value" class="chip__value">: {{ value }}</span>
    <el-icon
      v-if="closable"
      class="chip__close"
      @click.stop="emit('close')"
    >
      <svg viewBox="0 0 24 24" width="14" height="14">
        <path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
      </svg>
    </el-icon>
  </div>
</template>

<style lang="scss" scoped>
.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 10px;
  font-size: 12px;
  color: var(--text);
  background-color: var(--hover);
  border-radius: 14px;
  user-select: none;
  white-space: nowrap;

  &--closable {
    padding-right: 6px;
  }
}

.chip__label {
  color: var(--text2);
}

.chip__value {
  color: var(--text);
}

.chip__close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: var(--line);
  }
}
</style>
