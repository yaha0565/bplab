<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import request from '../utils/request'

const route = useRoute()
const commission = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await request.get(`/commissions/${route.params.id}`)
    commission.value = data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <h1>委托详情 — {{ commission?.commission_no }}</h1>
      <el-tag v-if="commission" :type="commission.status === '已入库' ? 'success' : 'info'">
        {{ commission.status }}
      </el-tag>
    </div>

    <template v-if="commission">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card header="基本信息" style="margin-bottom:16px">
            <el-descriptions :column="1" size="small">
              <el-descriptions-item label="委托编号">{{ commission.commission_no }}</el-descriptions-item>
              <el-descriptions-item label="客户名称">{{ commission.client_name }}</el-descriptions-item>
              <el-descriptions-item label="联系人">{{ commission.contact || '-' }}</el-descriptions-item>
              <el-descriptions-item label="电话">{{ commission.phone || '-' }}</el-descriptions-item>
              <el-descriptions-item label="客户地址">{{ commission.client_address || '-' }}</el-descriptions-item>
              <el-descriptions-item label="委托日期">{{ commission.commission_date || '-' }}</el-descriptions-item>
              <el-descriptions-item label="要求完成日期">{{ commission.due_date || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card header="生产信息" style="margin-bottom:16px">
            <el-descriptions :column="1" size="small">
              <el-descriptions-item label="生产单位">{{ commission.production_org_name }}</el-descriptions-item>
              <el-descriptions-item label="生产关系">{{ commission.production_relation }}</el-descriptions-item>
              <el-descriptions-item label="创建人">{{ commission.created_by || '-' }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ commission.created_at || '-' }}</el-descriptions-item>
              <el-descriptions-item label="备注">{{ commission.notes || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>

      <!-- 样品组 -->
      <el-card style="margin-bottom:16px">
        <template #header>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span>样品组</span>
            <span style="font-size:13px;color:#64748B">样品总数：<strong style="color:#0F172A">{{ commission.total_sample_count || 0 }}</strong></span>
          </div>
        </template>
        <el-table :data="commission.sample_groups" empty-text="暂无样品组" size="small">
          <el-table-column prop="group_no" label="组号" width="180" />
          <el-table-column prop="sample_name" label="样品名称" />
          <el-table-column prop="model" label="型号" />
          <el-table-column prop="material_name" label="材料" />
          <el-table-column prop="quantity" label="数量" width="80" />
          <el-table-column prop="experiment_codes" label="检测项目" width="150" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 样品 -->
      <el-card header="样品">
        <el-table :data="commission.samples" empty-text="暂无样品" size="small">
          <el-table-column prop="sample_no" label="样品编号" width="200" />
          <el-table-column prop="group_no" label="组号" width="180" />
          <el-table-column prop="sample_name" label="样品名称" />
          <el-table-column prop="condition" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.condition === '完好' ? 'success' : 'warning'" size="small">{{ row.condition }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="current_location" label="当前位置" width="120" />
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; }
.page-header {
  display: flex; align-items: center; gap: 16px;
  margin-bottom: 20px;
}
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
