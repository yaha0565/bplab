<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Files, Search, Download, View } from '@element-plus/icons-vue'
import request from '../utils/request'

const loading = ref(false)
const commissionNo = ref('')
const items = ref([])

// ── Preview state ──
const previewVisible = ref(false)
const previewHtml = ref('')
const previewLoading = ref(false)
const previewTitle = ref('')

// ── Document type registry ──
const docTypes = [
  { code: 'record',    label: '原始记录',     tagType: '' },
  { code: 'commission', label: '检验委托单',   tagType: 'warning' },
  { code: 'sample_reg', label: '样品登记表',   tagType: 'info' },
  { code: 'loan_return', label: '借出归还表',  tagType: '' },
  { code: 'hazardous', label: '危废处置表',    tagType: 'danger' },
  { code: 'report',    label: '检验报告',      tagType: 'success' },
  { code: 'delivery',  label: '报告发放登记',  tagType: 'primary' },
]

function docTypeLabel(code) {
  const dt = docTypes.find(d => d.code === code)
  return dt ? dt.label : code
}
function docTagType(code) {
  const dt = docTypes.find(d => d.code === code)
  return dt ? dt.tagType : ''
}

async function query() {
  if (!commissionNo.value.trim()) { ElMessage.warning('请输入委托编号'); return }
  loading.value = true
  items.value = []
  try {
    const cno = commissionNo.value.trim()

    // 1. Get tasks + reports
    const { data } = await request.get(`/export/commission/${cno}/items`)
    const tasks = data.tasks || []
    const reports = data.reports || []

    // 2. Commission info
    let commissionInfo = {}
    try {
      const cResp = await request.get('/commissions', { params: { search: cno } })
      const clist = Array.isArray(cResp.data) ? cResp.data : (cResp.data?.items || [])
      commissionInfo = clist.find(c => c.commission_no === cno) || {}
    } catch { /* ignore */ }

    const result = []

    // (A) 原始记录 per task
    for (const t of tasks) {
      if (t.task_no) {
        result.push({
          id: `record-${t.task_no}`,
          code: 'record',
          no: t.task_no,
          label: `原始记录 — ${t.experiment || t.task_no}`,
          status: t.status || '',
          experiment: t.experiment || '',
          preview_url: `/export/record/${t.task_no}/preview`,
          download_url: `/export/record/${t.task_no}`,
        })
      }
    }

    // (B) 检验委托单
    result.push({
      id: `commission-${cno}`,
      code: 'commission',
      no: cno,
      label: '检验委托单',
      status: commissionInfo.status || '',
      preview_url: `/export/commission/${cno}/preview`,
      download_url: `/export/commission/${cno}/export`,
    })

    // (C) 样品登记表
    result.push({
      id: `sample-reg-${cno}`,
      code: 'sample_reg',
      no: cno,
      label: '样品登记表',
      status: '',
      preview_url: `/export/sample-register/${cno}/preview`,
      download_url: `/export/sample-register/${cno}/export`,
    })

    // (D) 借出归还表
    result.push({
      id: `loan-${cno}`,
      code: 'loan_return',
      no: cno,
      label: '样品借出/归还表',
      status: '',
      preview_url: `/export/loan-return/${cno}/preview`,
      download_url: `/export/loan-return/${cno}/export`,
    })

    // (E) 危废处置表
    result.push({
      id: `waste-${cno}`,
      code: 'hazardous',
      no: cno,
      label: '危废处置表',
      status: '',
      preview_url: `/export/hazardous-waste/${cno}/preview`,
      download_url: `/export/hazardous-waste/${cno}/export`,
    })

    // (F) 检验报告 per report
    for (const r of reports) {
      if (r.report_no) {
        result.push({
          id: `report-${r.report_no}`,
          code: 'report',
          no: r.report_no,
          label: `检验报告 — ${r.report_no}`,
          status: r.status || '',
          preview_url: `/reports/${r.report_no}/preview`,
          download_url: `/reports/${r.report_no}/export`,
        })

        // (G) 报告发放登记 per report
        try {
          const dResp = await request.get(`/reports/${r.report_no}/deliveries`)
          for (const d of (dResp.data || [])) {
            result.push({
              id: `delivery-${d.id}`,
              code: 'delivery',
              no: r.report_no,
              label: `报告发放 — ${d.delivery_method || ''} → ${d.recipient || ''}`,
              status: d.receipt_status || '',
              preview_url: `/export/report-delivery/${r.report_no}/preview`,
              download_url: `/export/report-delivery/${r.report_no}`,
            })
          }
        } catch { /* no deliveries */ }
      }
    }

    items.value = result
    if (!result.length) ElMessage.info('该委托暂无单据')
    else ElMessage.success(`找到 ${result.length} 条单据`)
  } catch (e) {
    ElMessage.warning('查询失败，请检查委托编号')
    items.value = []
  } finally { loading.value = false }
}

// ── Preview (iframe via srcdoc with auth) ──
async function openPreview(item) {
  previewTitle.value = item.label
  previewVisible.value = true
  previewLoading.value = true
  previewHtml.value = ''
  try {
    const resp = await request.get(item.preview_url, { responseType: 'text' })
    previewHtml.value = typeof resp === 'string' ? resp : resp.data
  } catch (e) {
    previewHtml.value = `<html><body style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;color:#EF4444"><div>⚠️ 预览失败：${e.response?.status === 403 ? '无权限访问' : e.response?.data?.detail || e.message}</div></body></html>`
  } finally {
    previewLoading.value = false
  }
}

// ── Download (blob with auth) ──
async function downloadDoc(item) {
  try {
    const resp = await request.get(item.download_url, { responseType: 'blob' })
    const blob = resp.data || resp
    const url = URL.createObjectURL(new Blob([blob], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `${item.no}_${docTypeLabel(item.code)}.docx`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('下载完成')
  } catch (e) {
    if (e.response?.status === 403) ElMessage.error('无权限下载此文档')
    else ElMessage.error('下载失败')
  }
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2><el-icon><Files /></el-icon> 单据中心</h2>
      <p class="desc">按委托编号查询所有关联单据（原始记录/委托单/样品登记/借出归还/危废/报告/发放登记），支持在线预览与下载</p>
    </div>

    <div style="display:flex;gap:12px;align-items:center;margin-bottom:16px">
      <el-input v-model="commissionNo" placeholder="输入委托编号（如 WT20260811001）" clearable @keyup.enter="query" style="width:360px">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button type="primary" @click="query">查询</el-button>
      <span v-if="items.length" style="color:#64748B;font-size:13px">共 {{ items.length }} 条单据</span>
    </div>

    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column prop="label" label="单据名称" min-width="240" show-overflow-tooltip />
      <el-table-column label="类型" width="120">
        <template #default="{row}">
          <el-tag :type="docTagType(row.code)" size="small">{{ docTypeLabel(row.code) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="no" label="编号" width="220" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="90" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{row}">
          <el-button size="small" text type="primary" :icon="View" @click="openPreview(row)">预览</el-button>
          <el-button size="small" text type="success" :icon="Download" @click="downloadDoc(row)">下载</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !items.length" description="输入委托编号查询该委托下的所有单据" />

    <!-- Preview dialog -->
    <el-dialog v-model="previewVisible" :title="previewTitle" width="75%" top="4vh" :close-on-click-modal="false" destroy-on-close>
      <div v-loading="previewLoading" style="min-height:300px">
        <div v-if="previewHtml" style="border:1px solid #E2E8F0;border-radius:6px;overflow:hidden">
          <iframe :srcdoc="previewHtml" style="width:100%;height:70vh;border:none" sandbox="allow-same-origin" />
        </div>
        <el-empty v-else-if="!previewLoading" description="暂无预览内容" />
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header { margin-bottom: 16px; }
.page-header h2 { display: flex; align-items: center; gap: 8px; font-size: 20px; }
.page-header .desc { color: #64748B; margin-top: 4px; font-size: 14px; }
</style>
