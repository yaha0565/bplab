<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '../utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Picture, VideoPlay, VideoPause, Timer } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const user = JSON.parse(localStorage.getItem('user') || '{}')
const isAssignee = computed(() => task.value?.assignee === user.username)
const isTester = computed(() => user.role === '实验员')

const task = ref(null)
const records = ref([])
const attachments = ref([])
const loading = ref(true)
const acting = ref(false)

onMounted(async () => {
  await loadTask()
})

async function loadTask() {
  try {
    const { data } = await request.get(`/tasks/${route.params.id}`)
    task.value = data.task
    records.value = data.records
    attachments.value = data.attachments
  } finally {
    loading.value = false
  }
}

// ── 开始 / 结束实验 ──
async function markTime(action) {
  try {
    const label = action === '开始' ? '开始实验' : '结束实验'
    await ElMessageBox.confirm(
      `确认「${label}」？`,
      label,
      { type: 'info', confirmButtonText: label, cancelButtonText: '取消' }
    )
    acting.value = true
    await request.put(`/tasks/${route.params.id}/time`, { action })
    ElMessage.success(`已标记实验${action}`)
    await loadTask()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    acting.value = false
  }
}

function getStatusType(status) {
  const map = { '检测中': '', '已完成': 'success', '待接收': 'info', '待复核': 'warning' }
  return map[status] || 'info'
}
</script>

<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <h1>任务详情 — {{ task?.task_no }}</h1>
      <div style="display:flex;gap:8px;align-items:center">
        <el-tag v-if="task" :type="getStatusType(task.status)" size="large">{{ task.status }}</el-tag>
        <el-button
          v-if="isTester && isAssignee && task?.status === '检测中'"
          type="warning"
          @click="router.push(`/experiment/${route.params.id}`)"
        >去实验</el-button>
        <el-button
          v-if="isTester && isAssignee && task?.status === '待接收'"
          type="primary"
          :icon="VideoPlay"
          :loading="acting"
          @click="markTime('开始')"
        >开始实验</el-button>
        <el-button
          v-if="isTester && isAssignee && task?.status === '检测中'"
          type="danger"
          :icon="VideoPause"
          :loading="acting"
          @click="markTime('结束')"
        >结束实验</el-button>
      </div>
    </div>

    <template v-if="task">
      <el-row :gutter="20">
        <!-- 左侧：原始记录 + 附件 -->
        <el-col :span="16">
          <el-card header="原始记录" style="margin-bottom:16px">
            <el-table :data="records" empty-text="暂无记录" size="small">
              <el-table-column prop="record_no" label="记录编号" width="200" />
              <el-table-column prop="version" label="版本" width="80">
                <template #default="{ row }">V{{ row.version }}</template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === '已复核' ? 'success' : row.status === '待复核' ? 'warning' : 'info'" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="owner" label="操作人" width="120" />
              <el-table-column prop="created_at" label="创建时间" />
            </el-table>
          </el-card>

          <el-card header="附件与照片">
            <div v-if="attachments.length === 0" style="color:#94A3B8;text-align:center;padding:20px;">暂无附件</div>
            <el-table v-else :data="attachments" size="small">
              <el-table-column prop="checkpoint_label" label="节点" width="180">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.checkpoint_label ? 'primary' : 'info'">
                    {{ row.checkpoint_label || row.attachment_type }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="original_name" label="文件名" min-width="200" />
              <el-table-column prop="attachment_type" label="类型" width="140">
                <template #default="{ row }">
                  <el-icon v-if="row.attachment_type?.includes('图像') || row.attachment_type?.includes('照片')"><Picture /></el-icon>
                  <el-icon v-else><Document /></el-icon>
                  {{ row.attachment_type }}
                </template>
              </el-table-column>
              <el-table-column prop="uploader" label="上传者" width="100" />
              <el-table-column prop="captured_at" label="拍摄时间" width="160" />
            </el-table>
          </el-card>
        </el-col>

        <!-- 右侧：任务信息 + 时间线 -->
        <el-col :span="8">
          <el-card header="任务信息" style="margin-bottom:16px">
            <el-descriptions :column="1" size="small">
              <el-descriptions-item label="任务编号">{{ task.task_no }}</el-descriptions-item>
              <el-descriptions-item label="所属任务包">{{ task.package_no }}</el-descriptions-item>
              <el-descriptions-item label="委托编号">{{ task.commission_no }}</el-descriptions-item>
              <el-descriptions-item label="检测项目">{{ task.experiment }}</el-descriptions-item>
              <el-descriptions-item label="方法编号">{{ task.method_code }}</el-descriptions-item>
              <el-descriptions-item label="实验员">{{ task.assignee }}</el-descriptions-item>
              <el-descriptions-item label="复核员">{{ task.reviewer }}</el-descriptions-item>
              <el-descriptions-item label="检测地点">{{ task.detection_location }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card header="时间线">
            <el-timeline>
              <el-timeline-item :timestamp="task.created_at" placement="top" type="primary">
                任务创建
              </el-timeline-item>
              <el-timeline-item
                v-if="task.experiment_started_at"
                :timestamp="task.experiment_started_at"
                placement="top"
                type="warning"
              >
                <span style="font-weight:600">实验开始</span>
              </el-timeline-item>
              <el-timeline-item
                v-if="task.experiment_ended_at"
                :timestamp="task.experiment_ended_at"
                placement="top"
                type="success"
              >
                <span style="font-weight:600">实验结束</span>
              </el-timeline-item>
              <el-timeline-item
                v-if="!task.experiment_started_at && !task.experiment_ended_at"
                timestamp="等待开始"
                placement="top"
                color="#94A3B8"
              >
                尚未开始实验
              </el-timeline-item>
            </el-timeline>
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 1300px; }
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 20px;
}
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
