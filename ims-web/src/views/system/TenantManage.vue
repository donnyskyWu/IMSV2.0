<script setup lang="ts">
/** 租户套餐（FP-B2-T） */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import PlainTable from '@/components/list/PlainTable.vue'
import { systemAdminApi } from '@/api/system-admin'
import { toast } from '@/utils/toast'
import type { TableColumn } from '@/types'

const tab = ref<'tenant' | 'package'>('tenant')
const tenants = ref<Record<string, unknown>[]>([])
const packages = ref<Record<string, unknown>[]>([])
const tempPassword = ref('')
const form = ref({
  name: '',
  contactName: '',
  contactMobile: '',
  packageId: '',
  expireTime: '',
  adminUsername: '',
})

const tenantColumns: TableColumn[] = [
  { key: 'id', label: '租户 ID' },
  { key: 'name', label: '名称' },
  { key: 'packageName', label: '套餐' },
  { key: 'contactName', label: '联系人' },
  { key: 'expireTime', label: '过期时间' },
  { key: 'statusText', label: '状态' },
  { key: 'actions', label: '操作' },
]
const packageColumns: TableColumn[] = [
  { key: 'name', label: '名称' },
  { key: 'menuCount', label: '菜单数' },
  { key: 'tenantCount', label: '租户数' },
  { key: 'statusText', label: '状态' },
]

async function load() {
  const page = await systemAdminApi.tenantPage({ pageNo: 1, pageSize: 20 })
  tenants.value = (page.list || []).map((row) => ({
    ...row,
    statusText: row.status === 'DISABLED' ? '停用' : '启用',
  }))
  packages.value = (await systemAdminApi.packageList()) || []
}

async function createTenant() {
  const result = await systemAdminApi.tenantCreate(form.value)
  tempPassword.value = result.data?.tempPassword || ''
  toast.success('租户已创建')
  await load()
}

async function createPackage() {
  await systemAdminApi.packageCreate({ name: '测试只读包', menuIds: ['dict'] })
  toast.success('套餐已创建')
  await load()
}

async function assign(row: Record<string, unknown>) {
  await systemAdminApi.tenantUpdate(String(row.id), { packageId: form.value.packageId || 'pkg-user' })
  toast.success('套餐已分配')
}

async function disable(row: Record<string, unknown>) {
  await systemAdminApi.tenantUpdate(String(row.id), { status: 'DISABLED' })
  toast.success('租户已停用')
  await load()
}

onMounted(load)
</script>

<template>
  <div data-testid="page-tenant">
    <PageHeader title="租户套餐" />
    <button type="button" data-testid="tab-tenant" @click="tab = 'tenant'">租户</button>
    <button type="button" data-testid="tab-package" @click="tab = 'package'">套餐</button>
    <div v-if="tab === 'tenant'">
      <input v-model="form.name" data-testid="field-tenant-name" placeholder="名称" />
      <input v-model="form.contactName" data-testid="field-tenant-contact" placeholder="联系人" />
      <input v-model="form.contactMobile" data-testid="field-tenant-mobile" placeholder="联系手机" />
      <input v-model="form.packageId" data-testid="field-tenant-package" placeholder="套餐" />
      <input v-model="form.expireTime" data-testid="field-tenant-expire" placeholder="过期时间" />
      <input v-model="form.adminUsername" data-testid="field-tenant-admin" placeholder="初始管理员" />
      <el-button data-testid="btn-tenant-create" @click="createTenant">新建租户</el-button>
      <p v-if="tempPassword" data-testid="tenant-temp-password">{{ tempPassword }}</p>
      <PlainTable :columns="tenantColumns" :data="tenants">
        <template #cell-actions="{ row }">
          <el-button data-testid="btn-assign-package" @click="assign(row)">分配套餐</el-button>
          <el-button data-testid="btn-tenant-disable" @click="disable(row)">停用</el-button>
        </template>
      </PlainTable>
    </div>
    <div v-else>
      <el-button data-testid="btn-package-create" @click="createPackage">新建套餐</el-button>
      <PlainTable :columns="packageColumns" :data="packages" />
    </div>
  </div>
</template>
