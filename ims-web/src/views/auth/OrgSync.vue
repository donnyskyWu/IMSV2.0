<script setup lang="ts">
/**
 * 组织架构同步页 (FP-B1-ORG-01~11)
 * 依据: 01-功能点清单.md, 00-工作包.md
 */
import { ref, computed, onMounted, watch } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import StatusTag from '@/components/list/StatusTag.vue'
import Pagination from '@/components/list/Pagination.vue'
import EmptyState from '@/components/list/EmptyState.vue'
import DetailDrawer from '@/components/form/DetailDrawer.vue'
import { toast } from '@/utils/toast'
import { useResponsive } from '@/utils/responsive'
import { fmtDateTime } from '@/utils/format'
import { orgSyncApi } from '@/api/orgSync'
import type { SyncMetrics, SyncEvent, DiffSummary } from '@/api/orgSync'
import type { EmptyType } from '@/types'

const { isMobile } = useResponsive()

const activeTab = ref('events')
const loading = ref(false)
const emptyMode = ref<EmptyType | ''>('')

// Metrics
const metrics = ref<SyncMetrics | null>(null)

// Events
const events = ref<SyncEvent[]>([])
const eventPageNo = ref(1)
const eventPageSize = ref(10)
const eventTotal = ref(0)
const eventSearchForm = ref({
  keyword: '',
  status: '',
  eventType: '',
  startTime: '',
  endTime: '',
})

// Diff summary
const diffSummary = ref<DiffSummary | null>(null)
const diffCategory = ref('OVERRIDE')

// Detail drawer
const detailOpen = ref(false)
const detailEvent = ref<SyncEvent | null>(null)
const detailTab = ref('base')

// Replay drawer
const replayOpen = ref(false)
const replayForm = ref({
  startTime: '',
  endTime: '',
  statuses: ['DEAD', 'RETRYING'],
})
const replayPreviewCount = ref(0)

const showDingtalkAlert = computed(() => metrics.value?.dingtalkUnavailable ?? false)
const showReconcileAlert = computed(() => metrics.value?.reconcileFailedTwice ?? false)

const statCards = computed(() => {
  if (!metrics.value) return []
  return [
    { label: '在职人员', value: metrics.value.userTotal, type: 'default' },
    { label: '昨日事件', value: metrics.value.yesterdayEventCount, type: 'default' },
    { label: '待处理', value: metrics.value.pendingEventCount, type: metrics.value.pendingEventCount > 0 ? 'warning' : 'default' },
    { label: '死信', value: metrics.value.deadEventCount, type: metrics.value.deadEventCount > 0 ? 'danger' : 'default' },
  ]
})

async function loadMetrics() {
  try {
    const res = await request.get('/admin-api/ims/auth/org/sync-metrics')
    if (res.data.code === 0) {
      metrics.value = res.data.data
    }
  } catch (e) {
    console.error('Failed to load metrics', e)
  }
}

async function loadEvents() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      pageNo: eventPageNo.value,
      pageSize: eventPageSize.value,
    }
    if (eventSearchForm.value.keyword) params.keyword = eventSearchForm.value.keyword
    if (eventSearchForm.value.status) params.statuses = eventSearchForm.value.status
    if (eventSearchForm.value.eventType) params.eventTypes = eventSearchForm.value.eventType

    const res = await request.get('/admin-api/ims/auth/org/events', { params })
    if (res.data.code === 0) {
      events.value = res.data.data.list
      eventTotal.value = res.data.data.total
      emptyMode.value = ''
    } else if (res.data.code === 1008) {
      emptyMode.value = 'noPermission'
    } else {
      emptyMode.value = 'error'
    }
  } catch (e) {
    emptyMode.value = 'error'
  } finally {
    loading.value = false
  }
}

async function loadDiffSummary() {
  try {
    const res = await request.get('/admin-api/ims/auth/org/diffs/summary')
    if (res.data.code === 0) {
      diffSummary.value = res.data.data
    }
  } catch (e) {
    console.error('Failed to load diff summary', e)
  }
}

async function handleEventSearch() {
  eventPageNo.value = 1
  await loadEvents()
}

function handleEventReset() {
  eventSearchForm.value = {
    keyword: '',
    status: '',
    eventType: '',
    startTime: '',
    endTime: '',
  }
  eventPageNo.value = 1
  loadEvents()
}

async function handleViewEvent(event: SyncEvent) {
  try {
    const res = await request.get(`/admin-api/ims/auth/org/events/${event.id}`)
    if (res.data.code === 0) {
      detailEvent.value = res.data.data
      detailTab.value = 'base'
      detailOpen.value = true
    } else {
      toast.error(res.data.msg || '加载失败')
    }
  } catch (e) {
    toast.error('加载失败')
  }
}

async function handleRetryEvent(event: SyncEvent) {
  try {
    const res = await request.post(`/admin-api/ims/auth/org/events/${event.id}/retry`)
    if (res.data.code === 0) {
      toast.success('重试成功')
      loadEvents()
    } else if (res.data.code === 1286) {
      toast.warning('事件状态已变化，请刷新后重试')
      loadEvents()
    } else {
      toast.error(res.data.msg || '重试失败')
    }
  } catch (e) {
    toast.error('重试失败')
  }
}

async function handleReconcile() {
  try {
    const res = await request.post('/admin-api/ims/system/org-sync/reconcile')
    if (res.data.code === 0) {
      toast.success('对账任务已启动')
      loadMetrics()
    } else if (res.data.code === 1001) {
      toast.warning('同步正在进行中')
    } else {
      toast.error(res.data.msg || '对账失败')
    }
  } catch (e) {
    toast.error('对账失败')
  }
}

function openReplayDrawer() {
  replayForm.value = {
    startTime: '',
    endTime: '',
    statuses: ['DEAD', 'RETRYING'],
  }
  replayPreviewCount.value = 0
  replayOpen.value = true
}

async function handleReplayPreview() {
  if (!replayForm.value.startTime || !replayForm.value.endTime) {
    toast.warning('请选择时间范围')
    return
  }
  try {
    const res = await request.get('/admin-api/ims/auth/org/events/replay-preview', {
      params: {
        startTime: replayForm.value.startTime,
        endTime: replayForm.value.endTime,
        statuses: replayForm.value.statuses.join(','),
      },
    })
    if (res.data.code === 0) {
      replayPreviewCount.value = res.data.data.count
    } else {
      toast.error(res.data.msg || '预览失败')
    }
  } catch (e) {
    toast.error('预览失败')
  }
}

async function handleReplay() {
  if (!replayForm.value.startTime || !replayForm.value.endTime) {
    toast.warning('请选择时间范围')
    return
  }
  try {
    const res = await request.post('/admin-api/ims/auth/org/events/replay', {
      startTime: replayForm.value.startTime,
      endTime: replayForm.value.endTime,
      statuses: replayForm.value.statuses,
    })
    if (res.data.code === 0) {
      toast.success(`已重放 ${res.data.data.count} 条事件`)
      replayOpen.value = false
      loadEvents()
    } else {
      toast.error(res.data.msg || '重放失败')
    }
  } catch (e) {
    toast.error('重放失败')
  }
}

function getStatusType(status: string): string {
  switch (status) {
    case 'SUCCESS':
      return 'success'
    case 'PENDING':
      return 'warning'
    case 'RETRYING':
      return 'warning'
    case 'DEAD':
      return 'danger'
    case 'SKIPPED':
      return 'neutral'
    default:
      return 'neutral'
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case 'SUCCESS':
      return '已同步'
    case 'PENDING':
      return '待处理'
    case 'RETRYING':
      return '重试中'
    case 'DEAD':
      return '死信'
    case 'SKIPPED':
      return '已跳过'
    default:
      return status
  }
}

function getBizTypeLabel(bizType: string | null): string {
  if (!bizType) return '-'
  const map: Record<string, string> = {
    'HIRE': '入职',
    'RESIGN': '离职',
    'TRANSFER': '调岗',
    'USER_UPDATE': '信息更新',
    'DEPT_CREATE': '部门新增',
    'DEPT_UPDATE': '部门更新',
    'DEPT_DELETE': '部门删除',
  }
  return map[bizType] || bizType
}

function canRetry(event: SyncEvent): boolean {
  return event.status === 'RETRYING' || event.status === 'DEAD'
}

onMounted(() => {
  loadMetrics()
  loadEvents()
  loadDiffSummary()
})

watch(eventPageNo, loadEvents)
watch(eventPageSize, () => {
  eventPageNo.value = 1
  loadEvents()
})
</script>

<template>
  <AppLayout>
    <div class="org-sync-page">
      <PageHeader title="组织架构同步" data-testid="b1-page-title">
        <template #actions>
          <el-button @click="openReplayDrawer">重放失败事件</el-button>
          <el-button type="primary" @click="handleReconcile">手动对账</el-button>
        </template>
        <template #primary-action>
          <el-button type="primary" @click="handleReconcile">手动对账</el-button>
        </template>
      </PageHeader>

      <!-- Alert banners -->
      <div v-if="showDingtalkAlert" class="alert-banner alert-danger">
        <span>钉钉服务不可用，最近 10 分钟内有超时记录</span>
      </div>
      <div v-if="showReconcileAlert" class="alert-banner alert-danger">
        <span>对账连续两次失败，请检查钉钉连接状态</span>
      </div>

      <!-- Stat cards -->
      <div class="stat-cards" data-testid="sync-stat-cards">
        <div
          v-for="card in statCards"
          :key="card.label"
          class="stat-card"
          :class="{ warning: card.type === 'warning', danger: card.type === 'danger' }"
        >
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
        <div v-if="metrics" class="stat-card">
          <div class="stat-value">{{ (metrics.successRate24h * 100).toFixed(0) }}%</div>
          <div class="stat-label">24h 成功率</div>
        </div>
        <div v-if="metrics" class="stat-card" :class="{ danger: metrics.avgDelayMinutes > 5 }">
          <div class="stat-value">{{ metrics.avgDelayMinutes.toFixed(1) }}m</div>
          <div class="stat-label">平均延迟</div>
        </div>
      </div>

      <!-- Tabs -->
      <el-tabs v-model="activeTab" class="sync-tabs">
        <el-tab-pane label="同步事件" name="events">
          <div class="query-bar">
            <el-form :model="eventSearchForm" inline @submit.prevent="handleEventSearch">
              <el-form-item class="query-field" label="关键词">
                <el-input
                  v-model="eventSearchForm.keyword"
                  placeholder="姓名/工号/事件ID"
                  clearable
                  maxlength="50"
                  @keyup.enter="handleEventSearch"
                />
              </el-form-item>
              <el-form-item class="query-field" label="状态">
                <el-select v-model="eventSearchForm.status" placeholder="全部" clearable style="width: 120px">
                  <el-option label="待处理" value="PENDING" />
                  <el-option label="已同步" value="SUCCESS" />
                  <el-option label="重试中" value="RETRYING" />
                  <el-option label="死信" value="DEAD" />
                </el-select>
              </el-form-item>
              <el-form-item class="query-field" label="事件类型">
                <el-select v-model="eventSearchForm.eventType" placeholder="全部" clearable style="width: 140px">
                  <el-option label="入职" value="user_add_org" />
                  <el-option label="离职" value="user_leave_org" />
                  <el-option label="信息变更" value="user_modify_org" />
                  <el-option label="部门新增" value="org_dept_create" />
                  <el-option label="部门变更" value="org_dept_modify" />
                  <el-option label="部门删除" value="org_dept_remove" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleEventSearch">查询</el-button>
                <el-button @click="handleEventReset">重置</el-button>
              </el-form-item>
            </el-form>
          </div>

          <div v-loading="loading" class="table-wrap">
            <el-table v-if="!emptyMode" :data="events" style="width: 100%">
              <el-table-column prop="eventId" label="事件ID" min-width="180" show-overflow-tooltip />
              <el-table-column prop="bizType" label="类型" width="100">
                <template #default="{ row }">
                  {{ getBizTypeLabel(row.bizType) }}
                </template>
              </el-table-column>
              <el-table-column prop="subjectName" label="对象" width="120" show-overflow-tooltip />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <span :class="`status-${getStatusType(row.status)}`">
                    {{ getStatusLabel(row.status) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="retryCount" label="重试" width="80" align="center" />
              <el-table-column prop="eventTime" label="事件时间" width="160">
                <template #default="{ row }">
                  {{ row.eventTime ? fmtDateTime(row.eventTime) : '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="processedTime" label="处理时间" width="160">
                <template #default="{ row }">
                  {{ row.processedTime ? fmtDateTime(row.processedTime) : '-' }}
                </template>
              </el-table-column>
              <el-table-column label="操作" :width="isMobile ? 72 : 140" fixed="right">
                <template #default="{ row }">
                  <el-button text type="primary" size="small" @click="handleViewEvent(row)">详情</el-button>
                  <el-button
                    v-if="canRetry(row)"
                    text
                    type="primary"
                    size="small"
                    @click="handleRetryEvent(row)"
                  >
                    重试
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <EmptyState v-else :type="emptyMode" @retry="loadEvents" />
          </div>

          <Pagination v-model:page-no="eventPageNo" v-model:page-size="eventPageSize" :total="eventTotal" />
        </el-tab-pane>

        <el-tab-pane label="同步差异" name="diffs">
          <div v-if="diffSummary" class="diff-categories">
            <el-radio-group v-model="diffCategory">
              <el-radio-button value="OVERRIDE">
                覆盖修改 ({{ diffSummary.overrideCount }})
              </el-radio-button>
              <el-radio-button value="PENDING_ASSIGN">
                待分配 ({{ diffSummary.pendingAssignCount }})
              </el-radio-button>
              <el-radio-button value="LOCAL_ORPHAN">
                待确认 ({{ diffSummary.localOrphanCount }})
              </el-radio-button>
              <el-radio-button value="SAME_NAME">
                同名部门 ({{ diffSummary.sameNameCount }})
              </el-radio-button>
              <el-radio-button value="UNBOUND">
                未绑定 ({{ diffSummary.unboundCount }})
              </el-radio-button>
            </el-radio-group>
          </div>
          <div class="table-wrap">
            <EmptyState type="empty" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="对账报告" name="reconcile">
          <div class="table-wrap">
            <EmptyState type="empty" />
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- Event detail drawer -->
      <DetailDrawer
        v-model="detailOpen"
        :title="detailEvent?.eventId || '事件详情'"
        :tabs="[{ key: 'base', label: '基本信息' }, { key: 'timeline', label: '处理时间线' }]"
        :active-tab="detailTab"
        @update:active-tab="detailTab = $event"
      >
        <div v-if="detailTab === 'base' && detailEvent" class="detail-content">
          <div class="detail-row">
            <span class="detail-label">事件ID</span>
            <span class="detail-value mono">{{ detailEvent.eventId }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">类型</span>
            <span class="detail-value">{{ getBizTypeLabel(detailEvent.bizType) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">对象</span>
            <span class="detail-value">{{ detailEvent.subjectName || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">状态</span>
            <span class="detail-value" :class="`status-${getStatusType(detailEvent.status)}`">
              {{ getStatusLabel(detailEvent.status) }}
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-label">重试次数</span>
            <span class="detail-value">{{ detailEvent.retryCount }}</span>
          </div>
          <div v-if="detailEvent.lastError" class="detail-row">
            <span class="detail-label">错误信息</span>
            <span class="detail-value error-text">{{ detailEvent.lastError }}</span>
          </div>
        </div>
        <div v-if="detailTab === 'timeline' && detailEvent?.attempts" class="timeline-content">
          <div v-for="attempt in detailEvent.attempts" :key="attempt.attempt_no" class="timeline-item">
            <div class="timeline-header">
              <span class="attempt-no">#{{ attempt.attempt_no }}</span>
              <span :class="`status-${attempt.result === 'SUCCESS' ? 'success' : 'danger'}`">
                {{ attempt.result === 'SUCCESS' ? '成功' : '失败' }}
              </span>
            </div>
            <div class="timeline-time">{{ fmtDateTime(attempt.start_time) }}</div>
            <div v-if="attempt.error_msg" class="timeline-error">{{ attempt.error_msg }}</div>
          </div>
          <div v-if="!detailEvent.attempts?.length" class="empty-timeline">暂无处理记录</div>
        </div>
        <template #footer>
          <el-button v-if="detailEvent && canRetry(detailEvent)" type="primary" @click="handleRetryEvent(detailEvent)">
            重试
          </el-button>
          <el-button @click="detailOpen = false">关闭</el-button>
        </template>
      </DetailDrawer>

      <!-- Replay drawer -->
      <el-drawer v-model="replayOpen" title="重放失败事件" size="400px">
        <el-form :model="replayForm" label-width="80px">
          <el-form-item label="开始时间" required>
            <el-date-picker
              v-model="replayForm.startTime"
              type="datetime"
              placeholder="选择开始时间"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="结束时间" required>
            <el-date-picker
              v-model="replayForm.endTime"
              type="datetime"
              placeholder="选择结束时间"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-checkbox-group v-model="replayForm.statuses">
              <el-checkbox value="DEAD">死信</el-checkbox>
              <el-checkbox value="RETRYING">重试中</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item>
            <el-button @click="handleReplayPreview">预览</el-button>
            <span v-if="replayPreviewCount > 0" class="preview-count">
              共 {{ replayPreviewCount }} 条事件
            </span>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="replayOpen = false">取消</el-button>
          <el-button type="primary" :disabled="replayPreviewCount === 0" @click="handleReplay">
            确认重放
          </el-button>
        </template>
      </el-drawer>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.org-sync-page {
  width: 100%;
}

.alert-banner {
  padding: 12px 16px;
  margin-bottom: 16px;
  border-radius: var(--r-s);
  font-size: 14px;

  &.alert-danger {
    background-color: var(--red-bg);
    color: var(--red);
    border: 1px solid var(--red);
  }
}

.stat-cards {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.stat-card {
  flex: 1;
  min-width: 120px;
  padding: 16px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
  text-align: center;

  &.warning {
    border-color: var(--yellow);
    .stat-value {
      color: var(--yellow);
    }
  }

  &.danger {
    border-color: var(--red);
    .stat-value {
      color: var(--red);
    }
  }
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--text);
}

.stat-label {
  font-size: 12px;
  color: var(--text2);
  margin-top: 4px;
}

.sync-tabs {
  margin-top: 16px;
}

.query-bar {
  margin-bottom: 16px;
  padding: 16px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);

  :deep(.el-form-item) {
    margin-bottom: 12px;
    margin-right: 16px;
  }

  :deep(.el-input) {
    width: 180px;
  }
}

.table-wrap {
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
  overflow: hidden;
  min-height: 120px;
}

.diff-categories {
  margin-bottom: 16px;
}

.mono {
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  font-size: 12px;
}

.status-success {
  color: var(--green);
}

.status-warning {
  color: var(--yellow);
}

.status-danger {
  color: var(--red);
}

.status-neutral {
  color: var(--text2);
}

.detail-content {
  padding: 16px 0;
}

.detail-row {
  display: flex;
  margin-bottom: 12px;
}

.detail-label {
  width: 80px;
  color: var(--text2);
  flex-shrink: 0;
}

.detail-value {
  flex: 1;
}

.error-text {
  color: var(--red);
}

.timeline-content {
  padding: 16px 0;
}

.timeline-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--line);

  &:last-child {
    border-bottom: none;
  }
}

.timeline-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.attempt-no {
  font-weight: 600;
}

.timeline-time {
  font-size: 12px;
  color: var(--text2);
}

.timeline-error {
  margin-top: 4px;
  font-size: 12px;
  color: var(--red);
}

.empty-timeline {
  text-align: center;
  color: var(--text2);
  padding: 24px;
}

.preview-count {
  margin-left: 12px;
  color: var(--text2);
}
</style>
