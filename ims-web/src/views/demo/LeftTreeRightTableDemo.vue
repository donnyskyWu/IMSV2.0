<script setup lang="ts">
/**
 * 左树右表演示页 (FP-P-11)
 * 依据: UI-L02, FP-C-31, 00-工作包 §2.1 Q12
 * 桌面: 左树 280px + 右表
 * 手机: 树收进抽屉，顶部显示已选节点
 */
import { ref, computed } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import LeftTreeRightTable from '@/components/list/LeftTreeRightTable.vue'
import StatusTag from '@/components/list/StatusTag.vue'
import Pagination from '@/components/list/Pagination.vue'

// 分类树数据
const categoryTree = ref([
  {
    id: 'all',
    label: '全部商品',
    count: 256,
    children: [
      {
        id: 'electronics',
        label: '电子产品',
        count: 86,
        children: [
          { id: 'phone', label: '手机', count: 35 },
          { id: 'laptop', label: '笔记本', count: 28 },
          { id: 'tablet', label: '平板', count: 23 },
        ],
      },
      {
        id: 'clothing',
        label: '服装',
        count: 120,
        children: [
          { id: 'men', label: '男装', count: 45 },
          { id: 'women', label: '女装', count: 55 },
          { id: 'kids', label: '童装', count: 20 },
        ],
      },
      {
        id: 'home',
        label: '家居',
        count: 50,
        children: [
          { id: 'furniture', label: '家具', count: 30 },
          { id: 'decor', label: '装饰', count: 20 },
        ],
      },
    ],
  },
])

// 选中的分类
const selectedCategory = ref<string | number>('')

// 模拟商品数据
const allProducts = Array.from({ length: 100 }, (_, i) => ({
  id: String(i + 1),
  name: `商品 ${String(i + 1).padStart(3, '0')}`,
  category: ['phone', 'laptop', 'tablet', 'men', 'women', 'kids', 'furniture', 'decor'][i % 8],
  price: Math.round(Math.random() * 5000 + 100),
  stock: Math.round(Math.random() * 200),
  status: ['ON_SALE', 'OFF_SALE', 'SOLD_OUT'][i % 3],
  createTime: `2026-10-${String((i % 28) + 1).padStart(2, '0')}`,
}))

// 分页
const pageNo = ref(1)
const pageSize = ref(10)

// 过滤后的数据
const filteredProducts = computed(() => {
  if (!selectedCategory.value || selectedCategory.value === 'all') {
    return allProducts
  }
  
  // 递归获取所有子分类
  const getChildIds = (nodes: typeof categoryTree.value): string[] => {
    const ids: string[] = []
    for (const node of nodes) {
      ids.push(String(node.id))
      if (node.children) {
        ids.push(...getChildIds(node.children))
      }
    }
    return ids
  }

  // 查找选中节点
  const findNode = (nodes: typeof categoryTree.value, id: string | number): typeof categoryTree.value[0] | null => {
    for (const node of nodes) {
      if (node.id === id) return node
      if (node.children) {
        const found = findNode(node.children, id)
        if (found) return found
      }
    }
    return null
  }

  const node = findNode(categoryTree.value, selectedCategory.value)
  if (!node) return allProducts

  const categoryIds = [String(node.id)]
  if (node.children) {
    categoryIds.push(...getChildIds(node.children))
  }

  return allProducts.filter((p) => categoryIds.includes(p.category))
})

const total = computed(() => filteredProducts.value.length)

const tableData = computed(() => {
  const start = (pageNo.value - 1) * pageSize.value
  return filteredProducts.value.slice(start, start + pageSize.value)
})

// 分类切换
function handleCategoryChange() {
  pageNo.value = 1
}
</script>

<template>
  <AppLayout>
    <div class="left-tree-right-table-demo">
      <PageHeader title="左树右表演示" sub-title="FP-P-11 / UI-L02" />

      <LeftTreeRightTable
        v-model:selected-key="selectedCategory"
        :tree-data="categoryTree"
        tree-placeholder="搜索分类"
        @node-click="handleCategoryChange"
      >
        <!-- 右侧内容 -->
        <div class="table-section">
          <!-- 表格 -->
          <div class="table-wrap">
            <el-table :data="tableData" style="width: 100%">
              <el-table-column prop="name" label="商品名称" min-width="150" />
              <el-table-column prop="category" label="分类" width="100" />
              <el-table-column prop="price" label="价格" width="100" align="right">
                <template #default="{ row }">
                  ¥{{ row.price.toLocaleString() }}
                </template>
              </el-table-column>
              <el-table-column prop="stock" label="库存" width="80" align="right" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <StatusTag dict-type="product_status" :value="row.status" />
                </template>
              </el-table-column>
              <el-table-column prop="createTime" label="创建时间" width="120" />
              <el-table-column label="操作" width="120" fixed="right">
                <template #default>
                  <el-button v-perm="'ims:demo:order:update'" text type="primary" size="small">编辑</el-button>
                  <el-button v-perm="'ims:demo:order:delete'" text type="primary" size="small">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 分页 -->
          <Pagination
            v-model:page-no="pageNo"
            v-model:page-size="pageSize"
            :total="total"
          />
        </div>
      </LeftTreeRightTable>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.left-tree-right-table-demo {
  width: 100%;
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.table-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.table-wrap {
  flex: 1;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  overflow: hidden;
}
</style>
