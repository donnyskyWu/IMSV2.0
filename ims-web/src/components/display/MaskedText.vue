<script setup lang="ts">
/**
 * MaskedText 脱敏文本
 * 依据: FP-C19-02
 * - 显示脱敏值
 * - 有权限时可查看原始值
 */
import { ref } from 'vue'
import { View, Hide } from '@element-plus/icons-vue'

interface Props {
  value: string
  canView?: boolean
  onFetch?: () => Promise<string>
}

const props = withDefaults(defineProps<Props>(), {
  canView: false,
})

// 是否显示原始值
const revealed = ref(false)

// 原始值
const realValue = ref('')

// 加载状态
const loading = ref(false)

// 切换显示
async function toggleReveal() {
  if (!props.canView) return

  if (revealed.value) {
    revealed.value = false
    return
  }

  if (props.onFetch) {
    loading.value = true
    try {
      realValue.value = await props.onFetch()
    } finally {
      loading.value = false
    }
  }
  revealed.value = true
}

// 判断是否是脱敏值
function isMasked(val: string): boolean {
  return val.includes('*')
}
</script>

<template>
  <span class="masked-text" :class="{ 'can-view': canView }">
    <span class="text-value">
      {{ revealed && realValue ? realValue : value }}
    </span>
    <el-button
      v-if="canView && isMasked(value)"
      text
      size="small"
      :loading="loading"
      class="toggle-btn"
      @click="toggleReveal"
    >
      <el-icon v-if="!loading">
        <View v-if="!revealed" />
        <Hide v-else />
      </el-icon>
    </el-button>
  </span>
</template>

<style lang="scss" scoped>
.masked-text {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: 'SF Mono', Monaco, Consolas, monospace;
}

.text-value {
  color: var(--text);
}

.toggle-btn {
  padding: 4px;
  margin: -4px;
  color: var(--text2);

  &:hover {
    color: var(--blue);
  }
}
</style>
