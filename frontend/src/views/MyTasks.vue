<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, VideoPause, Clock, Edit } from '@element-plus/icons-vue'

const router = useRouter()
const tasks = ref([])
const loading = ref(true)
const acting = ref(false)
const activeTab = ref('all')
const counts = ref({ pending: 0, testing: 0, done: 0, returned: 0, review_pending: 0 })

onMounted(async () => {
  await loadTasks()
  await loadCounts()
})

async function loadTasks(status) {
  loading.value = true
  try {
    const params = { limit: 200 }
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
    counts.value = {
      pending: data.pending_tasks || 0,
      testing: data.active_tasks || 0,
      done: data.completed_tasks || 0,
      returned: data.returned_tasks || 0,
      review_pending: data.review_pending_tasks || 0,
    }
  } catch { /* ignore */ }
}

function handleTabChange(tab) {
  const map = {
    all: '', pending: '待接收', testing: '检测中',
    done: '已完成', returned: '退回修改', review_pending: '待复核',
  }
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
    handleTabChange(activeTab.value)
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
  const map = {
    '检测中': '', '已完成': 'success', '待接收': 'info',
    '待复核': 'warning', '退回修改': 'danger', '已复核': 'success',
    '草稿': 'info',
  }
  return map[status] || 'info'
}

function getStatusLabel(status) {
  const map = {
    '检测中': '检测中', '已完成': '已完成', '待接收': '待接收',
    '待复核': '待复核', '退回修改': '需修改', '已复核': '已复核',
  }
  return map[status] || status
}

// Group tasks by package
const taskGroups = computed(() => {
  const groups = {}
  for (const t of tasks.value) {
    const pkg = t.package_no || '未分组'
    if (!groups[pkg]) groups[pkg] = []
    groups[pkg].push(t)
  }
  return groups
})

// Summary per package
function packageSummary(tasks) {
  const statuses = tasks.map(t => t.status)
  let label = ''
  if (statuses.every(s => s === '已完成')) label = '全部已完成'
  else if (statuses.some(s => s === '退回修改')) label = '有需修改项'
  else if (statuses.some(s => s === '待复核')) label = '有任务待复核'
  else if (statuses.some(s => s === '检测中')) label = '进行中'
  else if (statuses.some(s => s === '待接收')) label = '待开始'
  else label = `${tasks.length}个任务`
  return label
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>我的实验任务</h1>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="4">
        <el-card class="mini-stat" @click="handleTabChange('pending')" style="cursor:pointer">
          <div class="mini-num" style="color:#7C3AED">{{ counts.pending || 0 }}</div>
          <div class="mini-label">待接收</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="mini-stat" @click="handleTabChange('testing')" style="cursor:pointer">
          <div class="mini-num" style="color:#D97706">{{ counts.testing || 0 }}</div>
          <div class="mini-label">检测中</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="mini-stat" @click="handleTabChange('review_pending')" style="cursor:pointer">
          <div class="mini-num" style="color:#2563EB">{{ counts.review_pending || 0 }}</div>
          <div class="mini-label">待复核</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="mini-stat" @click="handleTabChange('returned')" style="cursor:pointer">
          <div class="mini-num" style="color:#DC2626">{{ counts.returned || 0 }}</div>
          <div class="mini-label">需修改</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="mini-stat" @click="handleTabChange('done')" style="cursor:pointer">
          <div class="mini-num" style="color:#059669">{{ counts.done || 0 }}</div>
          <div class="mini-label">已完成</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="mini-stat" @click="handleTabChange('all')" style="cursor:pointer">
          <div class="mini-num" style="color:#64748B">{{ (counts.pending||0) + (counts.testing||0) + (counts.review_pending||0) + (counts.returned||0) + (counts.done||0) }}</div>
          <div class="mini-label">全部</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card>
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="待接收" name="pending" />
        <el-tab-pane label="检测中" name="testing" />
        <el-tab-pane label="已完成" name="done" />
        <el-tab-pane label="需修改" name="returned" />
        <el-tab-pane label="待复核" name="review_pending" />
      </el-tabs>

      <!-- Group by task package -->
      <div v-for="(pkgTasks, pkgNo) in taskGroups" :key="pkgNo" style="margin-bottom:20px">
        <div style="padding:6px 10px;background:#F1F5F9;border-radius:6px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600;font-size:13px;color:#334155">
            📦 {{ pkgNo }}
          </span>
          <el-tag size="small" :type="packageSummary(pkgTasks).includes('需修改')?'danger':packageSummary(pkgTasks).includes('待复核')?'warning':packageSummary(pkgTasks).includes('进行中')?'':packageSummary(pkgTasks).includes('待开始')?'info':'success'">
            {{ packageSummary(pkgTasks) }}
          </el-tag>
          <span style="font-size:12px;color:#94A3B8">{{ pkgTasks.length }}个任务</span>
        </div>

        <el-table :data="pkgTasks" v-loading="loading" stripe size="small"
          @row-click="viewTask" style="cursor:pointer">
          <el-table-column prop="task_no" label="任务编号" width="230" />
          <el-table-column prop="experiment" label="检测项目" width="180" />
          <el-table-column prop="method_code" label="方法编号" width="130" />
          <el-table-column prop="detection_location" label="检测地点" width="120" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="experiment_started_at" label="开始时间" width="160" />
          <el-table-column prop="experiment_ended_at" label="结束时间" width="160" />
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <!-- 待接收：开始实验 -->
              <el-button
                v-if="row.status === '待接收'"
                type="primary"
                size="small"
                :icon="VideoPlay"
                :loading="acting === row.task_no"
                @click.stop="markTime(row, '开始')"
              >开始</el-button>

              <!-- 检测中：去实验 + 结束 -->
              <template v-if="row.status === '检测中'">
                <el-button type="primary" size="small" @click.stop="router.push(`/experiment/${row.task_no}`)">去实验</el-button>
                <el-button type="danger" size="small" :icon="VideoPause" :loading="acting === row.task_no"
                  @click.stop="markTime(row, '结束')" style="margin-top:2px">结束</el-button>
              </template>

              <!-- 退回修改：去修改 -->
              <el-button
                v-if="row.status === '退回修改'"
                type="danger"
                size="small"
                :icon="Edit"
                @click.stop="router.push(`/experiment/${row.task_no}`)"
              >去修改</el-button>

              <!-- 草稿：继续编辑 -->
              <el-button
                v-if="row.status === '草稿'"
                type="primary"
                size="small"
                @click.stop="router.push(`/experiment/${row.task_no}`)"
              >继续编辑</el-button>

              <!-- 已完成 / 待复核 / 已复核：查看 -->
              <el-tag v-if="['已完成','待复核','已复核'].includes(row.status)" type="success" size="small">
                <el-icon :size="12"><Clock /></el-icon>
                {{ row.status === '待复核' ? '待复核' : '已完成' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- No tasks -->
      <el-empty v-if="!loading && !Object.keys(taskGroups).length" description="暂无任务" />
    </el-card>
  </div>
</template>

<style scoped>
.page { max-width: 1600px; }
.page-header { margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }

.mini-stat { text-align: center; }
.mini-stat :deep(.el-card__body) { padding: 14px; }
.mini-num { font-size: 24px; font-weight: 700; line-height: 1.2; }
.mini-label { font-size: 12px; color: #94A3B8; margin-top: 4px; }
</style>
