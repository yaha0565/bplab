<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Check, Box } from '@element-plus/icons-vue'
import request from '../utils/request'

const loading = ref(false)
const stats = reactive({ total: 0, unreturned: 0, returned: 0, confirmed: 0 })

const filters = reactive({
  return_status: '',
  package_no: '',
  search: '',
})
const list = ref([])

async function loadStats() {
  try {
    const { data } = await request.get('/returns/stats')
    Object.assign(stats, data)
  } catch { /* ignore */ }
}

async function loadList() {
  loading.value = true
  try {
    const params = {}
    if (filters.return_status) params.return_status = filters.return_status
    if (filters.package_no) params.package_no = filters.package_no
    if (filters.search) params.search = filters.search
    const { data } = await request.get('/returns', { params })
    list.value = data
  } catch {
    ElMessage.warning('加载归还记录失败')
  } finally {
    loading.value = false
  }
}

async function confirmReturn(row) {
  try {
    await request.put(`/returns/${row.id}/confirm`, {
      return_condition: row.return_condition || '完好',
      confirmed_location: '',
    })
    ElMessage.success(`样品 ${row.sample_no} 回库已确认`)
    await loadList()
    await loadStats()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '确认失败')
  }
}

function statusTag(s) {
  const map = { '未归还': 'danger', '已归还': 'warning', '已确认': 'success' }
  return map[s] || 'info'
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('zh-CN')
}

onMounted(() => {
  loadStats()
  loadList()
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2><el-icon><Box /></el-icon> 回库确认</h2>
      <p class="desc">确认样品归还入库，管理借出/归还全流程</p>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6">
        <el-statistic title="全部借出" :value="stats.total" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="未归还" :value="stats.unreturned">
          <template #suffix><el-tag type="danger" size="small">待处理</el-tag></template>
        </el-statistic>
      </el-col>
      <el-col :span="6">
        <el-statistic title="已归还待确认" :value="stats.returned">
          <template #suffix><el-tag type="warning" size="small">待确认</el-tag></template>
        </el-statistic>
      </el-col>
      <el-col :span="6">
        <el-statistic title="已确认回库" :value="stats.confirmed" />
      </el-col>
    </el-row>

    <!-- 筛选 -->
    <div class="filter-bar">
      <el-select v-model="filters.return_status" placeholder="归还状态" clearable style="width:140px" @change="loadList">
        <el-option label="未归还" value="未归还" />
        <el-option label="已归还" value="已归还" />
        <el-option label="已确认" value="已确认" />
      </el-select>
      <el-input v-model="filters.package_no" placeholder="任务包编号" clearable style="width:200px" @keyup.enter="loadList" />
      <el-input v-model="filters.search" placeholder="搜索样品编号/借用人" clearable style="width:220px" @keyup.enter="loadList">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button type="primary" @click="loadList">查询</el-button>
    </div>

    <!-- 表格 -->
    <el-table :data="list" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="package_no" label="任务包编号" width="200" />
      <el-table-column prop="sample_no" label="样品编号" width="160" />
      <el-table-column prop="sample_name" label="样品名称" width="140" />
      <el-table-column prop="material_name" label="材料" width="100" />
      <el-table-column prop="borrower" label="借用人" width="100" />
      <el-table-column label="借出时间" width="160">
        <template #default="{ row }">{{ formatDate(row.borrowed_at) }}</template>
      </el-table-column>
      <el-table-column prop="purpose" label="用途" min-width="120" />
      <el-table-column label="归还状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.return_status)">{{ row.return_status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="return_condition" label="归还状况" width="90" />
      <el-table-column prop="returned_by" label="归还人" width="90" />
      <el-table-column label="归还时间" width="160">
        <template #default="{ row }">{{ formatDate(row.returned_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="110" align="center" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.return_status !== '已确认'"
            type="primary" size="small" :icon="Check"
            @click="confirmReturn(row)"
          >
            确认回库
          </el-button>
          <el-tag v-else type="success" size="small">已确认</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.page { max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-header h2 { display: flex; align-items: center; gap: 8px; font-size: 20px; color: #1E293B; }
.page-header .desc { color: #64748B; margin: 4px 0 0; font-size: 14px; }
.filter-bar { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
</style>
