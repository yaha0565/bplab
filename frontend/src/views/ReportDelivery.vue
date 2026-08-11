<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Search, RefreshLeft, InfoFilled } from '@element-plus/icons-vue'
import request from '../utils/request'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const loading = ref(false)
const list = ref([])
const deliveries = ref([])
const searchNo = ref('')
const commissionNo = ref('')

// 撤回对话框
const showRevoke = ref(false)
const currentReport = ref(null)
const revokeReason = ref('')
const revoking = ref(false)

onMounted(() => { loadList() })

async function loadList() {
  loading.value = true
  try {
    const params = { status: '已发布', limit: 100 }
    if (commissionNo.value.trim()) params.commission_no = commissionNo.value.trim()
    const { data } = await request.get('/reports', { params })
    list.value = data
  } catch { ElMessage.warning('加载报告列表失败') } finally { loading.value = false }
}

async function loadDeliveries(reportNo) {
  try {
    const { data } = await request.get(`/reports/${reportNo}/deliveries`)
    deliveries.value = data
  } catch { deliveries.value = [] }
}

function openRevoke(row) {
  currentReport.value = row
  revokeReason.value = ''
  showRevoke.value = true
  loadDeliveries(row.report_no)
}

async function submitRevoke() {
  if (!revokeReason.value.trim()) { ElMessage.warning('请填写撤回原因'); return }
  revoking.value = true
  try {
    await request.post(`/reports/${currentReport.value.report_no}/revoke`, { reason: revokeReason.value })
    ElMessage.success(`报告 ${currentReport.value.report_no} 已撤回，关联任务已退回修改`)
    showRevoke.value = false
    loadList()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '撤回失败') } finally { revoking.value = false }
}

function searchReport() {
  if (!searchNo.value.trim()) { loadList(); return }
  loading.value = true
  try {
    request.get(`/reports/${searchNo.value.trim()}`).then(({ data }) => {
      list.value = [data]
      loading.value = false
    })
  } catch { ElMessage.warning('报告未找到'); loading.value = false }
}

function formatDate(d) { return d ? new Date(d).toLocaleString('zh-CN') : '—' }
function canRevoke(row) {
  return (user.role === '管理员' || user.role === '质量负责人') && row.status === '已发布'
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2><el-icon><Document /></el-icon> 报告发放管理</h2>
      <div style="display:flex;gap:10px">
        <el-input v-model="commissionNo" placeholder="按委托编号筛选" clearable @keyup.enter="loadList" @clear="loadList" style="width:220px">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-input v-model="searchNo" placeholder="输入报告编号精确搜索" clearable @keyup.enter="searchReport" style="width:280px">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
    </div>

    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="report_no" label="报告编号" width="220" />
      <el-table-column prop="commission_no" label="委托编号" width="180" />
      <el-table-column prop="tester" label="实验员" width="100" />
      <el-table-column prop="quality_inspector" label="签发人" width="100" />
      <el-table-column label="签发日期" width="120"><template #default="{row}">{{ formatDate(row.publish_date) }}</template></el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{row}"><el-tag type="success">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{row}">
          <el-button v-if="canRevoke(row)" size="small" type="warning" @click="openRevoke(row)">
            <el-icon><RefreshLeft /></el-icon> 撤回
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 撤回确认对话框 -->
    <el-dialog v-model="showRevoke" :title="`撤回报告 — ${currentReport?.report_no || ''}`" width="550px" :close-on-click-modal="false">
      <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
        <el-descriptions-item label="委托编号">{{ currentReport?.commission_no }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ currentReport?.status }}</el-descriptions-item>
        <el-descriptions-item label="实验员">{{ currentReport?.tester }}</el-descriptions-item>
        <el-descriptions-item label="签发日期">{{ formatDate(currentReport?.publish_date) }}</el-descriptions-item>
      </el-descriptions>

      <!-- 已有发放记录 -->
      <div v-if="deliveries.length" style="margin-bottom:16px">
        <p style="color:#64748B;font-size:13px;margin-bottom:6px"><el-icon><InfoFilled /></el-icon> 该报告已有 {{ deliveries.length }} 条发放记录：</p>
        <el-table :data="deliveries" size="small" border>
          <el-table-column prop="delivery_method" label="方式" width="80" />
          <el-table-column prop="recipient" label="接收人" width="90" />
          <el-table-column prop="recipient_contact" label="联系方式" width="110" />
          <el-table-column label="发放时间" width="150"><template #default="{row}">{{ formatDate(row.delivered_at) }}</template></el-table-column>
          <el-table-column prop="receipt_status" label="签收状态" width="80" />
        </el-table>
      </div>

      <el-form label-width="90px">
        <el-form-item label="撤回原因" required>
          <el-input v-model="revokeReason" type="textarea" :rows="3" placeholder="请详细说明撤回原因（必填）" />
        </el-form-item>
      </el-form>
      <el-alert type="warning" :closable="false" show-icon style="margin-top:8px"
        title="撤回后，报告状态变为「已撤回」且效力作废，关联实验任务自动退回修改。" />

      <template #footer>
        <el-button @click="showRevoke = false">取消</el-button>
        <el-button type="danger" :loading="revoking" @click="submitRevoke">确认撤回</el-button>
      </template>
    </el-dialog>
  </div>
</template>
