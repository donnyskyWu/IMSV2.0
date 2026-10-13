<script setup lang="ts">
/**
 * 岗位资料库 (FP-B21-MT-01~10)
 * 左树右表布局：左侧分类树 + 右侧资料列表
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import LeftTreeRightTable from '@/components/list/LeftTreeRightTable.vue'
import Pagination from '@/components/list/Pagination.vue'
import StatusTag from '@/components/list/StatusTag.vue'
import FormDrawer from '@/components/form/FormDrawer.vue'
import DetailDrawer from '@/components/form/DetailDrawer.vue'
import EmptyState from '@/components/list/EmptyState.vue'
import { toast } from '@/utils/toast'
import { useDictStore } from '@/stores/dict'
import { useResponsive } from '@/utils/responsive'
import {
  getCateTree,
  createCate,
  updateCate,
  deleteCate,
  getMaterialList,
  getMaterialDetail,
  createMaterial,
  updateMaterial,
  offlineMaterial,
  type TrainMaterialCate,
  type TrainMaterial,
  type TrainMaterialDetail,
} from '@/api/generated/train'
import type { EmptyType } from '@/types'

interface TreeNode {
  id: string
  label: string
  positionCode?: string | null
  children?: TreeNode[]
}

const route = useRoute()
const router = useRouter()
const dictStore = useDictStore()
const { isMobile } = useResponsive()

const loading = ref(false)
const emptyMode = ref<EmptyType | ''>('')
const treeData = ref<TreeNode[]>([])
const selectedCateId = ref('all')
const pageNo = ref(1)
const pageSize = ref(10)
const total = ref(0)
const materials = ref<TrainMaterial[]>([])

const searchForm = ref({
  keyword: '',
  status: '',
  materialType: '',
})

const uploadDrawerOpen = ref(false)
const uploadForm = ref({
  title: '',
  cateId: '',
  materialType: 'DOC' as 'DOC' | 'VIDEO' | 'LINK',
  fileKey: '',
  linkUrl: '',
  positionCodes: [] as string[],
  status: 'DRAFT',
})
const isEdit = ref(false)
const editingId = ref('')

const detailDrawerOpen = ref(false)
const detailTab = ref('base')
const detailData = ref<TrainMaterialDetail | null>(null)

const cateDrawerOpen = ref(false)
const cateForm = ref({
  parentId: '',
  cateName: '',
  positionCode: '',
  sort: 0,
})
const isEditCate = ref(false)
const editingCateId = ref('')

const confirmDeleteOpen = ref(false)
const pendingDeleteMaterial = ref<TrainMaterial | null>(null)

function transformCateTree(cates: TrainMaterialCate[]): TreeNode[] {
  return cates.map((cate) => ({
    id: cate.id,
    label: cate.cateName,
    positionCode: cate.positionCode,
    children: cate.children ? transformCateTree(cate.children) : undefined,
  }))
}

async function loadCateTree() {
  try {
    const res = await getCateTree()
    const nodes = transformCateTree(res.data || [])
    treeData.value = [{ id: 'all', label: '全部', children: nodes }]
  } catch {
    treeData.value = [{ id: 'all', label: '全部' }]
  }
}

async function loadMaterials() {
  loading.value = true
  emptyMode.value = ''
  try {
    const params: Record<string, unknown> = {
      pageNo: pageNo.value,
      pageSize: pageSize.value,
      ...searchForm.value,
    }
    if (selectedCateId.value && selectedCateId.value !== 'all') {
      params.cateId = selectedCateId.value
    }
    const res = await getMaterialList(params as Parameters<typeof getMaterialList>[0])
    materials.value = res.data?.list || []
    total.value = res.data?.total || 0
    if (materials.value.length === 0 && !searchForm.value.keyword && !searchForm.value.status) {
      emptyMode.value = 'empty'
    }
  } catch {
    emptyMode.value = 'error'
  } finally {
    loading.value = false
  }
}

function handleCategoryChange(node: { id: string }) {
  selectedCateId.value = node.id
  pageNo.value = 1
  router.replace({ query: { ...route.query, cateId: node.id } })
}

function handleSearch() {
  pageNo.value = 1
  loadMaterials()
}

function handleReset() {
  searchForm.value = { keyword: '', status: '', materialType: '' }
  handleSearch()
}

function handleCreate() {
  isEdit.value = false
  editingId.value = ''
  uploadForm.value = {
    title: '',
    cateId: selectedCateId.value !== 'all' ? selectedCateId.value : '',
    materialType: 'DOC',
    fileKey: '',
    linkUrl: '',
    positionCodes: [],
    status: 'DRAFT',
  }
  uploadDrawerOpen.value = true
}

async function handleEdit(row: TrainMaterial) {
  isEdit.value = true
  editingId.value = row.id
  uploadForm.value = {
    title: row.title,
    cateId: row.cateId,
    materialType: row.materialType,
    fileKey: row.fileKey || '',
    linkUrl: row.linkUrl || '',
    positionCodes: row.positionCodes || [],
    status: row.status,
  }
  uploadDrawerOpen.value = true
}

async function handleView(row: TrainMaterial) {
  try {
    const res = await getMaterialDetail(row.id)
    detailData.value = res.data || null
    detailTab.value = 'base'
    detailDrawerOpen.value = true
  } catch {
    toast.error('加载详情失败')
  }
}

async function handleSubmitMaterial() {
  const data = {
    title: uploadForm.value.title,
    cateId: uploadForm.value.cateId,
    materialType: uploadForm.value.materialType,
    fileKey: uploadForm.value.materialType !== 'LINK' ? uploadForm.value.fileKey : undefined,
    linkUrl: uploadForm.value.materialType === 'LINK' ? uploadForm.value.linkUrl : undefined,
    positionCodes: uploadForm.value.positionCodes,
    status: uploadForm.value.status,
  }
  if (isEdit.value) {
    await updateMaterial(editingId.value, data)
    toast.success('更新成功')
  } else {
    await createMaterial(data)
    toast.success('创建成功')
  }
  uploadDrawerOpen.value = false
  loadMaterials()
}

function handleOffline(row: TrainMaterial) {
  pendingDeleteMaterial.value = row
  confirmDeleteOpen.value = true
}

async function confirmOffline() {
  if (!pendingDeleteMaterial.value) return
  try {
    await offlineMaterial(pendingDeleteMaterial.value.id)
    toast.success('已下架')
    confirmDeleteOpen.value = false
    loadMaterials()
  } catch {
    toast.error('下架失败')
  }
}

function handleCreateCate() {
  isEditCate.value = false
  editingCateId.value = ''
  cateForm.value = {
    parentId: selectedCateId.value !== 'all' ? selectedCateId.value : '',
    cateName: '',
    positionCode: '',
    sort: 0,
  }
  cateDrawerOpen.value = true
}

async function handleSubmitCate() {
  if (isEditCate.value) {
    await updateCate(editingCateId.value, { cateName: cateForm.value.cateName, sort: cateForm.value.sort })
    toast.success('更新成功')
  } else {
    await createCate({
      parentId: cateForm.value.parentId,
      cateName: cateForm.value.cateName,
      positionCode: cateForm.value.positionCode || undefined,
      sort: cateForm.value.sort,
    })
    toast.success('创建成功')
  }
  cateDrawerOpen.value = false
  loadCateTree()
}

const materialTypeOptions = [
  { label: '文档', value: 'DOC' },
  { label: '视频', value: 'VIDEO' },
  { label: '外链', value: 'LINK' },
]

const statusOptions = [
  { label: '草稿', value: 'DRAFT' },
  { label: '已发布', value: 'PUBLISHED' },
  { label: '已下架', value: 'OFFLINE' },
]

onMounted(() => {
  dictStore.applyLocal('dict_train_material_type', [
    { dictValue: 'DOC', dictLabel: '文档', colorType: 'neutral' },
    { dictValue: 'VIDEO', dictLabel: '视频', colorType: 'purple' },
    { dictValue: 'LINK', dictLabel: '外链', colorType: 'success' },
  ])
  dictStore.applyLocal('dict_train_material_status', [
    { dictValue: 'DRAFT', dictLabel: '草稿', colorType: 'neutral' },
    { dictValue: 'PUBLISHED', dictLabel: '已发布', colorType: 'success' },
    { dictValue: 'OFFLINE', dictLabel: '已下架', colorType: 'danger' },
  ])

  const cateId = route.query.cateId as string
  if (cateId) {
    selectedCateId.value = cateId
  }
  loadCateTree()
  loadMaterials()
})

watch([pageNo, pageSize], loadMaterials)
</script>

<template>
  <AppLayout>
    <div class="material-list">
      <PageHeader title="岗位资料库" sub-title="FP-B21-MT">
        <template #actions>
          <el-button v-perm="'ims:train:material:add'" type="primary" @click="handleCreate">上传资料</el-button>
          <el-button v-perm="'ims:train:cate:edit'" @click="handleCreateCate">新建分类</el-button>
        </template>
        <template #primary-action>
          <el-button v-perm="'ims:train:material:add'" type="primary" @click="handleCreate">上传</el-button>
        </template>
      </PageHeader>

      <LeftTreeRightTable
        v-model:selected-key="selectedCateId"
        :tree-data="treeData"
        tree-placeholder="搜索分类"
        @node-click="handleCategoryChange"
      >
        <div class="table-section">
          <div class="query-bar">
            <el-form :model="searchForm" inline @submit.prevent="handleSearch">
              <el-form-item label="关键词">
                <el-input v-model="searchForm.keyword" placeholder="标题" clearable style="width: 160px" @keyup.enter="handleSearch" />
              </el-form-item>
              <el-form-item label="类型">
                <el-select v-model="searchForm.materialType" placeholder="全部" clearable style="width: 100px">
                  <el-option v-for="opt in materialTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="状态">
                <el-select v-model="searchForm.status" placeholder="全部" clearable style="width: 100px">
                  <el-option v-for="opt in statusOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleSearch">查询</el-button>
                <el-button @click="handleReset">重置</el-button>
              </el-form-item>
            </el-form>
          </div>

          <div v-loading="loading" class="table-wrap">
            <el-table v-if="!emptyMode" :data="materials" style="width: 100%">
              <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
              <el-table-column prop="materialNo" label="编号" width="140">
                <template #default="{ row }">
                  <span class="mono">{{ row.materialNo }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="materialType" label="类型" width="80">
                <template #default="{ row }">
                  <StatusTag dict-type="dict_train_material_type" :value="row.materialType" />
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="90">
                <template #default="{ row }">
                  <StatusTag dict-type="dict_train_material_status" :value="row.status" />
                </template>
              </el-table-column>
              <el-table-column prop="version" label="版本" width="60" align="center">
                <template #default="{ row }">
                  v{{ row.version }}
                </template>
              </el-table-column>
              <el-table-column prop="createTime" label="创建时间" width="160" />
              <el-table-column label="操作" :width="isMobile ? 72 : 180" fixed="right">
                <template #default="{ row }">
                  <el-button v-if="!isMobile" v-perm="'ims:train:material:query'" text type="primary" size="small" @click="handleView(row)">查看</el-button>
                  <el-button v-if="!isMobile" v-perm="'ims:train:material:edit'" text type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
                  <el-dropdown trigger="click">
                    <el-button text type="primary" size="small">更多</el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item v-if="isMobile" @click="handleView(row)">查看</el-dropdown-item>
                        <el-dropdown-item v-if="isMobile" @click="handleEdit(row)">编辑</el-dropdown-item>
                        <el-dropdown-item v-perm="'ims:train:material:offline'" divided @click="handleOffline(row)">
                          <span class="danger-text">下架</span>
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </template>
              </el-table-column>
            </el-table>
            <EmptyState v-else :type="emptyMode" @retry="loadMaterials" />
          </div>

          <Pagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" />
        </div>
      </LeftTreeRightTable>

      <!-- Upload/Edit Drawer -->
      <FormDrawer
        v-model:open="uploadDrawerOpen"
        :title="isEdit ? '编辑资料' : '上传资料'"
        size="M"
        :submit="handleSubmitMaterial"
      >
        <el-form :model="uploadForm" label-width="90px">
          <el-form-item label="标题" required>
            <el-input v-model="uploadForm.title" placeholder="请输入标题（最多128字）" maxlength="128" show-word-limit />
          </el-form-item>
          <el-form-item label="分类" required>
            <el-cascader v-model="uploadForm.cateId" :options="treeData" :props="{ value: 'id', label: 'label', emitPath: false }" placeholder="请选择分类" style="width: 100%" />
          </el-form-item>
          <el-form-item label="类型" required>
            <el-radio-group v-model="uploadForm.materialType" :disabled="isEdit">
              <el-radio v-for="opt in materialTypeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="uploadForm.materialType !== 'LINK'" label="文件">
            <el-input v-model="uploadForm.fileKey" placeholder="文件Key（上传后自动填充）" disabled />
          </el-form-item>
          <el-form-item v-if="uploadForm.materialType === 'LINK'" label="链接地址" required>
            <el-input v-model="uploadForm.linkUrl" placeholder="请输入 http:// 或 https:// 开头的链接" />
          </el-form-item>
          <el-form-item label="关联岗位">
            <el-select v-model="uploadForm.positionCodes" multiple placeholder="可多选" style="width: 100%">
              <el-option label="全员通用" value="" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-radio-group v-model="uploadForm.status">
              <el-radio value="DRAFT">草稿</el-radio>
              <el-radio value="PUBLISHED">发布</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </FormDrawer>

      <!-- Detail Drawer -->
      <DetailDrawer
        v-model="detailDrawerOpen"
        :title="detailData?.title || '资料详情'"
        :tabs="[{ key: 'base', label: '基本信息' }, { key: 'versions', label: '版本历史' }]"
        :active-tab="detailTab"
        @update:active-tab="detailTab = $event"
      >
        <template v-if="detailTab === 'base'">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="编号">{{ detailData?.materialNo }}</el-descriptions-item>
            <el-descriptions-item label="类型">
              <StatusTag dict-type="dict_train_material_type" :value="detailData?.materialType || ''" />
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <StatusTag dict-type="dict_train_material_status" :value="detailData?.status || ''" />
            </el-descriptions-item>
            <el-descriptions-item label="版本">v{{ detailData?.version }}</el-descriptions-item>
            <el-descriptions-item label="页数" v-if="detailData?.materialType === 'DOC'">{{ detailData?.pageCount || '-' }}</el-descriptions-item>
            <el-descriptions-item label="时长" v-if="detailData?.materialType === 'VIDEO'">{{ detailData?.durationSeconds ? Math.floor(detailData.durationSeconds / 60) + '分钟' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="发布时间">{{ detailData?.publishedAt || '-' }}</el-descriptions-item>
            <el-descriptions-item label="上传人">{{ detailData?.uploaderUserName || '-' }}</el-descriptions-item>
          </el-descriptions>
        </template>
        <template v-if="detailTab === 'versions'">
          <el-table :data="detailData?.versions || []" style="width: 100%">
            <el-table-column prop="version" label="版本" width="80">
              <template #default="{ row }">v{{ row.version }}</template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="150" show-overflow-tooltip />
            <el-table-column prop="editorUserName" label="编辑人" width="100" />
            <el-table-column prop="createdAt" label="创建时间" width="160" />
          </el-table>
        </template>
        <template #footer>
          <el-button @click="detailDrawerOpen = false">关闭</el-button>
        </template>
      </DetailDrawer>

      <!-- Category Drawer -->
      <FormDrawer
        v-model:open="cateDrawerOpen"
        :title="isEditCate ? '编辑分类' : '新建分类'"
        size="S"
        :submit="handleSubmitCate"
      >
        <el-form :model="cateForm" label-width="80px">
          <el-form-item label="父分类" v-if="!isEditCate">
            <el-cascader v-model="cateForm.parentId" :options="treeData" :props="{ value: 'id', label: 'label', emitPath: false, checkStrictly: true }" placeholder="根节点" style="width: 100%" />
          </el-form-item>
          <el-form-item label="分类名称" required>
            <el-input v-model="cateForm.cateName" placeholder="请输入分类名称" maxlength="64" />
          </el-form-item>
          <el-form-item label="关联岗位" v-if="!cateForm.parentId">
            <el-select v-model="cateForm.positionCode" placeholder="可选" clearable style="width: 100%">
              <el-option label="主播组" value="B21_ANCHOR" />
              <el-option label="直播运营" value="B21_OPERATOR" />
            </el-select>
          </el-form-item>
          <el-form-item label="排序">
            <el-input-number v-model="cateForm.sort" :min="0" :max="999" />
          </el-form-item>
        </el-form>
      </FormDrawer>

      <!-- Confirm Offline Dialog -->
      <el-dialog v-model="confirmDeleteOpen" title="确认下架" width="420px" :close-on-click-modal="false">
        <p>确定下架资料「{{ pendingDeleteMaterial?.title }}」？</p>
        <p class="hint-text">下架后学员将无法查看此资料</p>
        <template #footer>
          <el-button @click="confirmDeleteOpen = false">取消</el-button>
          <el-button type="danger" @click="confirmOffline">确定下架</el-button>
        </template>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.material-list {
  width: 100%;
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.table-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.query-bar {
  padding: 12px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);

  :deep(.el-form-item) {
    margin-bottom: 0;
    margin-right: 12px;
  }
}

.table-wrap {
  flex: 1;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  overflow: hidden;
  min-height: 200px;
}

.mono {
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  font-size: 12px;
}

.danger-text {
  color: var(--red);
}

.hint-text {
  color: var(--text2);
  font-size: 13px;
  margin-top: 8px;
}
</style>
