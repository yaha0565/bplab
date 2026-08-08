<script setup>
import { ref, onMounted } from 'vue'
import request from '../utils/request'

const commissions = ref([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await request.get('/commissions', { params: { limit: 50 } })
    commissions.value = data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>委托与样品管理</h1>
    </div>

    <el-card>
      <el-table :data="commissions" v-loading="loading" stripe empty-text="暂无委托数据">
        <el-table-column prop="commission_no" label="委托编号" width="180" />
        <el-table-column prop="client_name" label="客户名称" width="200" />
        <el-table-column prop="production_org_name" label="生产单位" width="200" />
        <el-table-column prop="commission_date" label="委托日期" width="120" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.status === '已入库' ? 'success' : 'info'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; }
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
