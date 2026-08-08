<script setup>
import { ref, onMounted } from 'vue'
import request from '../utils/request'

const records = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await request.get('/records/pending-review', { params: { limit: 50 } })
    records.value = data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>原始记录复核</h1>
    </div>

    <el-card>
      <el-table :data="records" v-loading="loading" stripe empty-text="暂无待复核记录">
        <el-table-column prop="record_no" label="记录编号" width="200" />
        <el-table-column prop="task_no" label="任务编号" width="200" />
        <el-table-column prop="version" label="版本" width="80">
          <template #default="{ row }">V{{ row.version }}</template>
        </el-table-column>
        <el-table-column prop="experiment" label="检测项目" min-width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag type="warning" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="owner" label="实验员" width="120" />
        <el-table-column prop="created_at" label="提交时间" width="160" />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.page { max-width: 1300px; }
.page-header { margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
