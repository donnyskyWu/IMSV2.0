<script setup lang="ts">
/**
 * Pagination 分页
 * 依据: FP-C08-01, 00-工作包 §2.1 Q8, §2.2 #4
 * 桌面: 显示"共 N 条" + 每页 10/20/50 + 页码
 * 手机 (Q8): 只显示上一页、"当前页/总页数"和下一页，隐藏每页条数和跳页
 * §2.2 #4: 保留"共 N 条"；total=0 时整个分页组件不显示
 */
import { computed } from 'vue'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { useResponsive } from '@/utils/responsive'

interface Props {
  pageNo: number
  pageSize: number
  total: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:pageNo', val: number): void
  (e: 'update:pageSize', val: number): void
  (e: 'change', payload: { pageNo: number; pageSize: number }): void
}>()

const { isMobile } = useResponsive()

// 总页数
const totalPages = computed(() => Math.ceil(props.total / props.pageSize) || 1)

// 是否显示分页 (§2.2 #4: total=0 时不显示)
const showPagination = computed(() => props.total > 0)

// 每页条数选项
const pageSizes = [10, 20, 50]

// 切换页码
function handlePageChange(page: number) {
  if (page < 1 || page > totalPages.value) return
  emit('update:pageNo', page)
  emit('change', { pageNo: page, pageSize: props.pageSize })
}

// 切换每页条数
function handleSizeChange(size: number) {
  emit('update:pageSize', size)
  emit('update:pageNo', 1) // 改 pageSize 回到第 1 页
  emit('change', { pageNo: 1, pageSize: size })
}

// 上一页
function prevPage() {
  if (props.pageNo > 1) {
    handlePageChange(props.pageNo - 1)
  }
}

// 下一页
function nextPage() {
  if (props.pageNo < totalPages.value) {
    handlePageChange(props.pageNo + 1)
  }
}
</script>

<template>
  <div v-if="showPagination || !isMobile" class="pagination" :class="{ 'pagination--mobile': isMobile }">
    <!-- 总数 -->
    <span class="pagination-total">共 {{ total }} 条</span>

    <!-- 桌面端：total=0 时只留总数，不显示页码 -->
    <template v-if="!isMobile && total > 0">
      <!-- 每页条数 -->
      <el-select
        :model-value="pageSize"
        class="page-size-select"
        @change="handleSizeChange"
      >
        <el-option
          v-for="size in pageSizes"
          :key="size"
          :label="`${size} 条/页`"
          :value="size"
        />
      </el-select>

      <!-- 页码 -->
      <el-pagination
        :current-page="pageNo"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        :pager-count="5"
        @current-change="handlePageChange"
      />
    </template>

    <!-- 手机端 (Q8) -->
    <template v-else>
      <div class="mobile-pager">
        <el-button
          class="pager-btn touch-target"
          :disabled="pageNo <= 1"
          text
          @click="prevPage"
        >
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <span class="pager-info">{{ pageNo }}/{{ totalPages }}</span>
        <el-button
          class="pager-btn touch-target"
          :disabled="pageNo >= totalPages"
          text
          @click="nextPage"
        >
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  padding: 12px 0;
}

.pagination-total {
  font-size: 13px;
  color: var(--text2);
}

.page-size-select {
  width: 110px;
}

// 手机端样式
.pagination--mobile {
  justify-content: space-between;

  .pagination-total {
    font-size: 12px;
  }
}

.mobile-pager {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pager-btn {
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: var(--r-xs);

  &:not(:disabled):hover {
    background-color: var(--bg);
  }
}

.pager-info {
  font-size: 13px;
  color: var(--text);
  min-width: 50px;
  text-align: center;
}
</style>
