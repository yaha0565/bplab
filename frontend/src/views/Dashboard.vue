<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../utils/request'
import {
  Folder, Files, List, Warning, Plus, Search,
  Upload, Download, Checked, Box, Notebook, Collection,
  Clock, Cpu, Van
} from '@element-plus/icons-vue'

const router = useRouter()
const counts = ref({})
const user = JSON.parse(localStorage.getItem('user') || '{}')
const role = computed(() => user.role || '')

// 角色对应的统计卡片配置
const statCards = computed(() => {
  const r = role.value
  const all = []

  if (r === '管理员' || r === '样品管理员') {
    all.push(
      { icon: Folder, color: '#2563EB', bg: '#DBEAFE', value: counts.value.total_commissions || 0, label: '委托总数' },
      { icon: Files, color: '#059669', bg: '#D1FAE5', value: counts.value.total_samples || 0, label: '样品总数' },
      { icon: Box, color: '#7C3AED', bg: '#EDE9FE', value: counts.value.pending_packages || 0, label: '待接收任务包' },
      { icon: Checked, color: '#D97706', bg: '#FEF3C7', value: counts.value.pending_reviews || 0, label: '待复核记录' },
    )
  } else if (r === '实验员') {
    all.push(
      { icon: Box, color: '#2563EB', bg: '#DBEAFE', value: counts.value.my_packages || 0, label: '我的任务包' },
      { icon: Warning, color: '#7C3AED', bg: '#EDE9FE', value: counts.value.pending_packages || 0, label: '待接收' },
      { icon: List, color: '#D97706', bg: '#FEF3C7', value: counts.value.active_tasks || 0, label: '检测中任务' },
      { icon: Checked, color: '#059669', bg: '#D1FAE5', value: counts.value.completed_tasks || 0, label: '已完成任务' },
    )
  } else if (r === '复核员') {
    all.push(
      { icon: Warning, color: '#7C3AED', bg: '#EDE9FE', value: counts.value.pending_reviews || 0, label: '待复核记录' },
      { icon: Checked, color: '#059669', bg: '#D1FAE5', value: counts.value.completed_tasks || 0, label: '已复核记录' },
      { icon: Clock, color: '#2563EB', bg: '#DBEAFE', value: counts.value.pending_packages || 0, label: '待处理总数' },
    )
  } else if (r === '质量负责人') {
    all.push(
      { icon: Collection, color: '#7C3AED', bg: '#EDE9FE', value: counts.value.pending_reports || 0, label: '待签发报告' },
      { icon: Checked, color: '#059669', bg: '#D1FAE5', value: counts.value.completed_tasks || 0, label: '已签发报告' },
    )
  }

  return all
})

// 角色对应的快捷操作
const quickActions = computed(() => {
  const r = role.value
  if (r === '管理员' || r === '样品管理员') return [
    { label: '新建委托', icon: Plus, path: '/commissions/create' },
    { label: '任务包分配', icon: Upload, path: '/task-packages' },
    { label: '样品入库', icon: Van, path: '/commissions' },
    { label: '导出报告', icon: Download, path: '/reports' },
  ]
  if (r === '实验员') return [
    { label: '查看任务包', icon: Box, path: '/task-packages' },
    { label: '开始实验', icon: Notebook, path: '/my-tasks' },
    { label: '登记危废', icon: Warning, path: '/hazardous-waste' },
    { label: '样品归还', icon: Van, path: '/sample-return' },
  ]
  if (r === '复核员') return [
    { label: '开始复核', icon: Checked, path: '/pending-reviews' },
    { label: '查看报告', icon: Collection, path: '/reports' },
  ]
  if (r === '质量负责人') return [
    { label: '报告审批', icon: Collection, path: '/reports' },
    { label: '客户异议', icon: Warning, path: '/objections' },
    { label: '审计追踪', icon: Search, path: '/audit-trail' },
  ]
  return []
})

onMounted(async () => {
  try {
    const { data } = await request.get('/dashboard/counts')
    counts.value = data
  } catch {
    ElMessage.warning('看板数据加载失败，请检查网络连接')
  }
})
</script>

<template>
  <div class="dashboard">
    <h1 class="page-title">
      欢迎回来{{ user.display_name ? '，' + user.display_name : '' }}
      <span class="role-badge">{{ user.role }}</span>
    </h1>

    <!-- 统计卡片 -->
    <el-row :gutter="20">
      <el-col v-for="(card, i) in statCards" :key="i" :span="statCards.length <= 2 ? 12 : statCards.length === 3 ? 8 : 6">
        <el-card class="stat-card">
          <div class="stat-icon" :style="{ background: card.bg, color: card.color }">
            <el-icon :size="28"><component :is="card.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ card.value }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top:24px">
      <!-- 快捷操作 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>快捷操作</span>
          </template>
          <el-space wrap>
            <el-button
              v-for="act in quickActions"
              :key="act.label"
              :type="act.label === quickActions[0]?.label ? 'primary' : 'default'"
              :icon="act.icon"
              @click="router.push(act.path)"
            >{{ act.label }}</el-button>
          </el-space>
        </el-card>
      </el-col>

      <!-- 系统信息 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>系统信息</span>
          </template>
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="系统版本">BPLab Trace LIMS V11.0</el-descriptions-item>
            <el-descriptions-item label="数据库">PostgreSQL 18</el-descriptions-item>
            <el-descriptions-item label="后端">FastAPI</el-descriptions-item>
            <el-descriptions-item label="前端">Vue 3 + Element Plus</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 22px;
  font-weight: 600;
  color: #0F172A;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.role-badge {
  font-size: 12px;
  font-weight: 500;
  color: #2563EB;
  background: #DBEAFE;
  padding: 2px 12px;
  border-radius: 10px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 4px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #0F172A;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #94A3B8;
  margin-top: 4px;
}
</style>
