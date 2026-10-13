<script setup lang="ts">
/**
 * 会议纪要列表页 (B18-M18 MN-01)
 * 依据: 01-功能点清单.md, 会议-实现理解.md §3.1
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import StatusTag from '@/components/list/StatusTag.vue'
import Pagination from '@/components/list/Pagination.vue'
import EmptyState from '@/components/list/EmptyState.vue'
import FormDrawer from '@/components/form/FormDrawer.vue'
import DetailDrawer from '@/components/form/DetailDrawer.vue'
import { toast } from '@/utils/toast'
import { confirm } from '@/utils/confirm'
import { useDictStore } from '@/stores/dict'
import { useAuthStore } from '@/stores/auth'
import { useResponsive } from '@/utils/responsive'
import { fmtDateTime } from '@/utils/format'
import type { EmptyType } from '@/types'

interface Attendees {
  internal: number[]
  external: string[]
}

interface ActionItem {
  id: string
  description: string
  assignee_user_id: string
  assignee_name: string
  due_date: string
  status: string
  close_remark: string | null
  evidence_url: string | null
  closed_at: string | null
  overdue_days: number | null
}

interface Decision {
  id: string
  seq: number
  content: string
}

interface Appendix {
  id: string
  content: string
  creator_name: string
  create_time: string
}

interface MeetingMinutes {
  id: string
  code: string
  title: string
  meeting_date: string
  meeting_room: string | null
  dept_id: string
  dept_name: string | null
  recorder_user_id: string
  recorder_name: string | null
  attendees: Attendees
  attendee_names: string[]
  summary: string | null
  status: string
  archived_at: string | null
  archived_by: string | null
  archived_by_name: string | null
  create_time: string
  update_time: string
  version: number
  action_item_count: number
  action_item_closed_count: number
  decisions: Decision[]
  action_items: ActionItem[]
  appendices: Appendix[]
}

const router = useRouter()
const dictStore = useDictStore()
const authStore = useAuthStore()
const { isMobile } = useResponsive()

const loading = ref(false)
const list = ref<MeetingMinutes[]>([])
const total = ref(0)
const pageNo = ref(1)
const pageSize = ref(10)
const emptyMode = ref<EmptyType | ''>('')

const searchForm = ref({
  title: '',
  status: '',
  meeting_date_start: '',
  meeting_date_end: '',
})

const drawerVisible = ref(false)
const drawerTitle = ref('登记会议')
const editingId = ref<string | null>(null)
const formModel = ref({
  title: '',
  meeting_date: '',
  meeting_room: '',
  recorder_user_id: '',
  attendees_internal: [] as number[],
  attendees_external: [] as string[],
  summary: '',
  decisions: [] as { content: string }[],
  action_items: [] as { description: string; assignee_user_id: number; due_date: string }[],
  client_token: '',
  base_version: 1,
})

const detailOpen = ref(false)
const detailTab = ref('base')
const detailRow = ref<MeetingMinutes | null>(null)

const appendixVisible = ref(false)
const appendixContent = ref('')
const appendixMinutesId = ref<string | null>(null)

const closeActionVisible = ref(false)
const closeActionForm = ref({
  close_remark: '',
  evidence_url: '',
})
const closingActionItemId = ref<string | null>(null)

const canAdd = computed(() => authStore.hasPerm('ims:meet:minutes:add'))
const canEdit = computed(() => authStore.hasPerm('ims:meet:minutes:edit'))
const canArchive = computed(() => authStore.hasPerm('ims:meet:minutes:archive'))
const canDelete = computed(() => authStore.hasPerm('ims:meet:minutes:delete'))
const canAppendix = computed(() => authStore.hasPerm('ims:meet:minutes:appendix'))
const canSupervise = computed(() => authStore.hasPerm('ims:meet:minutes:supervise'))

const statusOptions = computed(() => dictStore.getOptions('meet_minutes_status'))

async function fetchList() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      page_no: String(pageNo.value),
      page_size: String(pageSize.value),
    })
    if (searchForm.value.title) params.append('title', searchForm.value.title)
    if (searchForm.value.status) params.append('status', searchForm.value.status)
    if (searchForm.value.meeting_date_start) params.append('meeting_date_start', searchForm.value.meeting_date_start)
    if (searchForm.value.meeting_date_end) params.append('meeting_date_end', searchForm.value.meeting_date_end)

    const response = await fetch(`/admin-api/ims/meet/minutes/list?${params}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('ims_access_token')}` },
    })
    const result = await response.json()
    if (result.code === 0) {
      list.value = result.data.list
      total.value = result.data.total
      emptyMode.value = total.value === 0 ? 'no-data' : ''
    } else {
      toast.error(result.msg || '加载失败')
      emptyMode.value = 'error'
    }
  } catch {
    toast.error('网络异常，请检查网络后重试')
    emptyMode.value = 'error'
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pageNo.value = 1
  fetchList()
}

function handleReset() {
  searchForm.value = { title: '', status: '', meeting_date_start: '', meeting_date_end: '' }
  pageNo.value = 1
  fetchList()
}

function generateToken() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function handleAdd() {
  editingId.value = null
  drawerTitle.value = '登记会议'
  formModel.value = {
    title: '',
    meeting_date: new Date().toISOString().slice(0, 16),
    meeting_room: '',
    recorder_user_id: '',
    attendees_internal: [],
    attendees_external: [],
    summary: '',
    decisions: [],
    action_items: [],
    client_token: generateToken(),
    base_version: 1,
  }
  drawerVisible.value = true
}

async function handleEdit(row: MeetingMinutes) {
  if (row.status === 'ARCHIVED') {
    toast.warning('已归档纪要不可修改')
    return
  }

  if (row.recorder_user_id !== authStore.user?.id && !canEdit.value) {
    toast.error('暂无权限')
    return
  }

  editingId.value = row.id
  drawerTitle.value = '编辑纪要'
  formModel.value = {
    title: row.title,
    meeting_date: row.meeting_date.slice(0, 16),
    meeting_room: row.meeting_room || '',
    recorder_user_id: row.recorder_user_id,
    attendees_internal: row.attendees.internal,
    attendees_external: row.attendees.external,
    summary: row.summary || '',
    decisions: row.decisions.map(d => ({ content: d.content })),
    action_items: row.action_items.map(a => ({
      description: a.description,
      assignee_user_id: Number(a.assignee_user_id),
      due_date: a.due_date,
    })),
    client_token: generateToken(),
    base_version: row.version,
  }
  drawerVisible.value = true
}

async function handleSave() {
  if (!formModel.value.title.trim()) {
    toast.error('请输入会议主题')
    return
  }
  if (formModel.value.title.length > 128) {
    toast.error('会议主题不能超过 128 字')
    return
  }
  if (formModel.value.attendees_internal.length === 0 && formModel.value.attendees_external.length === 0) {
    toast.error('请选择参会人')
    return
  }

  const body = {
    title: formModel.value.title.trim(),
    meeting_date: formModel.value.meeting_date,
    meeting_room: formModel.value.meeting_room || null,
    recorder_user_id: formModel.value.recorder_user_id ? Number(formModel.value.recorder_user_id) : null,
    attendees: {
      internal: formModel.value.attendees_internal,
      external: formModel.value.attendees_external,
    },
    summary: formModel.value.summary || null,
    decisions: formModel.value.decisions.filter(d => d.content.trim()),
    action_items: formModel.value.action_items.filter(a => a.description.trim()),
    client_token: formModel.value.client_token,
    base_version: formModel.value.base_version,
  }

  try {
    const url = editingId.value
      ? `/admin-api/ims/meet/minutes/${editingId.value}`
      : '/admin-api/ims/meet/minutes'
    const method = editingId.value ? 'PUT' : 'POST'

    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('ims_access_token')}`,
      },
      body: JSON.stringify(body),
    })
    const result = await response.json()
    if (result.code === 0) {
      toast.success('保存成功')
      if (result.data.warnings?.includes(1116)) {
        toast.warning('会后超过 24 小时录入纪要')
      }
      drawerVisible.value = false
      fetchList()
    } else {
      toast.error(result.msg || '保存失败')
    }
  } catch {
    toast.error('网络异常，请检查网络后重试')
  }
}

async function handleArchive(row: MeetingMinutes) {
  if (row.status === 'REGISTERED') {
    toast.error('请先录入纪要')
    return
  }
  if (row.status === 'ARCHIVED') {
    toast.warning('已归档纪要不可重复归档')
    return
  }

  if (row.recorder_user_id !== authStore.user?.id && !canArchive.value) {
    toast.error('暂无权限')
    return
  }

  const confirmed = await confirm({
    title: '归档确认',
    message: '归档后不可修改，行动项继续跟踪。确定归档吗？',
    type: 'warning',
  })
  if (!confirmed) return

  try {
    const response = await fetch(`/admin-api/ims/meet/minutes/${row.id}/archive`, {
      method: 'PUT',
      headers: { Authorization: `Bearer ${localStorage.getItem('ims_access_token')}` },
    })
    const result = await response.json()
    if (result.code === 0) {
      toast.success('归档成功')
      if (result.data.warnings?.includes(1116)) {
        toast.warning('会后超过 48 小时归档')
      }
      fetchList()
    } else {
      toast.error(result.msg || '归档失败')
    }
  } catch {
    toast.error('网络异常，请检查网络后重试')
  }
}

async function handleDelete(row: MeetingMinutes) {
  if (row.status === 'ARCHIVED') {
    toast.error('已归档纪要不可删除')
    return
  }

  const confirmed = await confirm({
    title: '删除确认',
    message: `确定删除会议纪要「${row.title}」吗？`,
    type: 'danger',
  })
  if (!confirmed) return

  try {
    const response = await fetch(`/admin-api/ims/meet/minutes/${row.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${localStorage.getItem('ims_access_token')}` },
    })
    const result = await response.json()
    if (result.code === 0) {
      toast.success('删除成功')
      fetchList()
    } else {
      toast.error(result.msg || '删除失败')
    }
  } catch {
    toast.error('网络异常，请检查网络后重试')
  }
}

function handleView(row: MeetingMinutes) {
  detailRow.value = row
  detailTab.value = 'base'
  detailOpen.value = true
}

function openAppendix(row: MeetingMinutes) {
  if (row.status !== 'ARCHIVED') {
    toast.warning('未归档纪要请直接编辑')
    return
  }
  appendixMinutesId.value = row.id
  appendixContent.value = ''
  appendixVisible.value = true
}

async function handleAppendixSave() {
  if (!appendixContent.value.trim()) {
    toast.error('请输入附录内容')
    return
  }

  try {
    const response = await fetch(`/admin-api/ims/meet/minutes/${appendixMinutesId.value}/appendix`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('ims_access_token')}`,
      },
      body: JSON.stringify({ content: appendixContent.value.trim() }),
    })
    const result = await response.json()
    if (result.code === 0) {
      toast.success('附录添加成功')
      appendixVisible.value = false
      fetchList()
    } else {
      toast.error(result.msg || '添加失败')
    }
  } catch {
    toast.error('网络异常，请检查网络后重试')
  }
}

function openCloseAction(item: ActionItem) {
  if (item.status === 'CLOSED') {
    toast.warning('行动项已闭环')
    return
  }
  if (item.assignee_user_id !== authStore.user?.id) {
    toast.error('非行动项责任人，无权回填')
    return
  }
  closingActionItemId.value = item.id
  closeActionForm.value = { close_remark: '', evidence_url: '' }
  closeActionVisible.value = true
}

async function handleCloseAction() {
  if (!closeActionForm.value.close_remark.trim()) {
    toast.error('请输入闭环说明')
    return
  }
  if (closeActionForm.value.evidence_url) {
    try {
      const url = new URL(closeActionForm.value.evidence_url)
      if (!['http:', 'https:'].includes(url.protocol)) {
        toast.error('证据链接仅支持 http/https')
        return
      }
    } catch {
      toast.error('证据链接格式不正确')
      return
    }
  }

  try {
    const response = await fetch(`/admin-api/ims/meet/minutes/action-item/${closingActionItemId.value}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('ims_access_token')}`,
      },
      body: JSON.stringify(closeActionForm.value),
    })
    const result = await response.json()
    if (result.code === 0) {
      toast.success('行动项已闭环')
      closeActionVisible.value = false
      fetchList()
    } else {
      toast.error(result.msg || '操作失败')
    }
  } catch {
    toast.error('网络异常，请检查网络后重试')
  }
}

function getStatusType(status: string): string {
  const map: Record<string, string> = {
    REGISTERED: 'info',
    MINUTES_RECORDED: 'warning',
    ARCHIVED: 'success',
  }
  return map[status] || 'info'
}

function isRecorder(row: MeetingMinutes): boolean {
  return row.recorder_user_id === authStore.user?.id
}

function canEditRow(row: MeetingMinutes): boolean {
  return row.status !== 'ARCHIVED' && (isRecorder(row) || canEdit.value)
}

function canArchiveRow(row: MeetingMinutes): boolean {
  return row.status === 'MINUTES_RECORDED' && (isRecorder(row) || canArchive.value)
}

function canAppendixRow(row: MeetingMinutes): boolean {
  return row.status === 'ARCHIVED' && (isRecorder(row) || canAppendix.value)
}

onMounted(() => {
  fetchList()
})
</script>

<template>
  <AppLayout>
    <div class="minutes-list">
      <PageHeader title="会议纪要" />

      <div class="search-bar">
        <el-form :model="searchForm" inline>
          <el-form-item label="主题">
            <el-input v-model="searchForm.title" placeholder="请输入会议主题" clearable />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="searchForm.status" placeholder="全部" clearable>
              <el-option
                v-for="opt in statusOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
        <div class="toolbar">
          <el-button v-if="canAdd" type="primary" @click="handleAdd">新建</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column prop="code" label="编号" width="150" />
        <el-table-column prop="title" label="会议主题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="meeting_date" label="会议时间" width="160">
          <template #default="{ row }">{{ fmtDateTime(row.meeting_date) }}</template>
        </el-table-column>
        <el-table-column prop="recorder_name" label="记录人" width="100" />
        <el-table-column prop="attendee_names" label="参会人" min-width="150">
          <template #default="{ row }">
            {{ row.attendee_names.slice(0, 3).join('、') }}
            <span v-if="row.attendee_names.length > 3">等{{ row.attendee_names.length }}人</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <StatusTag :type="getStatusType(row.status)" :label="dictStore.getLabel('meet_minutes_status', row.status)" />
          </template>
        </el-table-column>
        <el-table-column label="行动项" width="120">
          <template #default="{ row }">
            {{ row.action_item_count }} 项（{{ row.action_item_closed_count }} 已闭环）
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">查看</el-button>
            <el-button v-if="canEditRow(row)" link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button v-if="canArchiveRow(row)" link type="warning" @click="handleArchive(row)">归档</el-button>
            <el-dropdown v-if="canDelete || canAppendixRow(row)" trigger="click">
              <el-button link type="primary">更多</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-if="canAppendixRow(row)" @click="openAppendix(row)">附录说明</el-dropdown-item>
                  <el-dropdown-item v-if="canDelete && row.status !== 'ARCHIVED'" @click="handleDelete(row)">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <EmptyState v-if="emptyMode" :type="emptyMode" @retry="fetchList" />

      <Pagination
        v-if="total > 0"
        v-model:page-no="pageNo"
        v-model:page-size="pageSize"
        :total="total"
        @change="fetchList"
      />

      <FormDrawer
        v-model="drawerVisible"
        :title="drawerTitle"
        @save="handleSave"
      >
        <el-form :model="formModel" label-width="100px">
          <el-form-item label="会议主题" required>
            <el-input v-model="formModel.title" placeholder="请输入会议主题" maxlength="128" show-word-limit />
          </el-form-item>
          <el-form-item label="会议时间" required>
            <el-date-picker
              v-model="formModel.meeting_date"
              type="datetime"
              placeholder="选择时间"
              format="YYYY-MM-DD HH:mm"
              value-format="YYYY-MM-DDTHH:mm:ss"
            />
          </el-form-item>
          <el-form-item label="会议室">
            <el-input v-model="formModel.meeting_room" placeholder="请输入会议室" />
          </el-form-item>
          <el-form-item label="纪要正文">
            <el-input v-model="formModel.summary" type="textarea" :rows="6" placeholder="请输入纪要正文" />
          </el-form-item>
        </el-form>
      </FormDrawer>

      <DetailDrawer v-model="detailOpen" title="会议纪要详情">
        <template v-if="detailRow">
          <el-tabs v-model="detailTab">
            <el-tab-pane label="基本信息" name="base">
              <el-descriptions :column="isMobile ? 1 : 2" border>
                <el-descriptions-item label="编号">{{ detailRow.code }}</el-descriptions-item>
                <el-descriptions-item label="主题">{{ detailRow.title }}</el-descriptions-item>
                <el-descriptions-item label="会议时间">{{ fmtDateTime(detailRow.meeting_date) }}</el-descriptions-item>
                <el-descriptions-item label="会议室">{{ detailRow.meeting_room || '-' }}</el-descriptions-item>
                <el-descriptions-item label="记录人">{{ detailRow.recorder_name }}</el-descriptions-item>
                <el-descriptions-item label="状态">
                  <StatusTag :type="getStatusType(detailRow.status)" :label="dictStore.getLabel('meet_minutes_status', detailRow.status)" />
                </el-descriptions-item>
                <el-descriptions-item label="参会人" :span="2">{{ detailRow.attendee_names.join('、') }}</el-descriptions-item>
              </el-descriptions>
              <div v-if="detailRow.summary" class="summary-section">
                <h4>纪要正文</h4>
                <div v-html="detailRow.summary"></div>
              </div>
            </el-tab-pane>
            <el-tab-pane label="决议事项" name="decisions">
              <el-table :data="detailRow.decisions" stripe>
                <el-table-column prop="seq" label="序号" width="80" />
                <el-table-column prop="content" label="内容" />
              </el-table>
            </el-tab-pane>
            <el-tab-pane label="行动项" name="actions">
              <el-table :data="detailRow.action_items" stripe>
                <el-table-column prop="description" label="描述" min-width="200" />
                <el-table-column prop="assignee_name" label="责任人" width="100" />
                <el-table-column prop="due_date" label="截止日期" width="120" />
                <el-table-column prop="status" label="状态" width="100">
                  <template #default="{ row }">
                    <StatusTag
                      :type="row.status === 'CLOSED' ? 'success' : row.status === 'OVERDUE' ? 'danger' : 'info'"
                      :label="dictStore.getLabel('meet_action_status', row.status)"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="100">
                  <template #default="{ row }">
                    <el-button v-if="row.status !== 'CLOSED'" link type="primary" @click="openCloseAction(row)">回填</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
            <el-tab-pane v-if="detailRow.status === 'ARCHIVED'" label="附录" name="appendix">
              <el-table :data="detailRow.appendices" stripe>
                <el-table-column prop="content" label="内容" />
                <el-table-column prop="creator_name" label="添加人" width="100" />
                <el-table-column prop="create_time" label="添加时间" width="160">
                  <template #default="{ row }">{{ fmtDateTime(row.create_time) }}</template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </template>
      </DetailDrawer>

      <el-dialog v-model="appendixVisible" title="添加附录说明" width="500px">
        <el-input v-model="appendixContent" type="textarea" :rows="4" placeholder="请输入附录内容" />
        <template #footer>
          <el-button @click="appendixVisible = false">取消</el-button>
          <el-button type="primary" @click="handleAppendixSave">确定</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="closeActionVisible" title="行动项回填" width="500px">
        <el-form :model="closeActionForm" label-width="100px">
          <el-form-item label="闭环说明" required>
            <el-input v-model="closeActionForm.close_remark" type="textarea" :rows="3" placeholder="请输入闭环说明" />
          </el-form-item>
          <el-form-item label="证据链接">
            <el-input v-model="closeActionForm.evidence_url" placeholder="请输入证据链接（仅支持 http/https）" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="closeActionVisible = false">取消</el-button>
          <el-button type="primary" @click="handleCloseAction">确定</el-button>
        </template>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<style scoped>
.minutes-list {
  padding: var(--space-m);
}

.search-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-m);
  flex-wrap: wrap;
  gap: var(--space-s);
}

.toolbar {
  display: flex;
  gap: var(--space-s);
}

.summary-section {
  margin-top: var(--space-m);
}

.summary-section h4 {
  margin-bottom: var(--space-s);
  color: var(--color-text-secondary);
}
</style>
