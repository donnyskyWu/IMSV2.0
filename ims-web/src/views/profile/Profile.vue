<script setup lang="ts">
/** 个人中心（FP-B2-PC）。无菜单二级页。 */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import { ApiError } from '@/api/request'
import { changePassword } from '@/api/password'
import { systemAdminApi } from '@/api/system-admin'
import { PASSWORD_COPY, validatePasswordChange } from '@/utils/password-rules'
import { toast } from '@/utils/toast'

const tab = ref<'info' | 'password' | 'sessions'>('info')
const profile = ref<Record<string, unknown>>({})
const sessions = ref<Record<string, unknown>[]>([])
const hasPassword = ref(true)
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const error = ref('')

async function load() {
  const me = await systemAdminApi.me()
  const user = (me.user || {}) as Record<string, unknown>
  profile.value = {
    ...user,
    dataScopeText: me.dataScopeText,
  }
  hasPassword.value = user.hasPassword !== false
  const sessionPage = await systemAdminApi.mySessions()
  sessions.value = sessionPage.list || []
}

async function submitPassword() {
  error.value = ''
  if (!hasPassword.value) {
    try {
      await systemAdminApi.setPassword(newPassword.value)
      toast.success('密码已设置')
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : '保存失败'
    }
    return
  }
  const errors = validatePasswordChange({
    oldPassword: oldPassword.value,
    newPassword: newPassword.value,
    confirmPassword: confirmPassword.value,
  })
  if (errors.oldPassword || errors.newPassword || errors.confirmPassword) {
    error.value = errors.oldPassword || errors.newPassword || errors.confirmPassword || ''
    return
  }
  try {
    await changePassword({ oldPassword: oldPassword.value, newPassword: newPassword.value })
    toast.success(PASSWORD_COPY.updated)
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '保存失败'
  }
}

async function kick(sid: string) {
  await systemAdminApi.deleteSession(sid)
  toast.success('已下线')
  await load()
}

onMounted(load)
</script>

<template>
  <div data-testid="page-profile">
    <PageHeader title="个人中心" :show-scope="false" />
    <div class="tabs">
      <button type="button" data-testid="tab-info" @click="tab = 'info'">基本信息</button>
      <button type="button" data-testid="tab-password" @click="tab = 'password'">{{ hasPassword ? '修改密码' : '设置密码' }}</button>
      <button type="button" data-testid="tab-sessions" @click="tab = 'sessions'">我的会话</button>
    </div>
    <section v-if="tab === 'info'" data-testid="profile-info">
      <p>姓名 {{ profile.nickname }}</p>
      <p>用户名 {{ profile.username }}</p>
      <p data-testid="profile-mobile">手机 {{ profile.mobileMasked || '—' }}</p>
      <p>部门 {{ profile.mainDeptName }}</p>
      <p>数据范围 {{ profile.dataScopeText }}</p>
    </section>
    <section v-else-if="tab === 'password'">
      <p v-if="error" class="error" data-testid="password-error">{{ error }}</p>
      <label v-if="hasPassword">当前密码<input v-model="oldPassword" data-testid="field-old-password" type="password" /></label>
      <label>新密码<input v-model="newPassword" data-testid="field-new-password" type="password" /></label>
      <label v-if="hasPassword">确认新密码<input v-model="confirmPassword" data-testid="field-confirm-password" type="password" /></label>
      <el-button data-testid="btn-save-password" @click="submitPassword">保存</el-button>
    </section>
    <section v-else>
      <article v-for="item in sessions" :key="String(item.sid)" data-testid="session-row">
        <span>{{ item.loginTime }} {{ item.ip }} {{ item.current ? '当前' : '' }}</span>
        <button v-if="!item.current" type="button" data-testid="btn-session-kick" @click="kick(String(item.sid))">下线</button>
      </article>
    </section>
  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.error {
  color: var(--danger, #c45656);
}

label {
  display: block;
  margin: 8px 0;
}
</style>
