<script setup>
import { ref, onMounted } from 'vue'
import request from '../utils/request'

const reports = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await request.get('/reports', { params: { limit: 50 } })
    reports.value = data
  } finally {
    loading.value = false
  }
})

function getStatusType(status) {
  const map = { '已签发': 'success', '草稿': 'info', '待签发': 'warning', '作废': 'danger' }
  return map[status] || 'info'
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>报告中心</h1>
    </div>

    <el-card>
      <el-table :data="reports" v-loading="loading" stripe empty-text="暂无报告">
        <el-table-column prop="report_no" label="报告编号" width="200" />
        <el-table-column prop="commission_no" label="委托编号" width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tester" label="实验员" width="120" />
        <el-table-column prop="verifier" label="复核员" width="120" />
        <el-table-column prop="quality_inspector" label="质量负责人" width="120" />
        <el-table-column prop="publish_date" label="签发日期" width="120" />
        <el-table-column prop="created_at" label="创建时间" />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.page { max-width: 1300px; }
.page-header { margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
