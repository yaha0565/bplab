<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Download, Folder, Files } from '@element-plus/icons-vue'
import request from '../utils/request'

const commissionNo = ref('')
const loading = ref(false)
const downloading = ref(false)

// All document categories for this commission
const docs = reactive({
  commission: null,       // 检验委托单
  sample_register: null,  // 样品登记表
  loan_return: null,      // 借出归还表
  hazardous_waste: null,  // 危废处置表
  records: [],            // 原始记录 (per task)
  reports: [],            // 检验报告 (per report)
  deliveries: [],         // 报告发放登记 (per report)
})

const selected = reactive({
  commission: true,
  sample_register: true,
  loan_return: false,
  hazardous_waste: false,
  records: [],    // task_no[]
  reports: [],    // report_no[]
  deliveries: [], // delivery id[]
})

const totalSelected = computed(() => {
  let n = 0
  if (selected.commission && docs.commission) n++
  if (selected.sample_register && docs.sample_register) n++
  if (selected.loan_return && docs.loan_return) n++
  if (selected.hazardous_waste && docs.hazardous_waste) n++
  n += selected.records.length + selected.reports.length + selected.deliveries.length
  return n
})

const tasksAllSelected = computed({
  get: () => docs.records.length > 0 && selected.records.length === docs.records.length,
  set: (v) => { selected.records = v ? docs.records.map(t => t.task_no) : [] }
})
const reportsAllSelected = computed({
  get: () => docs.reports.length > 0 && selected.reports.length === docs.reports.length,
  set: (v) => { selected.reports = v ? docs.reports.map(r => r.report_no) : [] }
})
const deliveriesAllSelected = computed({
  get: () => docs.deliveries.length > 0 && selected.deliveries.length === docs.deliveries.length,
  set: (v) => { selected.deliveries = v ? docs.deliveries.map(d => d.id) : [] }
})

function resetAll() {
  docs.commission = null
  docs.sample_register = null
  docs.loan_return = null
  docs.hazardous_waste = null
  docs.records = []
  docs.reports = []
  docs.deliveries = []
  selected.commission = true
  selected.sample_register = true
  selected.loan_return = false
  selected.hazardous_waste = false
  selected.records = []
  selected.reports = []
  selected.deliveries = []
}

async function loadItems() {
  if (!commissionNo.value.trim()) { ElMessage.warning('请输入委托编号'); return }
  loading.value = true
  resetAll()
  try {
    const cno = commissionNo.value.trim()

    // Get tasks + reports
    const { data } = await request.get(`/export/commission/${cno}/items`)
    const tasks = data.tasks || []
    const reportsData = data.reports || []

    // Always mark generic forms as available (they exist per commission)
    docs.commission = { no: cno, label: '检验委托单', type: '通用表单' }
    docs.sample_register = { no: cno, label: '样品登记表', type: '通用表单' }
    docs.loan_return = { no: cno, label: '样品借出/归还表', type: '通用表单' }
    docs.hazardous_waste = { no: cno, label: '危废处置表', type: '通用表单' }

    // Records per task
    for (const t of tasks) {
      if (t.task_no) {
        docs.records.push({
          task_no: t.task_no,
          experiment: t.experiment || '',
          status: t.status || '',
          tester: t.tester || '',
          download_url: `/export/record/${t.task_no}`,
        })
      }
    }
    selected.records = docs.records.map(t => t.task_no)

    // Reports
    for (const r of reportsData) {
      if (r.report_no) {
        docs.reports.push({
          report_no: r.report_no,
          experiment: r.experiment || '',
          status: r.status || '',
          tester: r.tester || '',
          download_url: `/export/report/${r.report_no}`,
        })

        // Delivery records for each report
        try {
          const dResp = await request.get(`/reports/${r.report_no}/deliveries`)
          for (const d of (dResp.data || [])) {
            docs.deliveries.push({
              id: d.id,
              report_no: r.report_no,
              recipient: d.recipient || '',
              delivery_method: d.delivery_method || '',
              receipt_status: d.receipt_status || '',
              download_url: `/export/report-delivery/${r.report_no}/export`,
            })
          }
        } catch { /* no deliveries */ }
      }
    }
    selected.reports = docs.reports.map(r => r.report_no)
    selected.deliveries = docs.deliveries.map(d => d.id)

    const total = (docs.commission ? 1 : 0) + (docs.sample_register ? 1 : 0) +
      (docs.loan_return ? 1 : 0) + (docs.hazardous_waste ? 1 : 0) +
      docs.records.length + docs.reports.length + docs.deliveries.length
    if (!total) ElMessage.info('该委托暂无可导出项')
    else ElMessage.success(`找到 ${total} 个可导出项`)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '查询失败')
    resetAll()
  } finally { loading.value = false }
}

// ── Download helpers (with auth) ──
async function downloadBlob(url, filename) {
  try {
    const resp = await request.get(url, { responseType: 'blob' })
    const blob = resp.data || resp
    const objectUrl = URL.createObjectURL(new Blob([blob], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }))
    const a = document.createElement('a')
    a.href = objectUrl; a.download = filename; a.click()
    URL.revokeObjectURL(objectUrl)
    ElMessage.success(`${filename} 下载完成`)
  } catch (e) {
    if (e.response?.status === 403) ElMessage.error(`无权下载 ${filename}`)
    else ElMessage.error(`${filename} 下载失败`)
  }
}

async function downloadSingle(type, item) {
  if (type === 'commission') downloadBlob(`/export/commission/${docs.commission.no}/export`, `委托单_${docs.commission.no}.docx`)
  else if (type === 'sample') downloadBlob(`/export/sample-register/${docs.sample_register.no}/export`, `样品登记_${docs.sample_register.no}.docx`)
  else if (type === 'loan') downloadBlob(`/export/loan-return/${docs.loan_return.no}/export`, `借出归还_${docs.loan_return.no}.docx`)
  else if (type === 'waste') downloadBlob(`/export/hazardous-waste/${docs.hazardous_waste.no}/export`, `危废处置_${docs.hazardous_waste.no}.docx`)
  else if (type === 'record') downloadBlob(item.download_url, `原始记录_${item.task_no}.docx`)
  else if (type === 'report') downloadBlob(item.download_url, `检验报告_${item.report_no}.docx`)
  else if (type === 'delivery') downloadBlob(item.download_url, `发放登记_${item.report_no}.docx`)
}

// ── Batch download with individual downloads (server doesn't have true zip endpoint) ──
async function doBatchDownload() {
  if (!totalSelected.value) { ElMessage.warning('请至少选择一个导出项'); return }
  downloading.value = true
  let success = 0, fail = 0

  // Try batch zip first
  try {
    const resp = await request.post('/export/batch', {
      task_nos: selected.records,
      report_nos: selected.reports,
    }, { responseType: 'blob' })
    const blob = resp.data || resp
    if (blob && blob.size > 100) {
      const url = URL.createObjectURL(new Blob([blob], { type: 'application/zip' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `${commissionNo.value.trim()}_export_${new Date().toISOString().slice(0, 10)}.zip`
      a.click()
      URL.revokeObjectURL(url)
      success += selected.records.length + selected.reports.length
    }
  } catch { /* batch zip failed, fall back to individual downloads */ }

  // Individual downloads for generic forms + any failed batch items
  const dl = async (url, name) => {
    try {
      await downloadBlob(url, name)
      success++
    } catch { fail++ }
  }

  const items = []
  if (selected.commission && docs.commission) items.push(dl(`/export/commission/${docs.commission.no}/export`, `委托单_${docs.commission.no}.docx`))
  if (selected.sample_register && docs.sample_register) items.push(dl(`/export/sample-register/${docs.sample_register.no}/export`, `样品登记_${docs.sample_register.no}.docx`))
  if (selected.loan_return && docs.loan_return) items.push(dl(`/export/loan-return/${docs.loan_return.no}/export`, `借出归还_${docs.loan_return.no}.docx`))
  if (selected.hazardous_waste && docs.hazardous_waste) items.push(dl(`/export/hazardous-waste/${docs.hazardous_waste.no}/export`, `危废处置_${docs.hazardous_waste.no}.docx`))

  for (const id of selected.deliveries) {
    const d = docs.deliveries.find(x => x.id === id)
    if (d) items.push(dl(d.download_url, `发放登记_${d.report_no}.docx`))
  }

  await Promise.allSettled(items)

  if (fail > 0) ElMessage.warning(`下载完成：${success} 个成功, ${fail} 个失败`)
  else ElMessage.success(`下载完成：${success} 个文件`)
  downloading.value = false
}

function statusTag(s) {
  const m = { '已完成': 'success', '检测中': 'warning', '待接收': 'info', '已退回': 'danger', '草稿': 'info', '已发布': 'success' }
  return m[s] || 'info'
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2><el-icon><Download /></el-icon> 一键下载</h2>
      <p class="desc">按委托号导出所有关联文档（通用表单 / 原始记录 / 检验报告 / 发放登记），勾选后一键打包下载</p>
    </div>

    <div class="search-bar">
      <el-input v-model="commissionNo" placeholder="输入委托编号，如 WT20260811001" clearable style="width:320px" @keyup.enter="loadItems">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button type="primary" :loading="loading" @click="loadItems">查询可导出项</el-button>
      <el-button type="success" :loading="downloading" :disabled="!totalSelected" @click="doBatchDownload">
        <el-icon><Download /></el-icon> 一键下载 ({{ totalSelected }})
      </el-button>
    </div>

    <div v-if="docs.commission || docs.records.length || docs.reports.length"
         style="display:flex; flex-direction:column; gap:14px">

      <!-- ═══ 通用表单 ═══ -->
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span><el-icon><Files /></el-icon> 通用表单</span>
            <span class="card-count">{{ [docs.commission, docs.sample_register, docs.loan_return, docs.hazardous_waste].filter(Boolean).length }} 项</span>
          </div>
        </template>
        <div class="item-grid">
          <!-- 委托单 -->
          <div v-if="docs.commission" class="item-row">
            <el-checkbox v-model="selected.commission" />
            <el-tag type="warning" size="small">委托单</el-tag>
            <span class="item-label">检验委托单</span>
            <span class="item-no">{{ docs.commission.no }}</span>
            <el-button size="small" text type="primary" :icon="Download" @click="downloadSingle('commission')">下载</el-button>
          </div>
          <!-- 样品登记 -->
          <div v-if="docs.sample_register" class="item-row">
            <el-checkbox v-model="selected.sample_register" />
            <el-tag type="info" size="small">登记</el-tag>
            <span class="item-label">样品登记表</span>
            <span class="item-no">{{ docs.sample_register.no }}</span>
            <el-button size="small" text type="primary" :icon="Download" @click="downloadSingle('sample')">下载</el-button>
          </div>
          <!-- 借出归还 -->
          <div v-if="docs.loan_return" class="item-row">
            <el-checkbox v-model="selected.loan_return" />
            <el-tag type="" size="small">借出</el-tag>
            <span class="item-label">样品借出/归还表</span>
            <span class="item-no">{{ docs.loan_return.no }}</span>
            <el-button size="small" text type="primary" :icon="Download" @click="downloadSingle('loan')">下载</el-button>
          </div>
          <!-- 危废 -->
          <div v-if="docs.hazardous_waste" class="item-row">
            <el-checkbox v-model="selected.hazardous_waste" />
            <el-tag type="danger" size="small">危废</el-tag>
            <span class="item-label">危废处置表</span>
            <span class="item-no">{{ docs.hazardous_waste.no }}</span>
            <el-button size="small" text type="primary" :icon="Download" @click="downloadSingle('waste')">下载</el-button>
          </div>
        </div>
      </el-card>

      <!-- ═══ 原始记录 ═══ -->
      <el-card v-if="docs.records.length" shadow="never">
        <template #header>
          <div class="card-header">
            <el-checkbox v-model="tasksAllSelected"
              :indeterminate="selected.records.length > 0 && selected.records.length < docs.records.length" />
            <span>原始记录 ({{ docs.records.length }})</span>
            <span class="card-count">已选 {{ selected.records.length }}/{{ docs.records.length }}</span>
          </div>
        </template>
        <el-checkbox-group v-model="selected.records">
          <div class="item-grid">
            <div v-for="t in docs.records" :key="t.task_no" class="item-row">
              <el-checkbox :value="t.task_no" />
              <span class="item-no">{{ t.task_no }}</span>
              <el-tag :type="statusTag(t.status)" size="small">{{ t.status }}</el-tag>
              <span class="item-exp">{{ t.experiment }}</span>
              <span class="item-tester">{{ t.tester || '—' }}</span>
              <el-button size="small" text type="primary" :icon="Download" @click="downloadSingle('record', t)">下载</el-button>
            </div>
          </div>
        </el-checkbox-group>
      </el-card>

      <!-- ═══ 检验报告 ═══ -->
      <el-card v-if="docs.reports.length" shadow="never">
        <template #header>
          <div class="card-header">
            <el-checkbox v-model="reportsAllSelected"
              :indeterminate="selected.reports.length > 0 && selected.reports.length < docs.reports.length" />
            <span>检验报告 ({{ docs.reports.length }})</span>
            <span class="card-count">已选 {{ selected.reports.length }}/{{ docs.reports.length }}</span>
          </div>
        </template>
        <el-checkbox-group v-model="selected.reports">
          <div class="item-grid">
            <div v-for="r in docs.reports" :key="r.report_no" class="item-row">
              <el-checkbox :value="r.report_no" />
              <span class="item-no">{{ r.report_no }}</span>
              <el-tag :type="statusTag(r.status)" size="small">{{ r.status }}</el-tag>
              <span class="item-exp">{{ r.experiment }}</span>
              <span class="item-tester">{{ r.tester || '—' }}</span>
              <el-button size="small" text type="primary" :icon="Download" @click="downloadSingle('report', r)">下载</el-button>
            </div>
          </div>
        </el-checkbox-group>
      </el-card>

      <!-- ═══ 报告发放登记 ═══ -->
      <el-card v-if="docs.deliveries.length" shadow="never">
        <template #header>
          <div class="card-header">
            <el-checkbox v-model="deliveriesAllSelected"
              :indeterminate="selected.deliveries.length > 0 && selected.deliveries.length < docs.deliveries.length" />
            <span>报告发放登记 ({{ docs.deliveries.length }})</span>
            <span class="card-count">已选 {{ selected.deliveries.length }}/{{ docs.deliveries.length }}</span>
          </div>
        </template>
        <el-checkbox-group v-model="selected.deliveries">
          <div class="item-grid">
            <div v-for="d in docs.deliveries" :key="`d-${d.id}`" class="item-row">
              <el-checkbox :value="d.id" />
              <span class="item-no">{{ d.report_no }}</span>
              <el-tag type="primary" size="small">{{ d.delivery_method || '发放' }}</el-tag>
              <span class="item-exp">{{ d.recipient || '—' }}</span>
              <span class="item-tester">{{ d.receipt_status || '—' }}</span>
              <el-button size="small" text type="primary" :icon="Download" @click="downloadSingle('delivery', d)">下载</el-button>
            </div>
          </div>
        </el-checkbox-group>
      </el-card>
    </div>

    <el-empty v-if="!loading && !docs.commission && !docs.records.length && !docs.reports.length && commissionNo"
      description="该委托暂无可导出项" />
    <el-empty v-if="!commissionNo" description="输入委托编号开始查询" />
  </div>
</template>

<style scoped>
.page { max-width: 1100px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-header h2 { display: flex; align-items: center; gap: 8px; font-size: 20px; color: #1E293B; }
.page-header .desc { color: #64748B; margin: 4px 0 0; font-size: 14px; }
.search-bar { display: flex; gap: 12px; margin-bottom: 20px; align-items: center; }
.card-header { display: flex; align-items: center; gap: 12px; }
.card-count { color: #94A3B8; font-size: 12px; margin-left: auto; }
.item-grid { display: flex; flex-direction: column; gap: 4px; }
.item-row { display: flex; align-items: center; padding: 8px 4px; border-bottom: 1px solid #F1F5F9; gap: 8px; }
.item-row:last-child { border-bottom: none; }
.item-label { color: #475569; min-width: 120px; }
.item-no { font-family: monospace; font-weight: 600; color: #1E293B; min-width: 160px; }
.item-exp { color: #475569; flex: 1; }
.item-tester { color: #94A3B8; font-size: 13px; min-width: 80px; }
</style>
