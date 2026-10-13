<script setup lang="ts">
/**
 * AppLayout 应用框架
 * 依据: FP-C01-01, 00-工作包 §2.1 Q2/Q3
 * 结构: 侧栏(232px) + 顶栏(56px) + 内容区
 * 手机: 侧栏改为左侧抽屉 240px, 带遮罩, 点菜单项后自动收起
 */
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Menu, Bell, ArrowDown, Fold, Expand } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useDownloadStore } from '@/stores/download'
import { useUnreadStore } from '@/stores/unread'
import { useResponsive } from '@/utils/responsive'
import { collectLeafPaths, resolveLanding, visibleMenus } from '@/utils/login-landing'
import DownloadBar from '@/components/file/DownloadBar.vue'
import BellDrawer from '@/components/workbench/BellDrawer.vue'
import type { MenuItem } from '@/types'
import SidebarMenuTree from '@/components/layout/SidebarMenuTree.vue'

const props = withDefaults(defineProps<{ hideSidebar?: boolean }>(), { hideSidebar: false })

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const downloadStore = useDownloadStore()
const unreadStore = useUnreadStore()
const { isMobile } = useResponsive()

// 侧栏状态
const sidebarCollapsed = ref(localStorage.getItem('sidebarCollapsed') === 'true')
const mobileSidebarOpen = ref(false)

// 铃铛抽屉
const bellDrawerVisible = ref(false)

// 计算属性
const currentPath = computed(() => route.path)
/** 未登记路由的菜单不进侧栏，避免 B3 前把工作台画成可点菜单。 */
const sidebarMenus = computed(() => visibleMenus(authStore.menus, registeredPaths()))
const hasMenus = computed(() => sidebarMenus.value.length > 0)

function registeredPaths(): string[] {
  return router.getRoutes().map((item) => item.path)
}

/** 菜单为空，或叶子都还没登记（B3 前的工作台）时，内容区提示，不跳业务页。 */
const showUnassigned = computed(() => {
  if (!authStore.isLoggedIn || route.meta.shell !== true) return false
  return resolveLanding({
    menus: authStore.menus,
    registeredPaths: registeredPaths(),
  }) === null
})

/**
 * 无权限页：
 * - 未登记的业务地址，以及已登记但菜单里没有的地址，直接遮住，不展示数据；
 * - 已登记的 /demo 示例页只在权限码为空时遮住（VC-R-16），避免挡住 B0b 演示。
 */
const showDenied = computed(() => {
  if (!authStore.isLoggedIn) return false
  if (route.meta.public || route.meta.menuless || route.meta.shell) return false
  const registered = router.getRoutes().some((item) => item.path === route.path)
  if (!registered) return true
  if (route.path.startsWith('/demo/')) return authStore.permCodes.length === 0
  const leaves = collectLeafPaths(authStore.menus)
  return !leaves.includes(route.path)
})

// 侧栏空菜单提示只在内容区不是同一句时出现，避免两处重复（B0b VC-R-16 仍要求侧栏有这句）
const showSidebarEmptyTip = computed(() => !hasMenus.value && !showUnassigned.value)

// 保存折叠状态
watch(sidebarCollapsed, (val) => {
  localStorage.setItem('sidebarCollapsed', String(val))
})

// 路由变化时关闭移动端侧栏 (Q2: 点菜单项后自动收起)
watch(
  () => route.path,
  () => {
    if (isMobile.value) {
      mobileSidebarOpen.value = false
    }
  }
)

// 切换侧栏折叠
function toggleSidebar() {
  if (isMobile.value) {
    mobileSidebarOpen.value = !mobileSidebarOpen.value
  } else {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }
}

// 菜单点击。设计器有未保存修改时先确认 (VC-L06-01)
async function handleMenuSelect(path: string) {
  if (sessionStorage.getItem('ims_designer_dirty') === '1') {
    try {
      await ElMessageBox.confirm('有未保存修改', '提示', {
        confirmButtonText: '离开',
        cancelButtonText: '留下',
      })
      sessionStorage.removeItem('ims_designer_dirty')
    } catch {
      return
    }
  }
  // 目录用 id 作 index，没有 path，不能当成路由跳转。
  if (!path.startsWith('/')) return
  router.push(path)
}

// 判断菜单是否激活
function isMenuActive(item: MenuItem): boolean {
  if (item.path === currentPath.value) return true
  if (item.children) {
    return item.children.some((child) => child.path === currentPath.value)
  }
  return false
}

// 获取激活的菜单路径 (用于展开)
function getActiveMenuPaths(): string[] {
  const paths: string[] = []
  function traverse(items: MenuItem[], parentPath: string[] = []) {
    for (const item of items) {
      const currentPaths = [...parentPath, item.id]
      if (item.path === currentPath.value) {
        paths.push(...currentPaths)
        return true
      }
      if (item.children && traverse(item.children, currentPaths)) {
        return true
      }
    }
    return false
  }
  traverse(sidebarMenus.value)
  return paths
}

// 退出登录。记下需要真实登录，避免开发环境在浏览器后退时又自动进入示例页。
function handleLogout() {
  authStore.clearSession()
  unreadStore.stopPolling()
  unreadStore.reset()
  sessionStorage.setItem('ims_require_auth', '1')
  router.push('/login')
}

// 打开铃铛抽屉
function openBellDrawer() {
  bellDrawerVisible.value = true
}

// 启动未读轮询
onMounted(() => {
  if (authStore.isLoggedIn) {
    unreadStore.startPolling()
  }
})

onUnmounted(() => {
  unreadStore.stopPolling()
})
</script>

<template>
  <div
    class="app-layout"
    :data-user-id="authStore.user?.id || ''"
    :class="{
      'sidebar-collapsed': sidebarCollapsed && !isMobile,
      'has-download': downloadStore.visible && downloadStore.tasks.length > 0,
    }"
  >
    <!-- 移动端侧栏遮罩 (Q2) -->
    <div
      v-if="isMobile && mobileSidebarOpen"
      class="sidebar-overlay"
      @click="mobileSidebarOpen = false"
    />

    <!-- 侧栏 -->
    <aside
      v-if="!props.hideSidebar"
      class="sidebar app-sidebar"
      :class="{
        collapsed: sidebarCollapsed && !isMobile,
        'mobile-open': isMobile && mobileSidebarOpen,
        'mobile-hidden': isMobile && !mobileSidebarOpen,
      }"
      data-testid="app-sidebar"
    >
      <div class="sidebar-header">
        <span v-if="!sidebarCollapsed || isMobile" class="logo-text">IMS</span>
        <span v-else class="logo-icon">I</span>
      </div>

      <!-- 菜单 -->
      <el-scrollbar class="sidebar-menu-wrap">
        <el-menu
          :default-active="currentPath"
          :default-openeds="getActiveMenuPaths()"
          :collapse="sidebarCollapsed && !isMobile"
          :collapse-transition="false"
          @select="handleMenuSelect"
        >
          <!-- 目录可多层。两级菜单与原来一样，三级（公司资产）也能点到叶子。 -->
          <SidebarMenuTree v-for="item in sidebarMenus" :key="item.id" :item="item" />
        </el-menu>

        <!-- 无菜单时的侧栏提示。壳页面的同一句改由内容区展示，避免重复。 -->
        <div v-if="showSidebarEmptyTip" class="no-menu-tip">
          您的账号尚未分配权限，请联系管理员
        </div>
      </el-scrollbar>
    </aside>

    <!-- 主区域 -->
    <div class="app-main">
      <!-- 顶栏 (Q3: 高度保持 56px) -->
      <header class="topbar app-topbar">
        <!-- 左侧: 菜单按钮 -->
        <div class="topbar-left">
          <el-button class="menu-btn touch-target" text @click="toggleSidebar">
            <el-icon :size="20">
              <Menu v-if="isMobile" />
              <Fold v-else-if="!sidebarCollapsed" />
              <Expand v-else />
            </el-icon>
          </el-button>
        </div>

        <!-- 右侧 (Q3: 只保留未读消息和用户菜单) -->
        <div class="topbar-right">
          <!-- 未读消息 -->
          <el-badge :value="unreadStore.count" :hidden="unreadStore.count === 0" class="msg-badge">
            <el-button class="topbar-btn touch-target" text @click="openBellDrawer">
              <el-icon :size="20"><Bell /></el-icon>
            </el-button>
          </el-badge>

          <!-- 用户菜单 -->
          <el-dropdown trigger="click" @command="handleLogout">
            <div class="user-dropdown touch-target">
              <el-avatar :size="32">
                {{ authStore.user?.nickname?.charAt(0) || 'U' }}
              </el-avatar>
              <span v-if="!isMobile" class="user-name">{{ authStore.user?.nickname }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <!-- Q3: 手机下"统计范围"移到用户菜单里 -->
                <el-dropdown-item v-if="isMobile && authStore.dataScopeText" disabled>
                  统计范围：{{ authStore.dataScopeText }}
                </el-dropdown-item>
                <el-dropdown-item v-if="isMobile && authStore.dataScopeText" divided />
                <el-dropdown-item>个人中心</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 内容区 -->
      <main class="app-content">
        <div v-if="showUnassigned" class="no-perm-panel" data-testid="unassigned-panel">
          <p>您的账号尚未分配权限，请联系管理员</p>
        </div>
        <div v-else-if="showDenied" class="no-perm-panel" data-testid="denied-panel">
          <p>暂无权限查看此内容</p>
        </div>
        <slot v-else />
      </main>
    </div>

    <Teleport to="body">
      <DownloadBar
        :tasks="downloadStore.tasks"
        :visible="downloadStore.visible"
        @close="downloadStore.hide()"
      />
    </Teleport>

    <!-- 铃铛抽屉 (B3) -->
    <BellDrawer v-model:visible="bellDrawerVisible" />
  </div>
</template>

<style lang="scss" scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background-color: var(--bg);
}

// 侧栏遮罩 (Q2)
.sidebar-overlay {
  position: fixed;
  inset: 0;
  background-color: rgb(0 0 0 / 40%);
  z-index: 999;
}

// 侧栏
.app-sidebar {
  width: var(--sidebar-width);
  min-height: 100vh;
  background-color: var(--card);
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  z-index: 1000;

  &.collapsed {
    width: var(--sidebar-collapsed-width);
  }

  // 手机端样式 (Q2)
  @include mobile {
    position: fixed;
    left: 0;
    top: 0;
    width: var(--mobile-sidebar-width);
    transform: translateX(-100%);
    transition: transform 0.3s ease;

    &.mobile-open {
      transform: translateX(0);
    }

    &.mobile-hidden {
      transform: translateX(-100%);
    }
  }
}

.sidebar-header {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--line);
  flex-shrink: 0;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: var(--blue);
}

.logo-icon {
  font-size: 20px;
  font-weight: 700;
  color: var(--blue);
}

.sidebar-menu-wrap {
  flex: 1;
  overflow: hidden;
}

// 菜单样式
:deep(.el-menu) {
  border-right: none;

  .el-menu-item,
  .el-sub-menu__title {
    height: 44px;
    line-height: 44px;
    font-size: 13px;

    @include mobile {
      // Q10: 最小触控尺寸 44px
      min-height: 44px;
    }
  }

  .el-sub-menu .el-menu-item {
    padding-left: 52px !important;
    font-size: 12.5px;
  }

  .el-menu-item.is-active {
    background-color: var(--blue-bg);
    color: var(--blue);
  }
}

.no-menu-tip {
  padding: 20px;
  text-align: center;
  color: var(--text2);
  font-size: 13px;
}

// 主区域
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

// 顶栏 (Q3)
.app-topbar {
  height: var(--topbar-height);
  background-color: var(--card);
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.menu-btn,
.topbar-btn {
  padding: 8px;
}

.msg-badge {
  :deep(.el-badge__content) {
    top: 6px;
    right: 6px;
  }
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--r-s);

  &:hover {
    background-color: var(--bg);
  }
}

.user-name {
  font-size: 14px;
  color: var(--text);
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

// 内容区
.app-content {
  flex: 1;
  padding: var(--content-padding-y) var(--content-padding-x);
  max-width: var(--content-max-width);
  width: 100%;
  margin: 0 auto;
  overflow-x: hidden;

  @include mobile {
    // Q18: 手机下内边距 12px 16px
    padding: $content-padding-y-mobile $content-padding-x-mobile;
  }
}

.app-layout.has-download .app-content {
  @include mobile {
    padding-bottom: 96px;
  }
}

// 侧栏折叠时调整
.sidebar-collapsed {
  .app-sidebar {
    width: var(--sidebar-collapsed-width);
  }
}
</style>
