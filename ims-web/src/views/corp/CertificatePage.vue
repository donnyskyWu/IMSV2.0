<script setup lang="ts">
/**
 * 证件档案、到期预警、分级与审计。版本 v1.0 · 2026-10-13
 * 原图走签名地址，页面不提供下载。
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import CertPreview from '@/components/file/CertPreview.vue'
import RealNameSelect from '@/components/selector/RealNameSelect.vue'
import { useAuthStore } from '@/stores/auth'
import { ApiError } from '@/api/request'
import {
  deleteCert,
  digitalMetrics,
  expireStats,
  getLevelConfig,
  listCerts,
  listExpireTasks,
  listViewLogs,
  recognizeCert,
  remindExpire,
  reviewCert,
  riskReport,
  saveLevelConfig,
  scanExpire,
  uploadCert,
  viewCert,
  type CertRow,
} from '@/api/resource'

const auth = useAuthStore()
const route = useRoute()
const tab = ref('archive')
const rows = ref<CertRow[]>([])
const rate = ref('')
const rateLow = computed(() => rate.value !== '' && Number(rate.value) < 95)
const formOpen = ref(false)
const errors = ref<string[]>([])
const ocrHint = ref('')
const preview = reactive({ open: false, watermarkText: '', certNo: '', previewUrl: '' })
const stats = ref({ YELLOW: 0, RED: 0, LOCKED: 0 })
const tasks = ref<Array<Record<string, string>>>([])
const logs = ref<Array<Record<string, string>>>([])
const risks = ref<Array<{ name?: string; userId: string; count: number }>>([])
const viewer = ref('')
const levelRole = ref('测试-资源只读')
const levelValue = ref(2)
const form = reactive({
  holderType: 'REALNAME',
  realnameId: '',
  holderName: '',
  certType: '',
  certNo: '',
  issueDate: '',
  expireDate: '',
  fileName: '',
})

const showExpire = computed(() => auth.hasPerm('ims:cert:expire:query'))
const showSecurity = computed(() => auth.hasPerm('ims:cert:security:audit') || auth.hasPerm('ims:cert:security:config'))
const canConfig = computed(() => auth.hasPerm('ims:cert:security:config'))
const holderFilter = computed(() => String(route.query.holder || ''))

const visibleRows = computed(() => {
  if (!holderFilter.value) return rows.value
  return rows.value.filter((item) => item.realnameId === holderFilter.value)
})

function statusText(row: CertRow) {
  if (row.statusLabel) return row.statusLabel
  if (row.warnLevel === 'LOCKED' || row.status === 'EXPIRED') return '已过期-锁定'
  if (row.status === 'PENDING_REVIEW') return '待审'
  if (row.status === 'EFFECTIVE') return '生效'
  if (row.status === 'REJECTED') return '已拒绝'
  if (row.status === 'RECYCLED') return '已归档'
  return row.status
}

async function loadArchive() {
  const page = await listCerts()
  rows.value = page.list || []
  if (auth.hasPerm('ims:cert:archive:query')) {
    const metrics = await digitalMetrics()
    rate.value = metrics.rate
  }
}

async function loadExpire() {
  stats.value = await expireStats()
  const page = await listExpireTasks()
  tasks.value = (page.list || []) as Array<Record<string, string>>
}

async function loadSecurity() {
  if (auth.hasPerm('ims:cert:security:audit')) {
    const page = await listViewLogs(viewer.value)
    logs.value = page.list || []
    const report = await riskReport()
    risks.value = report.users || []
  }
  if (canConfig.value) await getLevelConfig()
}

function openUpload() {
  form.holderType = 'REALNAME'
  form.realnameId = ''
  form.holderName = ''
  form.certType = ''
  form.certNo = ''
  form.issueDate = ''
  form.expireDate = ''
  form.fileName = ''
  errors.value = []
  ocrHint.value = ''
  formOpen.value = true
}

function onFile(event: Event) {
  const input = event.target as { files?: ArrayLike<{ name: string }> | null }
  form.fileName = input.files?.[0]?.name || ''
}

async function recognize() {
  try {
    const found = await recognizeCert(form.fileName || 'sample.png')
    if (!found.recognized) {
      ocrHint.value = ''
      ElMessage.warning('识别失败，请手工填写')
      return
    }
    form.holderName = found.name || form.holderName
    form.certNo = found.certNo || ''
    form.issueDate = found.issueDate || ''
    form.expireDate = found.expireDate || ''
    ocrHint.value = '识别结果，请核对'
  } catch {
    ElMessage.warning('识别失败，请手工填写')
  }
}

async function submitUpload() {
  errors.value = []
  const missing = !form.certType || !form.certNo || !form.issueDate || !form.expireDate || !form.fileName
    || (form.holderType === 'REALNAME' && !form.realnameId)
    || (form.holderType === 'EXTERNAL' && !form.holderName.trim())
  if (missing) {
    errors.value.push('持有人、类型、证件号、签发日期、有效期至、扫描件必填')
    return
  }
  if (form.certType === 'ID_CARD' && form.certNo.length < 18) {
    ElMessage.error('身份证号不合法')
    return
  }
  if (form.expireDate < form.issueDate) {
    ElMessage.error('有效期须晚于签发日期')
    return
  }
  try {
    await uploadCert({ ...form })
    formOpen.value = false
    await loadArchive()
  } catch (err) {
    if (err instanceof ApiError && err.code === 1032) {
      await ElMessageBox.confirm('已存在有效档案，如为新证请走换证流程', '提示', { confirmButtonText: '去换证' })
      tab.value = 'expire'
      return
    }
    if (err instanceof ApiError) ElMessage.error(err.message)
  }
}

function canReview(row: CertRow) {
  return auth.hasPerm('ims:cert:archive:review') && row.creatorId !== auth.user?.id && row.status === 'PENDING_REVIEW'
}

async function review(row: CertRow, passed: boolean) {
  let remark = ''
  if (!passed) {
    try {
      const result = await ElMessageBox.prompt('拒绝原因', '拒绝')
      remark = result.value || ''
    } catch {
      return
    }
    if (!remark.trim()) {
      ElMessage.error('原因必填')
      return
    }
  }
  await reviewCert(row.id, passed, remark)
  await loadArchive()
}

async function openView(row: CertRow) {
  try {
    const data = await viewCert(row.id)
    preview.watermarkText = data.watermarkText
    preview.certNo = data.certNo
    preview.previewUrl = data.previewUrl
    preview.open = true
  } catch {
    // 1034 / 1035 由请求层弹出一次。
  }
}

async function remove(row: CertRow) {
  try {
    await deleteCert(row.id)
    await loadArchive()
  } catch {
    // 锁定删除的 1502 由请求层弹出一次。
  }
}

async function scan() {
  await ElMessageBox.confirm('确认手动扫描', '扫描')
  await scanExpire()
  await loadExpire()
}

async function remind(taskId: string) {
  const result = await remindExpire(taskId)
  ElMessage.success(result.reminded ? `已催办 ${result.remindCount}` : '10 分钟内不再发消息')
}

async function saveLevel() {
  await saveLevelConfig({ rules: [{ roleName: levelRole.value, viewLevel: levelValue.value }] })
  ElMessage.success('下次查看即按新级别')
}

onMounted(async () => {
  await loadArchive()
  if (showExpire.value) await loadExpire()
  if (showSecurity.value) await loadSecurity()
})
</script>

<template>
  <div data-testid="cert-page">
      <header class="page-head">
        <h1>证件管理</h1>
        <el-button v-perm="'ims:cert:archive:upload'" type="primary" @click="openUpload">上传证件</el-button>
      </header>
      <p v-if="rate" class="rate" :class="{ low: rateLow }" data-testid="digital-rate">
        数字化率 {{ rate }}%
        <el-button link>查看统计</el-button>
      </p>
      <el-tabs v-model="tab">
        <el-tab-pane label="档案" name="archive">
          <el-table :data="visibleRows">
            <el-table-column prop="holderName" label="持有人">
              <template #default="{ row }">
                {{ row.holderName }}
                <el-tag v-if="row.external" type="info">外协</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="certTypeLabel" label="类型" />
            <el-table-column prop="certNo" label="证件号" />
            <el-table-column label="状态">
              <template #default="{ row }">
                <span :class="row.warnLevel">{{ statusText(row) }}</span>
                <span v-if="row.daysLeft != null">剩余 {{ row.daysLeft }} 天</span>
              </template>
            </el-table-column>
            <el-table-column label="操作">
              <template #default="{ row }">
                <el-button v-if="canReview(row)" link @click="review(row, true)">审核</el-button>
                <el-button v-if="canReview(row)" link @click="review(row, false)">拒绝</el-button>
                <el-button link @click="openView(row)">查看原图</el-button>
                <el-button v-perm="'ims:cert:archive:delete'" link @click="remove(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane v-if="showExpire" label="到期预警" name="expire">
          <p data-testid="expire-stats">黄 {{ stats.YELLOW }} 红 {{ stats.RED }} 锁定 {{ stats.LOCKED }}</p>
          <el-button v-perm="'ims:cert:expire:scan'" @click="scan">手动扫描</el-button>
          <el-table :data="tasks">
            <el-table-column prop="certName" label="证件" />
            <el-table-column prop="level" label="级别" />
            <el-table-column prop="status" label="状态" />
            <el-table-column label="操作">
              <template #default="{ row }">
                <el-button v-perm="'ims:cert:expire:remind'" link @click="remind(String(row.id))">催办</el-button>
                <el-button v-perm="'ims:cert:expire:renew'" link @click="tab = 'archive'">换证</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane v-if="showSecurity" label="分级与审计" name="security">
          <div v-if="canConfig" data-testid="level-config">
            <el-input v-model="levelRole" placeholder="角色" />
            <el-input v-model.number="levelValue" placeholder="级别" />
            <el-button @click="saveLevel">保存级别</el-button>
          </div>
          <div v-perm="'ims:cert:security:audit'">
            <el-input v-model="viewer" placeholder="查看人" />
            <el-button @click="loadSecurity">筛选</el-button>
            <el-table :data="logs">
              <el-table-column prop="viewerName" label="查看人" />
              <el-table-column prop="result" label="结果" />
              <el-table-column label="时长">
                <template #default>—</template>
              </el-table-column>
            </el-table>
            <p v-for="item in risks" :key="item.userId">风险 {{ item.name || item.userId }} {{ item.count }}</p>
          </div>
        </el-tab-pane>
      </el-tabs>

      <el-drawer v-model="formOpen" title="上传证件">
        <p v-for="item in errors" :key="item">{{ item }}</p>
        <p v-if="ocrHint">{{ ocrHint }}</p>
        <el-radio-group v-model="form.holderType">
          <el-radio value="REALNAME">实名人</el-radio>
          <el-radio value="USER">员工</el-radio>
          <el-radio value="EXTERNAL">外协</el-radio>
        </el-radio-group>
        <RealNameSelect v-if="form.holderType === 'REALNAME'" v-model="form.realnameId" />
        <el-input v-if="form.holderType === 'EXTERNAL'" v-model="form.holderName" placeholder="外协姓名" />
        <el-select v-model="form.certType" placeholder="证件类型">
          <el-option label="居民身份证" value="ID_CARD" />
          <el-option label="护照" value="PASSPORT" />
          <el-option label="健康证" value="HEALTH" />
        </el-select>
        <el-input v-model="form.certNo" placeholder="证件号" />
        <el-input v-model="form.issueDate" placeholder="签发日期" />
        <el-input v-model="form.expireDate" placeholder="有效期至" />
        <input type="file" aria-label="扫描件" @change="onFile">
        <el-button v-if="form.fileName" @click="recognize">识别</el-button>
        <el-button type="primary" @click="submitUpload">提交</el-button>
      </el-drawer>
      <CertPreview
        :open="preview.open"
        :watermark-text="preview.watermarkText"
        :cert-no="preview.certNo"
        :preview-url="preview.previewUrl"
        @close="preview.open = false"
      />
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.rate.low {
  color: var(--el-color-danger);
}

.RED {
  color: var(--el-color-danger);
}

.YELLOW {
  color: var(--el-color-warning);
}
</style>
