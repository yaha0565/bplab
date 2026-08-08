<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Files, Search, Download } from '@element-plus/icons-vue'
import request from '../utils/request'

const loading = ref(false)
const commissionNo = ref('')
const groupNo = ref('')
const items = ref([])

async function query() {
  if (!commissionNo.value.trim()) { ElMessage.warning('请输入委托编号'); return }
  loading.value = true
  try {
    const { data } = await request.get(`/export/commission/${commissionNo.value.trim()}/items`)
    items.value = data
  } catch { ElMessage.warning('查询失败，请检查委托编号') } finally { loading.value = false }
}

async function downloadAll() {
  try {
    const res = await request.post('/export/batch', {
      task_nos: items.value.filter(i => i.type === 'task').map(i => i.no),
      report_nos: items.value.filter(i => i.type === 'report').map(i => i.no),
    }, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/zip' }))
    const a = document.createElement('a'); a.href = url; a.download = `${commissionNo.value}_单据.zip`; a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('下载完成')
  } catch { ElMessage.error('下载失败') }
}

async function downloadOne(no, type) {
  const endpoint = type === 'task' ? `/export/record/${no}` : `/export/report/${no}`
  try {
    const res = await request.get(endpoint, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }))
    const a = document.createElement('a'); a.href = url; a.download = `${no}.docx`; a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('下载完成')
  } catch { ElMessage.error('下载失败') }
}

function formatDate(d) { return d ? new Date(d).toLocaleString('zh-CN') : '—' }
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2><el-icon><Files /></el-icon> 单据中心</h2>
    </div>

    <div style="display:flex;gap:12px;align-items:center;margin-bottom:16px">
      <el-input v-model="commissionNo" placeholder="输入委托编号（如 WT20260809XXX）" clearable @keyup.enter="query" style="width:300px">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button type="primary" @click="query">查询</el-button>
      <el-button v-if="items.length" type="success" @click="downloadAll"><el-icon><Download /></el-icon> 一键下载</el-button>
    </div>

    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column prop="no" label="编号" width="220" />
      <el-table-column prop="type" label="类型" width="120">
        <template #default="{row}">
          <el-tag :type="row.type==='task'?'':'success'">{{ row.type === 'task' ? '实验记录' : '检验报告' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="experiment" label="检测项目" width="180" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column label="时间" width="170"><template #default="{row}">{{ formatDate(row.created_at) }}</template></el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{row}">
          <el-button size="small" @click="downloadOne(row.no, row.type)"><el-icon><Download /></el-icon></el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !items.length" description="输入委托编号查询该委托下的所有单据" />
  </div>
</template>
