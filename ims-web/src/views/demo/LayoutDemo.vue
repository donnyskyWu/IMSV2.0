<script setup lang="ts">
/**
 * 布局演示页 (FP-P-03)
 * 依据: 00-工作包 §2.3 U3
 * 包含:
 * - AppLayout、PageHeader、Tabs、Breadcrumb、PermissionGate
 * - 页头按钮三组配置切换 (A/B/C) 供 VC-M-31 使用
 * - 一个故意写错格式的权限码 供 VC-M-35 使用
 */
import { ref, watch } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import Tabs from '@/components/layout/Tabs.vue'
import EmptyState from '@/components/list/EmptyState.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// 页头按钮配置切换 (§2.3 U3)
// A: 1 个 primary + 2 个普通
// B: 2 个 primary + 1 个普通
// C: 没有 primary，3 个普通
type ButtonConfig = 'A' | 'B' | 'C'
const buttonConfig = ref<ButtonConfig>('A')

const buttonConfigOptions = [
  { key: 'A', label: 'A: 1主 + 2普通' },
  { key: 'B', label: 'B: 2主 + 1普通' },
  { key: 'C', label: 'C: 0主 + 3普通' },
]

// Tab 配置
const activeTab = ref(sessionStorage.getItem('ims_layout_tab') || 'tab1')
watch(activeTab, (value) => sessionStorage.setItem('ims_layout_tab', value))
const tabItems = [
  { key: 'tab1', label: '标签一', count: 10 },
  { key: 'tab2', label: '标签二', count: 5 },
  { key: 'tab3', label: '标签三', count: 0 },
]

const breadcrumbExpanded = ref(false)

// 面包屑路径 (7 层)
const breadcrumbPath = [
  { label: '首页', value: '/' },
  { label: '系统管理', value: '/system' },
  { label: '组织架构', value: '/system/org' },
  { label: '部门管理', value: '/system/org/dept' },
  { label: '市场部', value: '/system/org/dept/1' },
  { label: '市场一组', value: '/system/org/dept/1/1' },
  { label: '详情', value: '/system/org/dept/1/1/detail' },
]

// 模拟操作
function handleAction(name: string) {
  console.log('Action:', name)
}
</script>

<template>
  <AppLayout>
    <div class="layout-demo">
      <!-- 页头按钮配置切换器 (§2.3 U3) -->
      <div class="config-switcher">
        <span class="switcher-label">页头按钮配置 (VC-M-31):</span>
        <el-radio-group v-model="buttonConfig" size="small">
          <el-radio-button
            v-for="opt in buttonConfigOptions"
            :key="opt.key"
            :value="opt.key"
          >
            {{ opt.label }}
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 页头 -->
      <PageHeader title="布局演示" sub-title="FP-P-03" :show-scope="true">
        <template #actions>
          <!-- 配置 A: 1 个 primary + 2 个普通 -->
          <template v-if="buttonConfig === 'A'">
            <el-button type="primary" @click="handleAction('新建')">新建</el-button>
            <el-button @click="handleAction('导入')">导入</el-button>
            <el-button @click="handleAction('导出')">导出</el-button>
          </template>

          <!-- 配置 B: 2 个 primary + 1 个普通 -->
          <template v-else-if="buttonConfig === 'B'">
            <el-button type="primary" @click="handleAction('提交')">提交</el-button>
            <el-button type="primary" @click="handleAction('审批')">审批</el-button>
            <el-button @click="handleAction('取消')">取消</el-button>
          </template>

          <!-- 配置 C: 没有 primary，3 个普通 -->
          <template v-else>
            <el-button @click="handleAction('操作一')">操作一</el-button>
            <el-button @click="handleAction('操作二')">操作二</el-button>
            <el-button @click="handleAction('操作三')">操作三</el-button>
          </template>
        </template>

        <!-- 手机端主按钮插槽 -->
        <template #primary-action>
          <template v-if="buttonConfig === 'A'">
            <el-button type="primary" @click="handleAction('新建')">新建</el-button>
          </template>
          <template v-else-if="buttonConfig === 'B'">
            <el-button type="primary" @click="handleAction('提交')">提交</el-button>
          </template>
          <!-- 配置 C 无 primary，手机端只显示"更多" -->
        </template>
      </PageHeader>

      <!-- 面包屑 (7层，中间会折叠) -->
      <section class="demo-section">
        <h3>面包屑导航 (7层)</h3>
        <div class="breadcrumb-demo">
          <el-breadcrumb v-if="breadcrumbExpanded" separator="/">
            <el-breadcrumb-item v-for="(item, index) in breadcrumbPath" :key="index">
              {{ item.label }}
            </el-breadcrumb-item>
          </el-breadcrumb>
          <el-breadcrumb v-else separator="/">
            <el-breadcrumb-item>{{ breadcrumbPath[0].label }}</el-breadcrumb-item>
            <el-breadcrumb-item>
              <button type="button" class="crumb-ellipsis" @click="breadcrumbExpanded = true">…</button>
            </el-breadcrumb-item>
            <el-breadcrumb-item>{{ breadcrumbPath[breadcrumbPath.length - 1].label }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
      </section>

      <!-- Tab 组件 -->
      <section class="demo-section">
        <h3>Tab 组件</h3>
        <div class="tabs-demo">
          <h4>下划线 Tab</h4>
          <Tabs v-model:active="activeTab" :items="tabItems" type="line" />

          <h4>胶囊 Tab</h4>
          <Tabs v-model:active="activeTab" :items="tabItems" type="pill" />
        </div>
      </section>

      <!-- 权限对照 (有权/无权按钮) -->
      <section class="demo-section">
        <h3>权限对照 (v-perm 指令)</h3>
        <div class="perm-demo">
          <p class="perm-note">
            当前用户权限码: {{ authStore.permCodes.join(', ') || '无' }}
          </p>

          <div class="perm-buttons">
            <!-- 有权限的按钮 -->
            <el-button
              v-perm="'ims:demo:order:create'"
              type="primary"
            >
              新建 (有权限)
            </el-button>

            <el-button v-perm="'ims:demo:order:delete'" type="danger">
              删除 (有权限)
            </el-button>

            <!-- 无权限的按钮 (不会显示) -->
            <el-button v-perm="'ims:system:admin:super'" type="danger">
              超级管理 (无权限，不显示)
            </el-button>

            <!-- §2.3 U3 & §2.2 #9: 故意写错格式的权限码 (用于 VC-M-35) -->
            <!-- test 构建中权限码格式错误降级为 console.warn，不算冒烟失败 -->
            <el-button v-perm="'bad-code'" type="warning">
              错误权限码 (VC-M-35)
            </el-button>
          </div>

          <p class="perm-hint">
            注意: 上面有一个故意写错格式的权限码 "bad-code"，
            控制台会显示 warning（不是 error），用于验证 VC-M-35
          </p>
        </div>
      </section>

      <!-- 空态展示 -->
      <section class="demo-section">
        <h3>空态组件</h3>
        <div class="empty-demo">
          <div class="empty-item">
            <h4>暂无数据</h4>
            <EmptyState type="empty" />
          </div>
          <div class="empty-item">
            <h4>无权限</h4>
            <EmptyState type="noPermission" />
          </div>
          <div class="empty-item">
            <h4>加载失败</h4>
            <EmptyState type="error" @retry="handleAction('retry')" />
          </div>
        </div>
      </section>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.layout-demo {
  max-width: 1000px;
}

.config-switcher {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);

  .switcher-label {
    font-size: 13px;
    color: var(--text2);
    flex-shrink: 0;
  }
}

.demo-section {
  margin-bottom: 32px;

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 12px;
  }

  h4 {
    font-size: 14px;
    font-weight: 500;
    color: var(--text2);
    margin: 16px 0 8px;

    &:first-child {
      margin-top: 0;
    }
  }
}

.breadcrumb-demo {
  padding: 16px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
}

.tabs-demo {
  padding: 16px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
}

.perm-demo {
  padding: 16px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);

  .perm-note {
    font-size: 13px;
    color: var(--text2);
    margin-bottom: 16px;
  }

  .perm-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 16px;

    @include mobile {
      // §2.3 U1: 小号按钮之间的视觉间距 ≥18px
      gap: $small-btn-gap;
    }
  }

  .perm-hint {
    font-size: 12px;
    color: var(--orange);
    margin-top: 12px;
    padding: 8px 12px;
    background-color: var(--status-warning-bg);
    border-radius: var(--r-xs);
  }
}

.empty-demo {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;

  .empty-item {
    padding: 16px;
    background-color: var(--card);
    border-radius: var(--r-s);
    border: 1px solid var(--line);
    text-align: center;

    h4 {
      margin: 0 0 12px;
      text-align: left;
    }
  }
}
</style>
