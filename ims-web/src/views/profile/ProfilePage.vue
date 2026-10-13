<script setup lang="ts">
/**
 * 个人中心（FP-B2-PC-01～04）
 * 留在 AppLayout 内。基本信息只读。
 */
import { computed, onMounted } from 'vue'
import PasswordForm from './PasswordForm.vue'
import SetPasswordForm from './SetPasswordForm.vue'
import SessionList from './SessionList.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const profile = computed(() => authStore.user)
const hasPassword = computed(() => profile.value?.hasPassword !== false)

onMounted(() => {
  authStore.fetchUserInfo().catch(() => {
    // 令牌失效由请求层处理。
  })
})
</script>

<template>
  <section class="profile-page" data-testid="profile-page">
    <h1>个人中心</h1>
    <el-tabs>
      <el-tab-pane label="基本信息">
        <dl class="profile-info" data-testid="profile-info">
          <div><dt>用户名</dt><dd>{{ profile?.username }}</dd></div>
          <div><dt>姓名</dt><dd>{{ profile?.nickname }}</dd></div>
          <div><dt>部门</dt><dd>{{ profile?.deptName }}</dd></div>
          <div><dt>岗位</dt><dd>{{ profile?.positionLabel || '' }}</dd></div>
          <div><dt>角色</dt><dd>{{ (profile?.roleNames || []).join('、') }}</dd></div>
          <div><dt>手机</dt><dd data-testid="mobile-masked">{{ profile?.mobileMasked || '' }}</dd></div>
          <div><dt>数据范围</dt><dd>{{ profile?.dataScopeText }}</dd></div>
        </dl>
      </el-tab-pane>
      <el-tab-pane :label="hasPassword ? '修改密码' : '设置密码'">
        <PasswordForm v-if="hasPassword" />
        <SetPasswordForm v-else />
      </el-tab-pane>
      <el-tab-pane label="我的会话">
        <SessionList />
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<style lang="scss" scoped>
.profile-page {
  padding: 16px 20px 32px;
}

h1 {
  margin: 0 0 12px;
  font-size: 20px;
}

.profile-info {
  margin: 0;
  display: grid;
  gap: 8px;
}

.profile-info div {
  display: grid;
  grid-template-columns: 96px 1fr;
  gap: 8px;
}

dt {
  color: var(--text2);
}

dd {
  margin: 0;
}
</style>
