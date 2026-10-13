<script setup lang="ts">
/**
 * 个人中心（FP-B2-PC-01～04）
 * 线框：AppLayout 内，PageHeader + Tabs。
 * 基本信息用 DescriptionList，手机用 MaskedText，会话用 DataTable。
 */
import { computed, onMounted, ref } from 'vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import Tabs from '@/components/layout/Tabs.vue'
import DescriptionList from '@/components/display/DescriptionList.vue'
import PasswordForm from './PasswordForm.vue'
import SetPasswordForm from './SetPasswordForm.vue'
import SessionList from './SessionList.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const active = ref('info')

const profile = computed(() => authStore.user)
const hasPassword = computed(() => profile.value?.hasPassword !== false)
const tabs = computed(() => [
  { key: 'info', label: '基本信息' },
  { key: 'password', label: hasPassword.value ? '修改密码' : '设置密码' },
  { key: 'sessions', label: '我的会话' },
])
const infoItems = computed(() => {
  const user = profile.value
  const depts = user?.deptNames?.filter(Boolean) || []
  return [
    { label: '姓名', value: user?.nickname || '' },
    { label: '用户名', value: user?.username || '' },
    { label: '手机', value: user?.mobileMasked || '', type: 'masked' as const },
    { label: '主部门', value: user?.deptName || '' },
    { label: '所属部门', value: depts.join('、') },
    { label: '岗位', value: user?.positionLabel || '' },
    { label: '角色', value: (user?.roleNames || []).join('、') },
    { label: '数据范围', value: user?.dataScopeText || '' },
  ]
})

onMounted(() => {
  authStore.fetchUserInfo().catch(() => {
    // 令牌失效由请求层处理。
  })
})
</script>

<template>
  <section class="profile-page" data-testid="profile-page">
    <PageHeader title="个人中心" :show-scope="false" />
    <Tabs v-model:active="active" :items="tabs" />
    <div v-if="active === 'info'" data-testid="profile-info">
      <DescriptionList :items="infoItems" :columns="2" />
    </div>
    <PasswordForm v-else-if="active === 'password' && hasPassword" />
    <SetPasswordForm v-else-if="active === 'password'" />
    <SessionList v-else />
  </section>
</template>

<style lang="scss" scoped>
.profile-page {
  padding: 16px 20px 32px;
}
</style>
