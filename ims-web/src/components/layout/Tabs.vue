<script setup lang="ts">
/**
 * Tabs / CatTabs 页签
 * 依据: FP-C03-01, 00-工作包 §2.1 Q4
 * Q4: Tabs 超出一屏时横向滚动，不换行
 */
import { computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

interface TabItem {
  key: string
  label: string
  count?: number
}

interface Props {
  items?: TabItem[]
  active?: string
  type?: 'line' | 'pill'
  syncQuery?: string
}

const props = withDefaults(defineProps<Props>(), {
  type: 'line',
  items: () => [],
})

const emit = defineEmits<{
  (e: 'update:active', key: string): void
  (e: 'change', key: string): void
}>()

const router = useRouter()
const route = useRoute()

// 从 URL 获取初始值
const activeKey = computed({
  get: () => {
    if (props.syncQuery && route.query[props.syncQuery]) {
      return route.query[props.syncQuery] as string
    }
    return props.active || props.items?.[0]?.key || ''
  },
  set: (val) => {
    emit('update:active', val)
    emit('change', val)
  },
})

// 同步到 URL
watch(activeKey, (val) => {
  if (props.syncQuery) {
    router.replace({
      query: {
        ...route.query,
        [props.syncQuery]: val,
      },
    })
  }
})

function handleClick(key: string) {
  activeKey.value = key
}
</script>

<template>
  <div class="tabs" :class="[`tabs--${type}`]">
    <div class="tabs-container">
      <div
        v-for="item in items"
        :key="item.key"
        class="tab-item touch-target"
        :class="{ active: activeKey === item.key }"
        @click="handleClick(item.key)"
      >
        <span class="tab-label">{{ item.label }}</span>
        <span v-if="item.count !== undefined" class="tab-count">{{ item.count }}</span>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.tabs {
  margin-bottom: 16px;

  // Q4: 超出一屏时横向滚动
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;

  &::-webkit-scrollbar {
    display: none;
  }
}

.tabs-container {
  display: flex;
  white-space: nowrap;
  gap: 4px;
}

// 下划线样式
.tabs--line {
  border-bottom: 1px solid var(--line);

  .tab-item {
    padding: 8px 14px;
    font-size: 13px;
    color: var(--text2);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    transition: all 0.2s;
    min-height: 44px;
    display: flex;
    align-items: center;
    gap: 6px;

    &:hover {
      color: var(--text);
    }

    &.active {
      color: var(--blue);
      border-bottom-color: var(--blue);
    }
  }
}

// 胶囊样式
.tabs--pill {
  .tabs-container {
    background-color: var(--bg);
    padding: 4px;
    border-radius: var(--r-s);
    display: inline-flex;
  }

  .tab-item {
    padding: 6px 12px;
    font-size: 13px;
    color: var(--text2);
    cursor: pointer;
    border-radius: var(--r-xs);
    transition: all 0.2s;
    min-height: 44px;
    display: flex;
    align-items: center;
    gap: 6px;

    &:hover {
      color: var(--text);
    }

    &.active {
      background-color: var(--card);
      color: var(--text);
      box-shadow: var(--sh);
    }
  }
}

.tab-label {
  white-space: nowrap;
}

// 计数徽标 (中性色, 不用红色)
.tab-count {
  background-color: var(--status-neutral-bg);
  color: var(--status-neutral-text);
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}
</style>
