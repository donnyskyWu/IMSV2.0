<script setup lang="ts">
/**
 * 培训统计 (FP-B21-SS-01~06)
 * Tab看板：完成率、部门汇总、排行、逾期、热度
 */
import { ref, computed, onMounted, watch } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import Pagination from '@/components/list/Pagination.vue'
import EmptyState from '@/components/list/EmptyState.vue'
import { toast } from '@/utils/toast'
import {
  getFinishRate,
  getDeptStat,
  getRank,
  getOverdueList,
  exportOverdue,
  getMaterialHeat,
  type TrainStatFinishRate,
  type TrainStatDept,
  type TrainStatRank,
  type TrainStatOverdue,
  type TrainMaterialHeat,
} from '@/api/generated/train'
import type { EmptyType } from '@/types'

const activeTab = ref('overview')

const loading = ref(false)
const emptyMode = ref<EmptyType | ''>('')

const finishRate = ref<TrainStatFinishRate | null>(null)
const deptStats = ref<TrainStatDept[]>([])
const ranks = ref<TrainStatRank[]>([])
const overdueList = ref<TrainStatOverdue[]>([])
const overdueTotal = ref(0)
const overduePageNo = ref(1)
const overduePageSize = ref(10)
const heatList = ref<TrainMaterialHeat[]>([])

const deptFilter = ref('')
const dateRange = ref<[string, string] | null>(null)

async function loadOverview() {
  loading.value = true
  emptyMode.value = ''
  try {
    const [rateRes, deptRes] = await Promise.all([
      getFinishRate({ deptId: deptFilter.value || undefined }),
      getDeptStat({ deptId: deptFilter.value || undefined }),
    ])
    finishRate.value = rateRes.data || null
    deptStats.value = deptRes.data?.list || []
  } catch {
    emptyMode.value = 'error'
  } finally {
    loading.value = false
  }
}

async function loadRank() {
  loading.value = true
  emptyMode.value = ''
  try {
    const res = await getRank({ deptId: deptFilter.value || undefined, limit: 20 })
    ranks.value = res.data?.list || []
    if (ranks.value.length === 0) {
      emptyMode.value = 'empty'
    }
  } catch {
    emptyMode.value = 'error'
  } finally {
    loading.value = false
  }
}

async function loadOverdue() {
  loading.value = true
  emptyMode.value = ''
  try {
    const res = await getOverdueList({
      deptId: deptFilter.value || undefined,
      pageNo: overduePageNo.value,
      pageSize: overduePageSize.value,
    })
    overdueList.value = res.data?.list || []
    overdueTotal.value = res.data?.total || 0
    if (overdueList.value.length === 0) {
      emptyMode.value = 'empty'
    }
  } catch {
    emptyMode.value = 'error'
  } finally {
    loading.value = false
  }
}

async function loadHeat() {
  loading.value = true
  emptyMode.value = ''
  try {
    const res = await getMaterialHeat({ limit: 20 })
    heatList.value = res.data?.list || []
    if (heatList.value.length === 0) {
      emptyMode.value = 'empty'
    }
  } catch {
    emptyMode.value = 'error'
  } finally {
    loading.value = false
  }
}

async function handleExportOverdue() {
  try {
    const res = await exportOverdue({ deptId: deptFilter.value || undefined })
    if (res.data?.taskId) {
      toast.success('导出任务已创建，请稍后下载')
    }
  } catch {
    toast.error('导出失败')
  }
}

function loadData() {
  switch (activeTab.value) {
    case 'overview':
      loadOverview()
      break
    case 'rank':
      loadRank()
      break
    case 'overdue':
      loadOverdue()
      break
    case 'heat':
      loadHeat()
      break
  }
}

function handleRetry() {
  loadData()
}

const ratePercent = computed(() => {
  if (!finishRate.value) return 0
  return Math.round(finishRate.value.finishRate * 100) / 100
})

const overduePercent = computed(() => {
  if (!finishRate.value) return 0
  return Math.round(finishRate.value.overdueRate * 100) / 100
})

onMounted(loadData)
watch(activeTab, loadData)
watch(overduePageNo, loadOverdue)
watch(deptFilter, loadData)
</script>

<template>
  <AppLayout>
    <div class="stat-dashboard">
      <PageHeader title="培训统计" sub-title="FP-B21-SS">
        <template #actions>
          <el-select v-model="deptFilter" placeholder="全部部门" clearable style="width: 150px">
            <el-option label="市场部" value="1" />
            <el-option label="技术部" value="2" />
            <el-option label="运营部" value="3" />
          </el-select>
        </template>
      </PageHeader>

      <el-tabs v-model="activeTab" class="stat-tabs">
        <el-tab-pane label="总览" name="overview">
          <div v-loading="loading" class="tab-content">
            <template v-if="!emptyMode">
              <div class="stat-cards">
                <div class="stat-card">
                  <div class="stat-card-title">完成率</div>
                  <div class="stat-card-value primary">{{ ratePercent }}%</div>
                  <div class="stat-card-sub">
                    {{ finishRate?.totalFinished || 0 }} / {{ finishRate?.totalAssigned || 0 }} 人次
                  </div>
                </div>
                <div class="stat-card">
                  <div class="stat-card-title">逾期率</div>
                  <div class="stat-card-value danger">{{ overduePercent }}%</div>
                  <div class="stat-card-sub">
                    {{ finishRate?.totalOverdue || 0 }} 人次逾期
                  </div>
                </div>
                <div class="stat-card">
                  <div class="stat-card-title">应完成</div>
                  <div class="stat-card-value">{{ finishRate?.totalAssigned || 0 }}</div>
                  <div class="stat-card-sub">人次</div>
                </div>
                <div class="stat-card">
                  <div class="stat-card-title">已完成</div>
                  <div class="stat-card-value success">{{ finishRate?.totalFinished || 0 }}</div>
                  <div class="stat-card-sub">人次</div>
                </div>
              </div>

              <div class="section">
                <h4>部门完成情况</h4>
                <el-table :data="deptStats" style="width: 100%">
                  <el-table-column prop="deptName" label="部门" min-width="120" />
                  <el-table-column prop="assignedCount" label="应完成" width="100" align="right" />
                  <el-table-column prop="finishedCount" label="已完成" width="100" align="right" />
                  <el-table-column prop="overdueCount" label="逾期" width="80" align="right">
                    <template #default="{ row }">
                      <span :class="{ 'text-danger': row.overdueCount > 0 }">{{ row.overdueCount }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="完成率" width="150">
                    <template #default="{ row }">
                      <el-progress :percentage="row.finishRate" :stroke-width="6" />
                    </template>
                  </el-table-column>
                  <el-table-column label="人均时长" width="100" align="right">
                    <template #default="{ row }">
                      {{ row.avgMinutes }} 分钟
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </template>
            <EmptyState v-else :type="emptyMode" @retry="handleRetry" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="学习排行" name="rank">
          <div v-loading="loading" class="tab-content">
            <template v-if="!emptyMode && ranks.length > 0">
              <el-table :data="ranks" style="width: 100%">
                <el-table-column type="index" label="排名" width="80" align="center">
                  <template #default="{ $index }">
                    <span :class="['rank-badge', `rank-${$index + 1}`]">{{ $index + 1 }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="userName" label="姓名" width="120" />
                <el-table-column prop="deptName" label="部门" min-width="120" />
                <el-table-column prop="totalMinutes" label="学习时长" width="120" align="right">
                  <template #default="{ row }">
                    {{ row.totalMinutes }} 分钟
                  </template>
                </el-table-column>
                <el-table-column prop="taskCount" label="完成任务" width="100" align="right">
                  <template #default="{ row }">
                    {{ row.taskCount }} 个
                  </template>
                </el-table-column>
              </el-table>
            </template>
            <EmptyState v-else :type="emptyMode || 'empty'" @retry="handleRetry">
              <template #description>暂无排行数据</template>
            </EmptyState>
          </div>
        </el-tab-pane>

        <el-tab-pane label="逾期督办" name="overdue">
          <div v-loading="loading" class="tab-content">
            <div class="toolbar">
              <el-button v-perm="'ims:train:stat:export'" type="primary" @click="handleExportOverdue">导出</el-button>
            </div>
            <template v-if="!emptyMode && overdueList.length > 0">
              <el-table :data="overdueList" style="width: 100%">
                <el-table-column prop="userName" label="学员" width="100" />
                <el-table-column prop="deptName" label="部门" width="120" />
                <el-table-column prop="taskName" label="任务名称" min-width="180" show-overflow-tooltip />
                <el-table-column prop="deadline" label="截止时间" width="160" />
                <el-table-column label="逾期天数" width="100" align="right">
                  <template #default="{ row }">
                    <span class="text-danger">{{ row.overduedays }} 天</span>
                  </template>
                </el-table-column>
              </el-table>
              <Pagination v-model:page-no="overduePageNo" v-model:page-size="overduePageSize" :total="overdueTotal" />
            </template>
            <EmptyState v-else :type="emptyMode || 'empty'" @retry="handleRetry">
              <template #description>暂无逾期数据</template>
            </EmptyState>
          </div>
        </el-tab-pane>

        <el-tab-pane label="资料热度" name="heat">
          <div v-loading="loading" class="tab-content">
            <template v-if="!emptyMode && heatList.length > 0">
              <el-table :data="heatList" style="width: 100%">
                <el-table-column type="index" label="排名" width="80" align="center" />
                <el-table-column prop="title" label="资料名称" min-width="200" show-overflow-tooltip />
                <el-table-column prop="materialType" label="类型" width="80">
                  <template #default="{ row }">
                    <el-tag v-if="row.materialType === 'DOC'" type="info" size="small">文档</el-tag>
                    <el-tag v-else-if="row.materialType === 'VIDEO'" type="warning" size="small">视频</el-tag>
                    <el-tag v-else type="success" size="small">外链</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="viewCount" label="浏览次数" width="100" align="right" />
                <el-table-column prop="finishCount" label="完成人次" width="100" align="right" />
              </el-table>
            </template>
            <EmptyState v-else :type="emptyMode || 'empty'" @retry="handleRetry">
              <template #description>暂无热度数据</template>
            </EmptyState>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.stat-dashboard {
  width: 100%;
}

.stat-tabs {
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-m);
  padding: 16px 20px;
}

.tab-content {
  min-height: 400px;
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background-color: var(--bg);
  border-radius: var(--r-s);
  padding: 20px;
  text-align: center;
}

.stat-card-title {
  font-size: 13px;
  color: var(--text2);
  margin-bottom: 8px;
}

.stat-card-value {
  font-size: 32px;
  font-weight: 600;
  color: var(--text1);
  line-height: 1.2;

  &.primary {
    color: var(--primary);
  }

  &.success {
    color: var(--green);
  }

  &.danger {
    color: var(--red);
  }
}

.stat-card-sub {
  font-size: 12px;
  color: var(--text2);
  margin-top: 4px;
}

.section {
  margin-top: 24px;

  h4 {
    margin: 0 0 12px;
    font-size: 14px;
    font-weight: 600;
  }
}

.toolbar {
  margin-bottom: 12px;
}

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
  background-color: var(--bg);
  color: var(--text2);

  &.rank-1 {
    background-color: #ffd700;
    color: #000;
  }

  &.rank-2 {
    background-color: #c0c0c0;
    color: #000;
  }

  &.rank-3 {
    background-color: #cd7f32;
    color: #fff;
  }
}

.text-danger {
  color: var(--red);
}

@media (width <= 768px) {
  .stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
