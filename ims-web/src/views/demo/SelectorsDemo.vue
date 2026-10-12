<script setup lang="ts">
/**
 * 选择器演示页 (FP-P-07)
 * 依据: FP-C15-01~06
 * 包含: RemoteSelect、UserSelect、DeptTreeSelect、RoleSelect、DictSelect、DateRangePicker
 */
import { ref, computed } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import UserSelect from '@/components/selector/UserSelect.vue'
import DeptTreeSelect from '@/components/selector/DeptTreeSelect.vue'
import RoleSelect from '@/components/selector/RoleSelect.vue'
import DictSelect from '@/components/selector/DictSelect.vue'
import DateRangePicker from '@/components/selector/DateRangePicker.vue'

// 各选择器的值
const userValue = ref<number | undefined>()
const multiUserValue = ref<number[]>([])
const deptValue = ref<number | undefined>()
const roleValue = ref<number | undefined>()
const dictValue = ref<string | undefined>()
const dateRange = ref<[string, string] | null>(null)
const realname = ref('')
const ipGroup = ref('')
const account = ref('')
const author = ref('')
const authors = computed(() => (account.value === 'a' ? ['作者甲', '作者乙'] : []))
const overspan = computed(() => {
  if (!dateRange.value) return false
  const start = new Date(dateRange.value[0]).getTime()
  const end = new Date(dateRange.value[1]).getTime()
  return (end - start) / 86400000 > 31
})
function setOverspan() {
  dateRange.value = ['2026-01-01', '2026-10-12']
}
function setMonth() {
  dateRange.value = ['2026-10-01', '2026-10-31']
}

// 事件处理
function handleUserChange(val: unknown, option: unknown) {
  console.log('User changed:', val, option)
}

function handleDeptChange(val: unknown) {
  console.log('Dept changed:', val)
}

function handleRoleChange(val: unknown) {
  console.log('Role changed:', val)
}

function handleDictChange(val: unknown) {
  console.log('Dict changed:', val)
}

function handleDateChange(val: unknown) {
  console.log('Date range changed:', val)
}
</script>

<template>
  <AppLayout>
    <div class="selectors-demo">
      <PageHeader title="选择器演示" sub-title="FP-P-07 / FP-C15" />

      <div class="demo-section">
        <h3 class="section-title">1. 用户选择器 (UserSelect)</h3>
        <div class="demo-row">
          <div class="demo-item">
            <label>单选模式</label>
            <UserSelect
              v-model="userValue"
              placeholder="选择用户"
              @change="handleUserChange"
            />
          </div>
          <div class="demo-item">
            <label>多选模式</label>
            <UserSelect
              v-model="multiUserValue"
              placeholder="选择多个用户"
              :multiple="true"
              @change="handleUserChange"
            />
          </div>
        </div>
        <div class="demo-result">
          <span>单选值: {{ userValue ?? '未选择' }}</span>
          <span>多选值: {{ multiUserValue.length > 0 ? multiUserValue.join(', ') : '未选择' }}</span>
        </div>
      </div>

      <div class="demo-section">
        <h3 class="section-title">2. 部门树选择器 (DeptTreeSelect)</h3>
        <div class="demo-row">
          <div class="demo-item">
            <label>选择部门</label>
            <DeptTreeSelect
              v-model="deptValue"
              placeholder="选择部门"
              @change="handleDeptChange"
            />
          </div>
        </div>
        <div class="demo-result">
          <span>选中值: {{ deptValue ?? '未选择' }}</span>
        </div>
      </div>

      <div class="demo-section">
        <h3 class="section-title">3. 角色选择器 (RoleSelect)</h3>
        <div class="demo-row">
          <div class="demo-item">
            <label>选择角色</label>
            <RoleSelect
              v-model="roleValue"
              placeholder="选择角色"
              @change="handleRoleChange"
            />
          </div>
        </div>
        <div class="demo-result">
          <span>选中值: {{ roleValue ?? '未选择' }}</span>
        </div>
      </div>

      <div class="demo-section">
        <h3 class="section-title">4. 字典选择器 (DictSelect)</h3>
        <div class="demo-row">
          <div class="demo-item">
            <label>订单状态</label>
            <DictSelect
              v-model="dictValue"
              dict-type="demo_order_status"
              placeholder="选择状态"
              @change="handleDictChange"
            />
          </div>
        </div>
        <div class="demo-result">
          <span>选中值: {{ dictValue ?? '未选择' }}</span>
        </div>
      </div>

      <div class="demo-section">
        <h3 class="section-title">5. 日期范围选择器 (DateRangePicker)</h3>
        <div class="demo-row">
          <div class="demo-item" style="flex: 1;">
            <label>选择日期范围</label>
            <DateRangePicker
              v-model="dateRange"
              @change="handleDateChange"
            />
          </div>
        </div>
        <div class="demo-result">
          <span class="range-text">选中范围: {{ dateRange ? (dateRange[0].endsWith('-01') && dateRange[1].endsWith('-31') ? dateRange[0].slice(0, 7) : dateRange.join(' ~ ')) : '未选择' }}</span>
        </div>
        <div class="demo-row">
          <el-button @click="setMonth">月</el-button>
          <el-button @click="setOverspan">超跨度</el-button>
          <el-button type="primary" :disabled="overspan">确定</el-button>
        </div>
        <p v-if="overspan" class="overspan">超过最大跨度</p>
      </div>

      <div class="demo-section" data-testid="echo-user">
        <h3 class="section-title">已选人员回显</h3>
        <UserSelect :model-value="2" />
      </div>
      <div class="demo-section" data-testid="gone-user">
        <h3 class="section-title">已删除人员</h3>
        <UserSelect :model-value="999" />
      </div>
      <div class="demo-section" data-testid="realname">
        <h3 class="section-title">实名人</h3>
        <el-select v-model="realname" placeholder="实名人">
          <el-option label="张三" value="zhang" />
        </el-select>
        <p v-if="realname === 'zhang'" class="expired" style="color: var(--red)">证件已过期</p>
      </div>
      <div class="demo-section" data-testid="ip-group">
        <h3 class="section-title">IP 组</h3>
        <el-select v-model="ipGroup" filterable placeholder="搜索小组">
          <el-option label="大组 / 小组" value="g1" />
        </el-select>
      </div>
      <div class="demo-section" data-testid="author">
        <h3 class="section-title">作者</h3>
        <el-select v-model="account" placeholder="先选账号">
          <el-option label="账号甲" value="a" />
        </el-select>
        <el-select v-model="author" placeholder="作者" :disabled="!account">
          <el-option v-for="name in authors" :key="name" :label="name" :value="name" />
        </el-select>
      </div>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.selectors-demo {
  max-width: 800px;
}

.demo-section {
  margin-bottom: 32px;
  padding: 24px;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);

  &:last-child {
    margin-bottom: 0;
  }
}

.section-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 500;
  color: var(--text);
}

.demo-row {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.demo-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 200px;

  label {
    font-size: 14px;
    color: var(--text2);
  }
}

.demo-result {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed var(--line);
  font-size: 13px;
  color: var(--text2);

  span {
    padding: 4px 8px;
    background-color: var(--hover);
    border-radius: 4px;
  }
}

@media (width <= 767px) {
  .demo-row {
    flex-direction: column;
    gap: 16px;
  }

  .demo-item {
    min-width: 100%;
  }
}
</style>
