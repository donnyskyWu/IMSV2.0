<script setup lang="ts">
/**
 * 会议纪要列表页 (B18-M18 MN-01)
 * 依据: 01-功能点清单.md, 会议-实现理解.md §3.1
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import StatusTag from '@/components/list/StatusTag.vue'
import Pagination from '@/components/list/Pagination.vue'
import EmptyState from '@/components/list/EmptyState.vue'
import FormDrawer from '@/components/form/FormDrawer.vue'
import DetailDrawer from '@/components/form/DetailDrawer.vue'
import UserSelect from '@/components/selector/UserSelect.vue'
import DateRangePicker from '@/components/selector/DateRangePicker.vue'
import DictSelect from '@/components/selector/DictSelect.vue'
import { toast } from '@/utils/toast'
import { confirm } from '@/utils/confirm'
import { useAuthStore } from '@/stores/auth'
import { useResponsive } from '@/utils/responsive'
import { fmtDateTime } from '@/utils/format'
import {
  meetApi,
  type MeetingMinutes,
  type MeetingMinutesListItem,
  type ActionItem,
  type ArchiveRateData,
} from '@/api/meet'
import type { EmptyType } from '@/types'

const router = useRouter()
const authStore = useAuthStore()
const { isMobile } = useResponsive()

const loading = ref(false)
const list = ref<MeetingMinutesListItem[]>([])
const total = ref(0)
const pageNo = ref(1)
const pageSize = ref(10)
const emptyMode = ref<EmptyType | ''>('')
const detailData = ref<MeetingMinutes | null>(null)

function last30Days(): [string, string] {
  return [dayjs().subtract(29, 'day').format('YYYY-MM-DD'), dayjs().format('YYYY-MM-DD')]
}

const dateRange = ref<[string, string] | null>(last30Days())
const searchForm = ref({
  title: '',
  status: '',
  meeting_date_start: '',
  meeting_date_end: '',
})
const archiveRate = ref<ArchiveRateData | null>(null)
const unarchivedOpen = ref(false)
const externalName = ref('')

const drawerVisible = ref(false)
const drawerTitle = ref('登记会议')
const editingId = ref<string | null>(null)
const formModel = ref({
  title: '',
  meeting_date: '',
  meeting_room: '',
  recorder_user_id: undefined as number | undefined,
  attendees_internal: [] as number[],
  attendees_external: [] as string[],
  summary: '',
  decisions: [] as { content: string }[],
  action_items: [] as { description: string; assignee_user_id: number; due_date: string }[],
  client_token: '',
  base_version: 1,
})

const detailOpen = ref(false)
const detailTab = ref('summary')

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

function syncDateRange() {
  if (dateRange.value) {
    searchForm.value.meeting_date_start = `${dateRange.value[0]}T00:00:00`
    searchForm.value.meeting_date_end = `${dateRange.value[1]}T23:59:59`
  } else {
    searchForm.value.meeting_date_start = ''
    searchForm.value.meeting_date_end = ''
  }
}

async function fetchMetrics() {
  if (!canSupervise.value) {
    archiveRate.value = null
    return
  }
  try {
    const result = await meetApi.getArchiveRate(
      dateRange.value
        ? { date_range_start: dateRange.value[0], date_range_end: dateRange.value[1] }
        : undefined,
    )
    if (result.code === 0 && result.data) {
      archiveRate.value = result.data
    }
  } catch {
    archiveRate.value = null
  }
}

async function fetchList() {
  syncDateRange()
  loading.value = true
  try {
    const result = await meetApi.list({
      page_no: pageNo.value,
      page_size: pageSize.value,
      title: searchForm.value.title || undefined,
      status: searchForm.value.status || undefined,
      meeting_date_start: searchForm.value.meeting_date_start || undefined,
      meeting_date_end: searchForm.value.meeting_date_end || undefined,
    })
    if (result.code === 0 && result.data) {
      list.value = result.data.list
      total.value = result.data.total
      emptyMode.value = total.value === 0 ? 'no-data' : ''
    } else {
      emptyMode.value = 'error'
    }
  } catch {
    emptyMode.value = 'error'
  } finally {
    loading.value = false
  }
  await fetchMetrics()
}

function handleSearch() {
  pageNo.value = 1
  fetchList()
}

function handleReset() {
  dateRange.value = last30Days()
  searchForm.value = { title: '', status: '', meeting_date_start: '', meeting_date_end: '' }
  pageNo.value = 1
  fetchList()
}

function currentUserId(): number | undefined {
  const id = authStore.user?.id
  if (!id) return undefined
  const parsed = Number(id)
  return Number.isFinite(parsed) ? parsed : undefined
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
    recorder_user_id: currentUserId(),
    attendees_internal: [],
    attendees_external: [],
    summary: '',
    decisions: [],
    action_items: [],
    client_token: generateToken(),
    base_version: 1,
  }
  externalName.value = ''
  drawerVisible.value = true
}

async function handleEdit(row: MeetingMinutesListItem) {
  if (row.status === 'ARCHIVED') {
    toast.warning('已归档纪要不可修改')
    return
  }

  if (row.recorder_user_id !== authStore.user?.id && !canEdit.value) {
    toast.error('暂无权限')
    return
  }

  try {
    const result = await meetApi.get(row.id)
    if (result.code === 0 && result.data) {
      const detail = result.data
      editingId.value = row.id
      drawerTitle.value = '编辑纪要'
      formModel.value = {
        title: detail.title,
        meeting_date: detail.meeting_date.slice(0, 16),
        meeting_room: detail.meeting_room || '',
        recorder_user_id: Number(detail.recorder_user_id) || undefined,
        attendees_internal: detail.attendees.internal,
        attendees_external: detail.attendees.external,
        summary: detail.summary || '',
        decisions: detail.decisions.map(d => ({ content: d.content })),
        action_items: detail.action_items.map(a => ({
          description: a.description,
          assignee_user_id: Number(a.assignee_user_id),
          due_date: a.due_date,
        })),
        client_token: generateToken(),
        base_version: detail.version,
      }
      externalName.value = ''
      drawerVisible.value = true
    }
  } catch {
    toast.error('加载详情失败')
  }
}

function addExternalAttendee() {
  const name = externalName.value.trim()
  if (!name) return
  if ([...name].length > 32) {
    toast.error('外部参会人不能超过 32 字')
    return
  }
  if (!formModel.value.attendees_external.includes(name)) {
    formModel.value.attendees_external.push(name)
  }
  externalName.value = ''
}

function removeExternalAttendee(name: string) {
  formModel.value.attendees_external = formModel.value.attendees_external.filter((item) => item !== name)
}

function addDecision() {
  formModel.value.decisions.push({ content: '' })
}

function removeDecision(index: number) {
  formModel.value.decisions.splice(index, 1)
}

function addActionItem() {
  formModel.value.action_items.push({ description: '', assignee_user_id: 0, due_date: '' })
}

function removeActionItem(index: number) {
  formModel.value.action_items.splice(index, 1)
}

function todayText() {
  return dayjs().format('YYYY-MM-DD')
}

function disablePastDate(date: Date) {
  return dayjs(date).isBefore(dayjs(), 'day')
}

async function handleSave() {
  if (!formModel.value.title.trim()) {
    toast.error('请输入会议主题')
    throw new Error('invalid')
  }
  if (formModel.value.title.length > 128) {
    toast.error('会议主题不能超过 128 字')
    throw new Error('invalid')
  }
  if (!formModel.value.meeting_date) {
    toast.error('请选择会议时间')
    throw new Error('invalid')
  }
  if (formModel.value.attendees_internal.length === 0 && formModel.value.attendees_external.length === 0) {
    toast.error('请选择参会人')
    throw new Error('invalid')
  }
  const today = todayText()
  for (const item of formModel.value.action_items) {
    if (!item.description.trim()) continue
    if (!item.assignee_user_id) {
      toast.error('请选择行动项责任人')
      throw new Error('invalid')
    }
    if (!item.due_date || item.due_date < today) {
      toast.error('行动项期限不能早于今天')
      throw new Error('invalid')
    }
  }

  const body = {
    title: formModel.value.title.trim(),
    meeting_date: formModel.value.meeting_date,
    meeting_room: formModel.value.meeting_room || null,
    recorder_user_id: formModel.value.recorder_user_id ?? null,
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

  const result = editingId.value
    ? await meetApi.update(editingId.value, body)
    : await meetApi.create(body)

  if (result.code !== 0) {
    throw new Error('save failed')
  }
  toast.success('保存成功')
  if (result.data?.warnings?.includes(1116)) {
    toast.warning('会后超过 24 小时录入纪要')
  }
  drawerVisible.value = false
  fetchList()
}

async function handleArchive(row: MeetingMinutesListItem) {
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
    const result = await meetApi.archive(row.id)
    if (result.code === 0) {
      toast.success('归档成功')
      if (result.data?.warnings?.includes(1116)) {
        toast.warning('会后超过 48 小时归档')
      }
      fetchList()
    }
  } catch {
    // Error handled by request interceptor
  }
}

async function handleDelete(row: MeetingMinutesListItem) {
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
    const result = await meetApi.delete(row.id)
    if (result.code === 0) {
      toast.success('删除成功')
      fetchList()
    }
  } catch {
    // Error handled by request interceptor
  }
}

async function handleView(row: MeetingMinutesListItem) {
  try {
    const result = await meetApi.get(row.id)
    if (result.code === 0 && result.data) {
      detailData.value = result.data
      detailTab.value = 'summary'
      detailOpen.value = true
    }
  } catch {
    toast.error('加载详情失败')
  }
}

function openAppendix(row: MeetingMinutesListItem) {
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
    const result = await meetApi.addAppendix(appendixMinutesId.value!, { content: appendixContent.value.trim() })
    if (result.code === 0) {
      toast.success('附录添加成功')
      appendixVisible.value = false
      fetchList()
    }
  } catch {
    // Error handled by request interceptor
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
    throw new Error('invalid')
  }
  if ([...closeActionForm.value.close_remark].length > 512) {
    toast.error('闭环说明不能超过 512 字')
    throw new Error('invalid')
  }
  if (closeActionForm.value.evidence_url) {
    let url: URL
    try {
      url = new URL(closeActionForm.value.evidence_url)
    } catch (error) {
      toast.error('证据链接格式不正确')
      throw new Error('invalid', { cause: error })
    }
    if (!['http:', 'https:'].includes(url.protocol)) {
      toast.error('证据链接仅支持 http/https')
      throw new Error('invalid')
    }
  }

  const result = await meetApi.closeActionItem(closingActionItemId.value!, closeActionForm.value)
  if (result.code !== 0) {
    throw new Error('save failed')
  }
  toast.success('行动项已闭环')
  closeActionVisible.value = false
  if (detailData.value) {
    const refreshed = await meetApi.get(detailData.value.id)
    if (refreshed.code === 0 && refreshed.data) detailData.value = refreshed.data
  }
  fetchList()
}

function openArchiveRatePage() {
  router.push('/ims/meet/archive-rate')
}

function isRecorder(row: MeetingMinutesListItem): boolean {
  return row.recorder_user_id === authStore.user?.id
}

function canEditRow(row: MeetingMinutesListItem): boolean {
  return row.status !== 'ARCHIVED' && (isRecorder(row) || canEdit.value)
}

function canArchiveRow(row: MeetingMinutesListItem): boolean {
  return row.status === 'MINUTES_RECORDED' && (isRecorder(row) || canArchive.value)
}

function canAppendixRow(row: MeetingMinutesListItem): boolean {
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

      <div v-if="canSupervise" class="metric-cards">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="8">
            <el-card shadow="hover">
              <div class="metric-label">本期会议数</div>
              <div class="metric-value">{{ archiveRate?.total_meetings ?? 0 }}</div>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-card shadow="hover" class="metric-click" @click="unarchivedOpen = true">
              <div class="metric-label">已归档</div>
              <div class="metric-value">{{ archiveRate?.archived_count ?? 0 }}</div>
              <el-button link type="primary">未归档</el-button>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-card shadow="hover" class="metric-click" @click="openArchiveRatePage">
              <div class="metric-label">留痕率</div>
              <div class="metric-value" :class="{ low: (archiveRate?.archive_rate ?? 100) < 100 }">
                {{ archiveRate?.archive_rate ?? 100 }}%
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <div class="search-bar">
        <el-form :model="searchForm" inline>
          <el-form-item label="主题">
            <el-input v-model="searchForm.title" placeholder="请输入会议主题" clearable />
          </el-form-item>
          <el-form-item label="会议时间">
            <DateRangePicker v-model="dateRange" />
          </el-form-item>
          <el-form-item label="状态">
            <DictSelect v-model="searchForm.status" dict-type="meet_minutes_status" placeholder="全部" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
        <div class="toolbar">
          <el-button v-if="canAdd" type="primary" @click="handleAdd">登记会议</el-button>
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
            <StatusTag dict-type="meet_minutes_status" :value="row.status" />
          </template>
        </el-table-column>
        <el-table-column label="行动项" width="160">
          <template #default="{ row }">
            {{ row.action_item_count }} 项（{{ row.action_item_closed_count }} 已闭环）
          </template>
        </el-table-column>
        <el-table-column prop="archived_at" label="归档时间" width="160">
          <template #default="{ row }">{{ row.archived_at ? fmtDateTime(row.archived_at) : '-' }}</template>
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
        v-model:open="drawerVisible"
        :title="drawerTitle"
        size="M"
        :submit="handleSave"
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
          <el-form-item label="内部参会人" required>
            <UserSelect v-model="formModel.attendees_internal" multiple placeholder="选择内部参会人" />
          </el-form-item>
          <el-form-item label="外部参会人">
            <div class="external-row">
              <el-input
                v-model="externalName"
                placeholder="外部参会人姓名"
                maxlength="32"
                @keyup.enter="addExternalAttendee"
              />
              <el-button @click="addExternalAttendee">添加</el-button>
            </div>
            <div v-if="formModel.attendees_external.length" class="external-tags">
              <el-tag
                v-for="name in formModel.attendees_external"
                :key="name"
                closable
                @close="removeExternalAttendee(name)"
              >
                {{ name }}
              </el-tag>
            </div>
          </el-form-item>
          <el-form-item label="会议室">
            <el-input v-model="formModel.meeting_room" placeholder="请输入会议室" />
          </el-form-item>
          <el-form-item label="记录人">
            <UserSelect v-model="formModel.recorder_user_id" placeholder="选择记录人" />
          </el-form-item>
          <el-form-item label="纪要正文">
            <el-input
              v-model="formModel.summary"
              type="textarea"
              :rows="6"
              maxlength="20000"
              show-word-limit
              placeholder="请输入纪要正文"
            />
          </el-form-item>
          <el-form-item label="决议事项">
            <div class="dynamic-list">
              <div v-for="(decision, index) in formModel.decisions" :key="index" class="dynamic-row">
                <el-input v-model="decision.content" placeholder="决议内容" />
                <el-button link type="danger" @click="removeDecision(index)">删除</el-button>
              </div>
              <el-button @click="addDecision">添加决议</el-button>
            </div>
          </el-form-item>
          <el-form-item label="行动项">
            <div class="dynamic-list">
              <div v-for="(item, index) in formModel.action_items" :key="index" class="action-row">
                <el-input v-model="item.description" placeholder="行动项描述" />
                <UserSelect v-model="item.assignee_user_id" placeholder="责任人" />
                <el-date-picker
                  v-model="item.due_date"
                  type="date"
                  placeholder="期限"
                  value-format="YYYY-MM-DD"
                  :disabled-date="disablePastDate"
                />
                <el-button link type="danger" @click="removeActionItem(index)">删除</el-button>
              </div>
              <el-button @click="addActionItem">添加行动项</el-button>
            </div>
          </el-form-item>
        </el-form>
      </FormDrawer>

      <DetailDrawer v-model="detailOpen" title="会议纪要详情" size="70%">
        <template v-if="detailData">
          <el-tabs v-model="detailTab">
            <el-tab-pane label="纪要正文" name="summary">
              <el-descriptions :column="isMobile ? 1 : 2" border>
                <el-descriptions-item label="编号">{{ detailData.code }}</el-descriptions-item>
                <el-descriptions-item label="主题">{{ detailData.title }}</el-descriptions-item>
                <el-descriptions-item label="会议时间">{{ fmtDateTime(detailData.meeting_date) }}</el-descriptions-item>
                <el-descriptions-item label="会议室">{{ detailData.meeting_room || '-' }}</el-descriptions-item>
                <el-descriptions-item label="记录人">{{ detailData.recorder_name }}</el-descriptions-item>
                <el-descriptions-item label="状态">
                  <StatusTag dict-type="meet_minutes_status" :value="detailData.status" />
                </el-descriptions-item>
                <el-descriptions-item label="参会人" :span="2">{{ detailData.attendee_names.join('、') }}</el-descriptions-item>
              </el-descriptions>
              <div class="summary-section">
                <h4>纪要正文</h4>
                <div v-if="detailData.summary" v-html="detailData.summary"></div>
                <div v-else>-</div>
              </div>
              <div class="summary-section">
                <h4>附录</h4>
                <el-table :data="[...(detailData.appendices || [])].reverse()" stripe>
                  <el-table-column prop="content" label="内容" />
                  <el-table-column prop="creator_name" label="添加人" width="100" />
                  <el-table-column prop="create_time" label="添加时间" width="160">
                    <template #default="{ row }">{{ fmtDateTime(row.create_time) }}</template>
                  </el-table-column>
                </el-table>
              </div>
            </el-tab-pane>
            <el-tab-pane label="决议事项" name="decisions">
              <el-table :data="detailData.decisions" stripe>
                <el-table-column prop="seq" label="序号" width="80" />
                <el-table-column prop="content" label="内容" />
              </el-table>
            </el-tab-pane>
            <el-tab-pane label="行动项跟踪" name="actions">
              <el-table :data="detailData.action_items" stripe>
                <el-table-column prop="description" label="描述" min-width="200" />
                <el-table-column prop="assignee_name" label="责任人" width="100" />
                <el-table-column prop="due_date" label="截止日期" width="120" />
                <el-table-column prop="overdue_days" label="逾期天数" width="100">
                  <template #default="{ row }">{{ row.overdue_days ?? '-' }}</template>
                </el-table-column>
                <el-table-column label="推送" width="90">
                  <template #default="{ row }">{{ row.notified_at ? '已推送' : '-' }}</template>
                </el-table-column>
                <el-table-column label="升级" width="90">
                  <template #default="{ row }">{{ row.escalated_at ? '已升级' : '-' }}</template>
                </el-table-column>
                <el-table-column prop="status" label="状态" width="100">
                  <template #default="{ row }">
                    <StatusTag dict-type="meet_action_status" :value="row.status" />
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="100">
                  <template #default="{ row }">
                    <el-button v-if="row.status !== 'CLOSED'" link type="primary" @click="openCloseAction(row)">回填</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
            <el-tab-pane label="操作留痕" name="traces">
              <el-table :data="detailData.traces || []" stripe>
                <el-table-column prop="operation" label="操作" width="140" />
                <el-table-column prop="operator_name" label="操作人" width="120" />
                <el-table-column prop="create_time" label="时间" width="180">
                  <template #default="{ row }">{{ fmtDateTime(row.create_time) }}</template>
                </el-table-column>
              </el-table>
              <el-descriptions v-if="!(detailData.traces || []).length" :column="1" border class="summary-section">
                <el-descriptions-item label="登记时间">{{ fmtDateTime(detailData.create_time) }}</el-descriptions-item>
                <el-descriptions-item label="更新时间">{{ detailData.update_time ? fmtDateTime(detailData.update_time) : '-' }}</el-descriptions-item>
                <el-descriptions-item label="归档时间">{{ detailData.archived_at ? fmtDateTime(detailData.archived_at) : '-' }}</el-descriptions-item>
              </el-descriptions>
            </el-tab-pane>
          </el-tabs>
        </template>
      </DetailDrawer>

      <el-drawer v-model="unarchivedOpen" title="未归档清单" size="480px">
        <el-table :data="archiveRate?.unarchived_list ?? []" stripe>
          <el-table-column prop="minutes_no" label="编号" width="140" />
          <el-table-column prop="meeting_title" label="会议主题" min-width="160" show-overflow-tooltip />
          <el-table-column prop="recorder_name" label="记录人" width="100" />
          <el-table-column label="距今" width="90">
            <template #default="{ row }">
              <span :class="{ 'hours-danger': row.hours_since_meeting > 48 }">{{ row.hours_since_meeting }}h</span>
            </template>
          </el-table-column>
        </el-table>
      </el-drawer>

      <el-dialog v-model="appendixVisible" title="添加附录说明" width="500px">
        <el-input v-model="appendixContent" type="textarea" :rows="4" placeholder="请输入附录内容" />
        <template #footer>
          <el-button @click="appendixVisible = false">取消</el-button>
          <el-button type="primary" @click="handleAppendixSave">确定</el-button>
        </template>
      </el-dialog>

      <FormDrawer
        v-model:open="closeActionVisible"
        title="行动项回填"
        size="S"
        :submit="handleCloseAction"
      >
        <el-form :model="closeActionForm" label-width="100px">
          <el-form-item label="闭环说明" required>
            <el-input
              v-model="closeActionForm.close_remark"
              type="textarea"
              :rows="3"
              maxlength="512"
              show-word-limit
              placeholder="请输入闭环说明"
            />
          </el-form-item>
          <el-form-item label="证据链接">
            <el-input v-model="closeActionForm.evidence_url" placeholder="请输入证据链接（仅支持 http/https）" />
          </el-form-item>
        </el-form>
      </FormDrawer>
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

.metric-cards {
  margin-bottom: var(--space-m);
}

.metric-label {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.metric-value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 600;
}

.metric-value.low {
  color: var(--color-danger);
}

.metric-click {
  cursor: pointer;
}

.external-row,
.dynamic-row,
.action-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
  width: 100%;
}

.external-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.dynamic-list {
  width: 100%;
}

.hours-danger {
  color: var(--color-danger);
  font-weight: 600;
}
</style>
