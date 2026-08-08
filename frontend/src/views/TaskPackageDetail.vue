<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import request from '../utils/request'

const route = useRoute()
const pkg = ref(null)
const tasks = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await request.get(`/tasks/packages/${route.params.id}`)
    pkg.value = data.package
    tasks.value = data.tasks
  } finally {
    loading.value = false
  }
})

function getStatusType(status) {
  const map = { '待接收': 'info', '检测中': '', '待复核': 'warning', '已完成': 'success' }
  return map[status] || 'info'
}
</script>

<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <h1>任务包 — {{ pkg?.package_no }}</h1>
      <el-tag v-if="pkg" :type="getStatusType(pkg.status)">{{ pkg.status }}</el-tag>
    </div>

    <template v-if="pkg">
      <el-card header="任务包信息" style="margin-bottom:16px">
        <el-descriptions :column="2" size="small">
          <el-descriptions-item label="任务包编号">{{ pkg.package_no }}</el-descriptions-item>
          <el-descriptions-item label="委托编号">{{ pkg.commission_no }}</el-descriptions-item>
          <el-descriptions-item label="样品组">{{ pkg.group_no }}</el-descriptions-item>
          <el-descriptions-item label="材料">{{ pkg.material_name }}</el-descriptions-item>
          <el-descriptions-item label="实验员">{{ pkg.assignee }}</el-descriptions-item>
          <el-descriptions-item label="复核员">{{ pkg.reviewer }}</el-descriptions-item>
          <el-descriptions-item label="检测项目" :span="2">{{ pkg.experiments }}</el-descriptions-item>
          <el-descriptions-item label="检测地点">{{ pkg.detection_location || '-' }}</el-descriptions-item>
          <el-descriptions-item label="分配时间">{{ pkg.assigned_at || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card header="包含的实验任务">
        <el-table :data="tasks" empty-text="暂无任务" size="small">
          <el-table-column prop="task_no" label="任务编号" width="200" />
          <el-table-column prop="experiment" label="检测项目" min-width="200" />
          <el-table-column prop="method_code" label="方法编号" width="140" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="detection_location" label="检测地点" width="130" />
          <el-table-column prop="experiment_started_at" label="开始时间" width="160" />
          <el-table-column prop="experiment_ended_at" label="结束时间" width="160" />
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; }
.page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
