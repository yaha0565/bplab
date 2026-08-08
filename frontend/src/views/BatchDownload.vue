<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Download, Select, Close } from '@element-plus/icons-vue'
import request from '../utils/request'

const commissionNo = ref('')
const loading = ref(false)
const downloading = ref(false)
const items = reactive({ tasks: [], reports: [] })

const selectedTasks = ref([])
const selectedReports = ref([])

const allTasksSelected = computed({
  get: () => items.tasks.length > 0 && selectedTasks.value.length === items.tasks.length,
  set: (v) => { selectedTasks.value = v ? items.tasks.map(t => t.task_no) : [] }
})

const allReportsSelected = computed({
  get: () => items.reports.length > 0 && selectedReports.value.length === items.reports.length,
  set: (v) => { selectedReports.value = v ? items.reports.map(r => r.report_no) : [] }
})

const isIndeterminateTasks = computed(() =>
  selectedTasks.value.length > 0 && selectedTasks.value.length < items.tasks.length
)
const isIndeterminateReports = computed(() =>
  selectedReports.value.length > 0 && selectedReports.value.length < items.reports.length
)

async function loadItems() {
  if (!commissionNo.value.trim()) {
    ElMessage.warning('请输入委托编号')
    return
  }
  loading.value = true
  try {
    const { data } = await request.get(`/export/commission/${commissionNo.value.trim()}/items`)
    items.tasks = data.tasks || []
    items.reports = data.reports || []
    selectedTasks.value = []
    selectedReports.value = []
    if (!items.tasks.length && !items.reports.length) {
      ElMessage.info('该委托暂无可导出的任务或报告')
    } else {
      ElMessage.success(`找到 ${items.tasks.length} 个任务, ${items.reports.length} 个报告`)
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '查询失败')
    items.tasks = []
    items.reports = []
  } finally {
    loading.value = false
  }
}

async function doDownload() {
  if (!selectedTasks.value.length && !selectedReports.value.length) {
    ElMessage.warning('请至少选择一个任务或报告')
    return
  }
  downloading.value = true
  try {
    const resp = await request.post('/export/batch', {
      task_nos: selectedTasks.value,
      report_nos: selectedReports.value,
    }, { responseType: 'blob' })

    const url = URL.createObjectURL(new Blob([resp.data], { type: 'application/zip' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `export_${commissionNo.value.trim()}_${new Date().toISOString().slice(0, 10)}.zip`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('批量导出完成')
  } catch {
    ElMessage.error('批量导出失败')
  } finally {
    downloading.value = false
  }
}

async function downloadSingle(type, no) {
  try {
    const endpoint = type === 'task' ? `/export/record/${no}` : `/export/report/${no}`
    const resp = await request.get(endpoint, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([resp.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `${no}.${type === 'task' ? 'docx' : 'docx'}`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success(`${no} 导出完成`)
  } catch {
    ElMessage.error(`${no} 导出失败`)
  }
}

function statusTag(s) {
  const map = { '已完成': 'success', '检测中': 'warning', '待接收': 'info', '已退回': 'danger', '草稿': 'info', '已发布': 'success' }
  return map[s] || 'info'
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2><el-icon><Download /></el-icon> 一键下载</h2>
      <p class="desc">按委托号批量导出实验记录和报告，选择需要下载的条目一键打包</p>
    </div>

    <!-- 委托查询 -->
    <div class="search-bar">
      <el-input v-model="commissionNo" placeholder="输入委托编号，如 WT20260809001" clearable style="width:320px" @keyup.enter="loadItems">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button type="primary" :loading="loading" @click="loadItems">查询可导出项</el-button>
      <el-button
        type="success"
        :loading="downloading"
        :disabled="!selectedTasks.length && !selectedReports.length"
        @click="doDownload"
      >
        <el-icon><Download /></el-icon> 一键打包下载 ({{ selectedTasks.length + selectedReports.length }})
      </el-button>
    </div>

    <!-- 结果 -->
    <div v-if="items.tasks.length || items.reports.length" style="display:flex;flex-direction:column;gap:16px">
      <!-- 任务列表 -->
      <el-card v-if="items.tasks.length" shadow="never">
        <template #header>
          <div style="display:flex;align-items:center;gap:12px">
            <el-checkbox v-model="allTasksSelected" :indeterminate="isIndeterminateTasks" />
            <span>实验任务 ({{ items.tasks.length }})</span>
            <span style="color:#64748B;font-size:12px">已选 {{ selectedTasks.length }}/{{ items.tasks.length }}</span>
          </div>
        </template>
        <el-checkbox-group v-model="selectedTasks">
          <div class="item-grid">
            <div v-for="t in items.tasks" :key="t.task_no" class="item-row">
              <el-checkbox :value="t.task_no" style="margin-right:12px" />
              <span class="item-no">{{ t.task_no }}</span>
              <el-tag :type="statusTag(t.status)" size="small">{{ t.status }}</el-tag>
              <span class="item-exp">{{ t.experiment }}</span>
              <span class="item-tester">{{ t.tester || '—' }}</span>
              <el-button size="small" text type="primary" :icon="Download" @click="downloadSingle('task', t.task_no)">
                单独下载
              </el-button>
            </div>
          </div>
        </el-checkbox-group>
      </el-card>

      <!-- 报告列表 -->
      <el-card v-if="items.reports.length" shadow="never">
        <template #header>
          <div style="display:flex;align-items:center;gap:12px">
            <el-checkbox v-model="allReportsSelected" :indeterminate="isIndeterminateReports" />
            <span>检验报告 ({{ items.reports.length }})</span>
            <span style="color:#64748B;font-size:12px">已选 {{ selectedReports.length }}/{{ items.reports.length }}</span>
          </div>
        </template>
        <el-checkbox-group v-model="selectedReports">
          <div class="item-grid">
            <div v-for="r in items.reports" :key="r.report_no" class="item-row">
              <el-checkbox :value="r.report_no" style="margin-right:12px" />
              <span class="item-no">{{ r.report_no }}</span>
              <el-tag :type="statusTag(r.status)" size="small">{{ r.status }}</el-tag>
              <span class="item-exp">{{ r.experiment }}</span>
              <span class="item-tester">{{ r.tester || '—' }}</span>
              <el-button size="small" text type="primary" :icon="Download" @click="downloadSingle('report', r.report_no)">
                单独下载
              </el-button>
            </div>
          </div>
        </el-checkbox-group>
      </el-card>
    </div>

    <el-empty v-if="!loading && !items.tasks.length && !items.reports.length && commissionNo" description="该委托暂无可导出的任务或报告" />
    <el-empty v-if="!commissionNo" description="输入委托编号开始查询" />
  </div>
</template>

<style scoped>
.page { max-width: 1000px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-header h2 { display: flex; align-items: center; gap: 8px; font-size: 20px; color: #1E293B; }
.page-header .desc { color: #64748B; margin: 4px 0 0; font-size: 14px; }
.search-bar { display: flex; gap: 12px; margin-bottom: 20px; align-items: center; }
.item-grid { display: flex; flex-direction: column; gap: 4px; }
.item-row { display: flex; align-items: center; padding: 8px 4px; border-bottom: 1px solid #F1F5F9; gap: 8px; }
.item-row:last-child { border-bottom: none; }
.item-no { font-family: monospace; font-weight: 600; color: #1E293B; min-width: 160px; }
.item-exp { color: #475569; flex: 1; }
.item-tester { color: #94A3B8; font-size: 13px; }
</style>
