<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, VideoPause, Clock } from '@element-plus/icons-vue'

const router = useRouter()
const tasks = ref([])
const loading = ref(true)
const acting = ref(false)       // 正在操作的 task_no
const activeTab = ref('all')    // all | pending | testing | done
const counts = ref({ pending: 0, testing: 0, done: 0 })

onMounted(async () => {
  await loadTasks()
  await loadCounts()
})

async function loadTasks(status) {
  loading.value = true
  try {
    const params = { limit: 50 }
    if (status) params.status = status
    const { data } = await request.get('/tasks/my', { params })
    tasks.value = data
  } catch (e) {
    ElMessage.error('加载任务失败')
  } finally {
    loading.value = false
  }
}

async function loadCounts() {
  try {
    const { data } = await request.get('/dashboard/counts')
    counts.value = data
  } catch { /* ignore */ }
}

function handleTabChange(tab) {
  const map = { all: '', pending: '待接收', testing: '检测中', done: '已完成' }
  loadTasks(map[tab] || '')
}

// ── 开始 / 结束实验 ──
async function markTime(task, action) {
  try {
    const label = action === '开始' ? '开始实验' : '结束实验'
    await ElMessageBox.confirm(
      `确认「${label}」？任务: ${task.task_no}`,
      label,
      { type: 'info', confirmButtonText: label, cancelButtonText: '取消' }
    )
    acting.value = task.task_no
    await request.put(`/tasks/${task.task_no}/time`, { action })
    ElMessage.success(`已标记实验${action}`)
    loadTasks(activeTab.value === 'all' ? '' : activeTab.value === 'pending' ? '待接收' : activeTab.value === 'testing' ? '检测中' : '已完成')
    loadCounts()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    acting.value = false
  }
}

function viewTask(task) {
  router.push(`/task/${task.task_no}`)
}

function getStatusType(status) {
  const map = { '检测中': '', '已完成': 'success', '待接收': 'info', '待复核': 'warning' }
  return map[status] || 'info'
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>我的实验任务</h1>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="8">
        <el-card class="mini-stat">
          <div class="mini-num" style="color:#7C3AED">{{ counts.pending_packages || 0 }}</div>
          <div class="mini-label">待接收</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="mini-stat">
          <div class="mini-num" style="color:#D97706">{{ counts.active_tasks || 0 }}</div>
          <div class="mini-label">检测中</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="mini-stat">
          <div class="mini-num" style="color:#059669">{{ counts.completed_tasks || 0 }}</div>
          <div class="mini-label">已完成</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card>
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="待接收" name="pending" />
        <el-tab-pane label="检测中" name="testing" />
        <el-tab-pane label="已完成" name="done" />
      </el-tabs>

      <el-table :data="tasks" v-loading="loading" stripe empty-text="暂无任务" @row-click="viewTask" style="cursor:pointer">
        <el-table-column prop="task_no" label="任务编号" width="210" />
        <el-table-column prop="package_no" label="所属任务包" width="210" />
        <el-table-column prop="experiment" label="检测项目" width="160" />
        <el-table-column prop="method_code" label="方法编号" width="140" />
        <el-table-column prop="detection_location" label="检测地点" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="experiment_started_at" label="开始时间" width="160" />
        <el-table-column prop="experiment_ended_at" label="结束时间" width="160" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === '待接收'"
              type="primary"
              size="small"
              :icon="VideoPlay"
              :loading="acting === row.task_no"
              @click.stop="markTime(row, '开始')"
            >开始</el-button>
            <el-button
              v-else-if="row.status === '检测中'"
              type="warning"
              size="small"
              @click.stop="router.push(`/experiment/${row.task_no}`)"
            >去实验</el-button>
            <el-button
              v-if="row.status === '检测中'"
              type="danger"
              size="small"
              :icon="VideoPause"
              :loading="acting === row.task_no"
              @click.stop="markTime(row, '结束')"
              style="margin-top:2px"
            >结束</el-button>
            <el-tag v-else-if="row.status === '已完成'" type="success" size="small">
              <el-icon :size="12"><Clock /></el-icon>
              已完成
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.page { max-width: 1400px; }
.page-header { margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }

.mini-stat { text-align: center; cursor: default; }
.mini-stat :deep(.el-card__body) { padding: 16px; }
.mini-num { font-size: 28px; font-weight: 700; line-height: 1.2; }
.mini-label { font-size: 13px; color: #94A3B8; margin-top: 4px; }
</style>
