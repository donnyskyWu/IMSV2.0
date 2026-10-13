<script setup lang="ts">
/**
 * 留痕率统计页 (B18-M18 ST-01)
 * 依据: 01-功能点清单.md, 会议-实现理解.md §3.9
 */
import { ref, computed, onMounted } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import { toast } from '@/utils/toast'
import { useAuthStore } from '@/stores/auth'
import { fmtDateTime } from '@/utils/format'

interface UnarchivedMinutes {
  minutes_no: string
  meeting_title: string
  meeting_date: string
  recorder_name: string
  hours_since_meeting: number
}

interface ArchiveRateData {
  total_meetings: number
  archived_count: number
  archive_rate: number
  unarchived_list: UnarchivedMinutes[]
}

const authStore = useAuthStore()
const loading = ref(false)
const data = ref<ArchiveRateData | null>(null)
const dateRange = ref<[string, string] | null>(null)

const canSupervise = computed(() => authStore.hasPerm('ims:meet:minutes:supervise'))

async function fetchData() {
  if (!canSupervise.value) {
    toast.error('暂无权限')
    return
  }

  loading.value = true
  try {
    const params = new URLSearchParams()
    if (dateRange.value) {
      params.append('date_range_start', dateRange.value[0])
      params.append('date_range_end', dateRange.value[1])
    }

    const response = await fetch(`/admin-api/ims/meet/minutes/archive-rate?${params}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('ims_access_token')}` },
    })
    const result = await response.json()
    if (result.code === 0) {
      data.value = result.data
    } else {
      toast.error(result.msg || '加载失败')
    }
  } catch {
    toast.error('网络异常，请检查网络后重试')
  } finally {
    loading.value = false
  }
}

function getHoursClass(hours: number): string {
  if (hours > 48) return 'hours-danger'
  if (hours > 24) return 'hours-warning'
  return ''
}

onMounted(() => {
  if (canSupervise.value) {
    fetchData()
  }
})
</script>

<template>
  <AppLayout>
    <div class="archive-rate">
      <PageHeader title="留痕率统计" />

      <template v-if="!canSupervise">
        <el-empty description="暂无权限查看此内容" />
      </template>

      <template v-else>
        <div class="filter-bar">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="fetchData"
          />
        </div>

        <div v-loading="loading" class="stats-cards">
          <el-row :gutter="20">
            <el-col :xs="24" :sm="8">
              <el-card shadow="hover">
                <div class="stat-item">
                  <div class="stat-label">会议总数</div>
                  <div class="stat-value">{{ data?.total_meetings ?? 0 }}</div>
                </div>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="8">
              <el-card shadow="hover">
                <div class="stat-item">
                  <div class="stat-label">已归档数</div>
                  <div class="stat-value">{{ data?.archived_count ?? 0 }}</div>
                </div>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="8">
              <el-card shadow="hover">
                <div class="stat-item">
                  <div class="stat-label">留痕率</div>
                  <div class="stat-value rate" :class="{ low: (data?.archive_rate ?? 100) < 80 }">
                    {{ data?.archive_rate ?? 100 }}%
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>

        <div v-if="data && data.unarchived_list.length > 0" class="unarchived-section">
          <h3>未归档会议清单</h3>
          <el-table :data="data.unarchived_list" stripe>
            <el-table-column prop="minutes_no" label="编号" width="150" />
            <el-table-column prop="meeting_title" label="会议主题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="meeting_date" label="会议时间" width="160">
              <template #default="{ row }">{{ fmtDateTime(row.meeting_date) }}</template>
            </el-table-column>
            <el-table-column prop="recorder_name" label="记录人" width="100" />
            <el-table-column label="距今" width="120">
              <template #default="{ row }">
                <span :class="getHoursClass(row.hours_since_meeting)">
                  {{ row.hours_since_meeting }}h
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </div>
  </AppLayout>
</template>

<style scoped>
.archive-rate {
  padding: var(--space-m);
}

.filter-bar {
  margin-bottom: var(--space-m);
}

.stats-cards {
  margin-bottom: var(--space-l);
}

.stat-item {
  text-align: center;
  padding: var(--space-m);
}

.stat-label {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-s);
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: var(--color-primary);
}

.stat-value.rate {
  color: var(--color-success);
}

.stat-value.rate.low {
  color: var(--color-danger);
}

.unarchived-section {
  margin-top: var(--space-l);
}

.unarchived-section h3 {
  margin-bottom: var(--space-m);
  font-size: 16px;
  font-weight: 500;
}

.hours-warning {
  color: var(--color-warning);
  font-weight: 500;
}

.hours-danger {
  color: var(--color-danger);
  font-weight: 500;
}
</style>
