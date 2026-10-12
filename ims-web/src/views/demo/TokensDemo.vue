<script setup lang="ts">
/**
 * Token 演示页 (FP-P-01)
 * 展示: Token 色板、字号、按钮四种层级、状态色 8 组
 */
import PageHeader from '@/components/layout/PageHeader.vue'
import StatusTag from '@/components/list/StatusTag.vue'

// 颜色 Token
const colorTokens = [
  { name: '--bg', value: '#f5f5f7', desc: '页面背景' },
  { name: '--card', value: '#fff', desc: '卡片背景' },
  { name: '--text', value: '#1d1d1f', desc: '主文字' },
  { name: '--text2', value: '#86868b', desc: '次要文字' },
  { name: '--blue', value: '#0071e3', desc: '主色' },
  { name: '--blue-h', value: '#0077ed', desc: '主色 hover' },
  { name: '--blue-bg', value: '#e8f2fe', desc: '选中背景' },
  { name: '--green', value: '#34c759', desc: '成功' },
  { name: '--orange', value: '#ff9500', desc: '警告' },
  { name: '--red', value: '#ff3b30', desc: '错误/危险' },
  { name: '--gray', value: '#8e8e93', desc: '中性' },
  { name: '--cyan', value: '#5ac8fa', desc: '信息' },
  { name: '--purple', value: '#af52da', desc: '分类' },
  { name: '--yellow', value: '#ffcc00', desc: '等级' },
]

// 尺寸 Token
const sizeTokens = [
  { name: '--sidebar-width', value: '232px', desc: '侧栏宽度' },
  { name: '--topbar-height', value: '56px', desc: '顶栏高度' },
  { name: '--content-padding-y', value: '28px', desc: '内容区上下内边距' },
  { name: '--content-padding-x', value: '32px', desc: '内容区左右内边距' },
  { name: '--drawer-s', value: '480px', desc: '抽屉 S 宽度' },
  { name: '--drawer-m', value: '720px', desc: '抽屉 M 宽度' },
  { name: '--drawer-l', value: '880px', desc: '抽屉 L 宽度' },
  { name: '--r', value: '12px', desc: '大圆角' },
  { name: '--r-s', value: '8px', desc: '中圆角' },
  { name: '--r-xs', value: '5px', desc: '小圆角' },
]

// 状态色示例
const statusColors = [
  { type: 'primary', label: '进行中/已提交', text: '#0071e3', bg: 'rgba(0,113,227,.12)' },
  { type: 'success', label: '完成/正常', text: '#1e8e3e', bg: 'rgba(52,199,89,.12)' },
  { type: 'warning', label: '待办/警示', text: '#c46a00', bg: 'rgba(255,149,0,.12)' },
  { type: 'danger', label: '失败/严重', text: '#d70015', bg: 'rgba(255,59,48,.12)' },
  { type: 'neutral', label: '中性/终止', text: '#6d6d72', bg: 'rgba(142,142,147,.12)' },
  { type: 'info', label: '信息', text: '#0e7fb8', bg: 'rgba(90,200,250,.12)' },
  { type: 'purple', label: '分类', text: '#8944ab', bg: 'rgba(175,82,218,.12)' },
  { type: 'yellow', label: '等级', text: '#a07d00', bg: 'rgba(255,204,0,.12)' },
]
</script>

<template>
  <div class="tokens-demo">
    <PageHeader title="Token 演示" sub-title="FP-P-01 / FP-T-01~04" />

    <!-- 颜色 Token -->
    <section class="demo-section">
      <h2 class="section-title">颜色 Token</h2>
      <div class="color-grid">
        <div v-for="token in colorTokens" :key="token.name" class="color-item">
          <div class="color-swatch" :style="{ backgroundColor: token.value }" />
          <div class="color-info">
            <code class="color-name">{{ token.name }}</code>
            <span class="color-value">{{ token.value }}</span>
            <span class="color-desc">{{ token.desc }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 尺寸 Token -->
    <section class="demo-section">
      <h2 class="section-title">尺寸 Token</h2>
      <div class="size-grid">
        <div v-for="token in sizeTokens" :key="token.name" class="size-item">
          <code class="size-name">{{ token.name }}</code>
          <span class="size-value">{{ token.value }}</span>
          <span class="size-desc">{{ token.desc }}</span>
        </div>
      </div>
    </section>

    <!-- 按钮层级 -->
    <section class="demo-section">
      <h2 class="section-title">按钮层级</h2>
      <div class="button-demo">
        <div class="button-row">
          <el-button type="primary">主按钮</el-button>
          <el-button>次按钮</el-button>
          <el-button text type="primary">文字按钮</el-button>
          <el-button text type="danger">危险文字按钮</el-button>
        </div>
        <div class="button-row button-row--small">
          <el-button type="primary" size="small">小号主按钮</el-button>
          <el-button size="small">小号次按钮</el-button>
        </div>
        <div class="button-specs">
          <p>主按钮: 高 32px, padding 0 16px, 字号 13px, 圆角 8px</p>
          <p>小号按钮: 高 26px, padding 0 11px, 字号 12px, 圆角 5px</p>
        </div>
      </div>
    </section>

    <!-- 状态色 8 组 -->
    <section class="demo-section">
      <h2 class="section-title">状态色 8 组 (FP-T-03)</h2>
      <div class="status-grid">
        <div v-for="status in statusColors" :key="status.type" class="status-item">
          <div
            class="status-preview"
            :style="{ backgroundColor: status.bg, color: status.text }"
          >
            <span class="status-dot" :style="{ backgroundColor: status.text }" />
            {{ status.label }}
          </div>
          <div class="status-info">
            <span class="status-type">{{ status.type }}</span>
            <code>文字: {{ status.text }}</code>
            <code>底色: {{ status.bg }}</code>
          </div>
        </div>
      </div>
    </section>

    <!-- 字典驱动状态标签示例 -->
    <section class="demo-section">
      <h2 class="section-title">StatusTag 组件示例</h2>
      <div class="status-tags">
        <StatusTag dict-type="demo_order_status" value="DRAFT" />
        <StatusTag dict-type="demo_order_status" value="PENDING" />
        <StatusTag dict-type="demo_order_status" value="APPROVED" />
        <StatusTag dict-type="demo_order_status" value="REJECTED" />
        <StatusTag dict-type="demo_order_status" value="CANCELLED" />
      </div>
    </section>

    <!-- 输入框高度 -->
    <section class="demo-section">
      <h2 class="section-title">表单控件</h2>
      <div class="form-demo">
        <div class="form-row">
          <span class="form-label">输入框 (高 34px):</span>
          <el-input placeholder="请输入" style="width: 200px" />
        </div>
        <div class="form-row">
          <span class="form-label">查询栏输入框 (高 30px):</span>
          <el-input class="query-bar" placeholder="请输入" style="width: 200px" />
        </div>
      </div>
    </section>

    <!-- 表头样式 -->
    <section class="demo-section">
      <h2 class="section-title">表格样式</h2>
      <p class="demo-note">表头: 11px / 600 / 次要文字色 / 底色 #fafafc</p>
      <p class="demo-note">单元格: 13px / 内边距 10px 12px</p>
      <el-table :data="[{ name: '示例', amount: 1234.5, status: 'APPROVED' }]" style="max-width: 600px">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="amount" label="金额" align="right" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <StatusTag dict-type="demo_order_status" :value="row.status" />
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style lang="scss" scoped>
.tokens-demo {
  max-width: 1000px;
}

.demo-section {
  margin-bottom: 40px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}

// 颜色 Token
.color-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.color-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
}

.color-swatch {
  width: 40px;
  height: 40px;
  border-radius: var(--r-xs);
  border: 1px solid var(--line);
  flex-shrink: 0;
}

.color-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.color-name {
  font-size: 12px;
  color: var(--blue);
}

.color-value {
  font-size: 12px;
  color: var(--text);
  font-family: monospace;
}

.color-desc {
  font-size: 12px;
  color: var(--text2);
}

// 尺寸 Token
.size-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 8px;
}

.size-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background-color: var(--card);
  border-radius: var(--r-xs);
  border: 1px solid var(--line);
}

.size-name {
  font-size: 12px;
  color: var(--blue);
  min-width: 140px;
}

.size-value {
  font-size: 12px;
  color: var(--text);
  font-family: monospace;
  min-width: 60px;
}

.size-desc {
  font-size: 12px;
  color: var(--text2);
}

// 按钮
.button-demo {
  background-color: var(--card);
  padding: 20px;
  border-radius: var(--r);
  border: 1px solid var(--line);
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;

  // §2.3 U1: 小号按钮之间的视觉间距 ≥18px
  &--small {
    gap: 18px;
  }
}

.button-specs {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--line);

  p {
    font-size: 12px;
    color: var(--text2);
    margin: 4px 0;
  }
}

// 状态色
.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.status-item {
  padding: 12px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
}

.status-preview {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--r-xs);
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 8px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-info {
  display: flex;
  flex-direction: column;
  gap: 4px;

  .status-type {
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
  }

  code {
    font-size: 11px;
    color: var(--text2);

    @include mobile {
      font-size: 12px;
    }
  }
}

// 状态标签示例
.status-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

// 表单
.form-demo {
  background-color: var(--card);
  padding: 20px;
  border-radius: var(--r);
  border: 1px solid var(--line);
}

.form-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;

  &:last-child {
    margin-bottom: 0;
  }
}

.form-label {
  font-size: 13px;
  color: var(--text2);
  min-width: 160px;
}

.demo-note {
  font-size: 13px;
  color: var(--text2);
  margin: 4px 0 12px;
}
</style>
