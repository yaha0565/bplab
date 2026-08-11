<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import request from '../utils/request'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

const reports = ref([])
const loading = ref(true)
const selectedReport = ref(null)
const reportDetail = ref(null)
const reportDocuments = ref([])
const detailLoading = ref(false)
const previewTab = ref('')
const previewLoading = ref(false)
const previewHtml = ref('')
const previewVisible = ref(false)
const previewTitle = ref('')

// Filters
const statusFilter = ref('')
const experimentFilter = ref('')

// Dialogs
const reviewDialogVisible = ref(false)
const reviewDecision = ref('通过')
const reviewComment = ref('')
const reviewing = ref(false)

const voidDialogVisible = ref(false)
const voidReason = ref('')
const voidAction = ref('void')
const voiding = ref(false)

const deliveryDialogVisible = ref(false)
const deliveryForm = ref({
  delivery_method: '自取',
  recipient: '',
  recipient_contact: '',
  tracking_no: '',
  note: '',
})
const delivering = ref(false)

const userRole = computed(() => authStore.user?.role || '')
const userName = computed(() => authStore.user?.username || '')

function getStatusType(status) {
  const map = {
    '待质量审核': 'warning', '待管理员签发': 'primary', '已发布': 'success',
    '质量退回': 'danger', '已撤回': 'info', '已作废': 'danger', '草稿': 'info',
  }
  return map[status] || 'info'
}

const filteredReports = computed(() => {
  let list = reports.value
  if (statusFilter.value) list = list.filter(r => r.status === statusFilter.value)
  if (experimentFilter.value) list = list.filter(r => (r.experiment || '').includes(experimentFilter.value))
  return list
})

const statusOptions = computed(() => {
  const seen = new Set()
  for (const r of reports.value) seen.add(r.status)
  return [...seen]
})

async function loadReports() {
  loading.value = true
  try {
    const { data } = await request.get('/reports', { params: { limit: 100 } })
    reports.value = data
  } finally {
    loading.value = false
  }
}

async function selectReport(report) {
  selectedReport.value = report
  detailLoading.value = true
  reportDocuments.value = []
  previewTab.value = ''
  previewHtml.value = ''
  try {
    const [detailRes, docsRes] = await Promise.all([
      request.get(`/reports/${report.report_no}`),
      request.get(`/reports/${report.report_no}/documents`),
    ])
    reportDetail.value = detailRes.data
    reportDocuments.value = docsRes.data?.documents || []
    // Auto-select first available document
    const first = reportDocuments.value.find(d => d.available && d.preview_url)
    if (first) previewTab.value = first.code
  } catch (e) {
    ElMessage.error('加载报告详情失败')
  } finally {
    detailLoading.value = false
  }
}

async function loadPreview(doc) {
  if (!doc?.preview_url || previewLoading.value) return
  previewTab.value = doc.code
  previewLoading.value = true
  previewTitle.value = doc.label
  previewHtml.value = ''
  try {
    const resp = await request.get(doc.preview_url, { responseType: 'text' })
    previewHtml.value = typeof resp === 'string' ? resp : resp.data
  } catch (e) {
    previewHtml.value = `<html><body style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;color:#EF4444"><div>⚠️ 预览失败：${e.response?.data?.detail || e.message}</div></body></html>`
  } finally {
    previewLoading.value = false
  }
}

function downloadDocument(doc) {
  if (!doc?.download_url) {
    ElMessage.warning('该文档暂无下载')
    return
  }
  window.open(`/api/v1${doc.download_url.replace('/api/v1', '')}`, '_blank')
}

// Watch previewTab change
watch(previewTab, (code) => {
  if (!code) return
  const doc = reportDocuments.value.find(d => d.code === code)
  if (doc && doc.preview_url) loadPreview(doc)
})

// ── Quality Review ──
const canQualityReview = computed(() => {
  if (userRole.value !== '质量负责人') return false
  if (!selectedReport.value) return false
  return ['待质量审核', '待管理员签发'].includes(selectedReport.value.status)
})

function openQualityReview() {
  reviewDecision.value = '通过'
  reviewComment.value = ''
  reviewDialogVisible.value = true
}

// ── Admin Approve ──
const canApprove = computed(() => {
  if (userRole.value !== '管理员') return false
  if (!selectedReport.value) return false
  return selectedReport.value.status === '待管理员签发'
})

function openApprove() {
  reviewDecision.value = '通过'
  reviewComment.value = ''
  reviewDialogVisible.value = true
}

// ── Void / Correct ──
const canVoid = computed(() => {
  if (userRole.value !== '管理员') return false
  if (!selectedReport.value) return false
  return selectedReport.value.status === '已发布'
})

function openVoidDialog(action) {
  voidAction.value = action
  voidReason.value = ''
  voidDialogVisible.value = true
}

async function submitVoid() {
  if (!voidReason.value.trim()) { ElMessage.warning('请填写原因'); return }
  voiding.value = true
  try {
    const rn = selectedReport.value.report_no
    const endpoint = voidAction.value === 'void'
      ? `/reports/${rn}/void`
      : `/reports/${rn}/correct`
    await request.post(endpoint, { reason: voidReason.value, action: voidAction.value })
    ElMessage.success(voidAction.value === 'void' ? '报告已作废' : '报告已标记更正')
    voidDialogVisible.value = false
    await loadReports()
    if (selectedReport.value) await selectReport(selectedReport.value)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    voiding.value = false
  }
}

// ── Delivery ──
const canDeliver = computed(() => {
  if (!selectedReport.value) return false
  if (selectedReport.value.status !== '已发布') return false
  return userRole.value === '样品管理员' || userRole.value === '管理员'
})

function openDelivery() {
  deliveryForm.value = {
    delivery_method: '自取',
    recipient: '',
    recipient_contact: '',
    tracking_no: '',
    note: '',
  }
  deliveryDialogVisible.value = true
}

async function submitDelivery() {
  if (!deliveryForm.value.recipient.trim()) { ElMessage.warning('请输入接收人'); return }
  delivering.value = true
  try {
    // Build payload matching DeliverReportRequest: fold tracking_no into note
    const payload = {
      delivery_method: deliveryForm.value.delivery_method,
      recipient: deliveryForm.value.recipient,
      recipient_contact: deliveryForm.value.recipient_contact,
      note: deliveryForm.value.tracking_no
        ? `快递单号：${deliveryForm.value.tracking_no}；${deliveryForm.value.note || ''}`
        : (deliveryForm.value.note || ''),
    }
    await request.post(`/reports/${selectedReport.value.report_no}/delivery`, payload)
    ElMessage.success('报告发放已登记')
    deliveryDialogVisible.value = false
    await selectReport(selectedReport.value)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '发放失败')
  } finally {
    delivering.value = false
  }
}

// ── Submit review/approve ──
async function submitReview() {
  if (reviewDecision.value === '退回' && !reviewComment.value.trim()) {
    ElMessage.warning('退回时必须填写意见'); return
  }
  reviewing.value = true
  try {
    const rn = selectedReport.value.report_no
    // Quality review vs admin approve use different endpoints
    if (canApprove.value && selectedReport.value.status === '待管理员签发') {
      await request.post(`/reports/${rn}/approve`, {
        decision: reviewDecision.value,
        comment: reviewComment.value,
      })
    } else {
      await request.post(`/reports/${rn}/quality-review`, {
        decision: reviewDecision.value,
        comment: reviewComment.value,
      })
    }
    ElMessage.success(reviewDecision.value === '通过'
      ? (canApprove.value ? '报告已签发！' : '质量审核通过，报告待管理员签发')
      : '报告已退回')
    reviewDialogVisible.value = false
    await loadReports()
    if (selectedReport.value) await selectReport(selectedReport.value)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    reviewing.value = false
  }
}

// ── View original record ──
function viewOriginalRecord() {
  const rec = reportDetail.value?.linked_record
  if (!rec) { ElMessage.warning('未关联原始记录'); return }
  router.push(`/records/${rec.record_no}/v${rec.version}`)
}

onMounted(loadReports)
</script>

<template>
  <div class="rc-page">
    <!-- Header -->
    <div class="rc-header">
      <div>
        <h1>报告中心</h1>
        <div class="rc-subtitle">
          {{ userRole === '质量负责人' ? '质量负责人：预览确认 → 管理员签发' :
             userRole === '管理员' ? '管理员（授权签字人）：最终审核签发 · 作废更正 · 报告发放' :
             userRole === '样品管理员' ? '样品管理员：报告发放登记' : '报告管理' }}
        </div>
      </div>
      <div style="display:flex;gap:8px">
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable size="small" style="width:140px">
          <el-option v-for="s in statusOptions" :key="s" :value="s" :label="s" />
        </el-select>
        <el-button @click="loadReports" :loading="loading" size="small">刷新</el-button>
      </div>
    </div>

    <!-- Dual-pane layout -->
    <div class="rc-panes">
      <!-- Left: Report List -->
      <div class="rc-left">
        <el-card shadow="never" class="rc-table-card">
          <template #header>
            <span>{{ filteredReports.length }} 份报告</span>
          </template>
          <el-table
            :data="filteredReports"
            v-loading="loading"
            stripe
            size="small"
            highlight-current-row
            @row-click="selectReport"
            :row-class-name="({row}) => row.report_no === selectedReport?.report_no ? 'rc-selected-row' : ''"
            max-height="calc(100vh - 220px)"
          >
            <el-table-column prop="report_no" label="报告编号" width="195" />
            <el-table-column prop="status" label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="commission_no" label="委托编号" width="170" />
            <el-table-column prop="tester" label="实验员" width="90" />
            <el-table-column prop="verifier" label="复核员" width="90" />
            <el-table-column prop="quality_inspector" label="质量负责人" width="100" />
            <el-table-column prop="created_at" label="创建时间" width="155" />
          </el-table>
        </el-card>
      </div>

      <!-- Right: Document Center -->
      <div class="rc-right">
        <template v-if="!selectedReport">
          <el-empty description="← 选择一份报告查看详情" style="margin-top:120px" />
        </template>

        <template v-else>
          <!-- Report meta + actions -->
          <el-card shadow="never" class="rc-meta-card">
            <div class="rc-meta-row">
              <div class="rc-meta-main">
                <div class="rc-report-no">
                  {{ selectedReport.report_no }}
                  <el-tag :type="getStatusType(selectedReport.status)" size="small" style="margin-left:8px">{{ selectedReport.status }}</el-tag>
                </div>
                <div class="rc-meta-sub">
                  <span>委托：{{ selectedReport.commission_no }}</span>
                  <span>实验员：{{ selectedReport.tester || '-' }}</span>
                  <span>复核员：{{ selectedReport.verifier || '-' }}</span>
                  <span>质量负责人：{{ selectedReport.quality_inspector || '-' }}</span>
                </div>
              </div>
              <div class="rc-actions">
                <el-button v-if="canQualityReview" type="warning" size="small" @click="openQualityReview">质量审核</el-button>
                <el-button v-if="canApprove" type="primary" size="small" @click="openApprove">签发</el-button>
                <el-button v-if="canVoid" size="small" @click="openVoidDialog('void')">作废</el-button>
                <el-button v-if="canVoid" size="small" @click="openVoidDialog('correct')">更正</el-button>
                <el-button v-if="canVoid" type="danger" size="small" plain @click="async () => { await request.post(`/reports/${selectedReport.report_no}/revoke`); ElMessage.success('已撤回'); loadReports(); }">撤回</el-button>
                <el-button v-if="canDeliver" type="success" size="small" @click="openDelivery">发放登记</el-button>
                <el-button size="small" @click="viewOriginalRecord" v-if="reportDetail?.linked_record">原始记录</el-button>
              </div>
            </div>

            <!-- Action history -->
            <div v-if="reportDetail?.actions?.length" style="margin-top:8px;padding-top:8px;border-top:1px solid #E2E8F0">
              <div style="font-size:12px;font-weight:600;color:#475569;margin-bottom:4px">操作记录</div>
              <el-timeline>
                <el-timeline-item
                  v-for="(act, i) in reportDetail.actions.slice(-6)"
                  :key="i"
                  :timestamp="act.created_at"
                  size="small"
                  :type="act.action.includes('退回') || act.action.includes('作废') ? 'danger' : 'primary'"
                >
                  <strong>{{ act.actor }}</strong> — {{ act.action }}
                  <span v-if="act.comment" style="color:#64748B;margin-left:4px">{{ act.comment }}</span>
                </el-timeline-item>
              </el-timeline>
            </div>
          </el-card>

          <!-- Document tabs -->
          <el-card shadow="never" class="rc-docs-card" v-loading="detailLoading">
            <el-tabs v-model="previewTab" type="card" class="rc-doc-tabs">
              <el-tab-pane
                v-for="doc in reportDocuments"
                :key="doc.code"
                :label="doc.label"
                :name="doc.code"
                :disabled="!doc.available"
              >
                <template #label>
                  <span :style="{opacity: doc.available ? 1 : 0.4}">
                    {{ doc.type }}
                    <el-tag v-if="!doc.available" size="small" type="info" style="margin-left:4px">暂无</el-tag>
                  </span>
                </template>
              </el-tab-pane>
            </el-tabs>

            <!-- Preview area -->
            <div class="rc-preview-area" v-loading="previewLoading">
              <template v-if="!previewTab">
                <el-empty description="选择上方标签页查看文档预览" />
              </template>
              <template v-else>
                <!-- Action bar -->
                <div class="rc-preview-toolbar" v-if="reportDocuments.find(d=>d.code===previewTab)">
                  <span style="font-weight:500;font-size:13px">{{ previewTitle }}</span>
                  <div>
                    <el-button
                      size="small"
                      @click="downloadDocument(reportDocuments.find(d=>d.code===previewTab))"
                      :disabled="!reportDocuments.find(d=>d.code===previewTab)?.download_url"
                    >📥 下载</el-button>
                  </div>
                </div>
                <!-- iframe preview -->
                <div v-if="previewHtml" class="rc-iframe-wrap">
                  <iframe :srcdoc="previewHtml" class="rc-iframe" sandbox="allow-same-origin" />
                </div>
                <el-empty v-else-if="!previewLoading" description="该文档暂无在线预览" />
              </template>
            </div>
          </el-card>
        </template>
      </div>
    </div>

    <!-- Review / Approve Dialog -->
    <el-dialog
      v-model="reviewDialogVisible"
      :title="canApprove ? '管理员（授权签字人）最终签发' : '质量负责人预览确认'"
      width="500px" :close-on-click-modal="false"
    >
      <template v-if="selectedReport">
        <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
          <el-descriptions-item label="报告编号">{{ selectedReport.report_no }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ selectedReport.status }}</el-descriptions-item>
          <el-descriptions-item label="实验员">{{ selectedReport.tester }}</el-descriptions-item>
          <el-descriptions-item label="复核员">{{ selectedReport.verifier }}</el-descriptions-item>
        </el-descriptions>

        <el-alert v-if="!canApprove" type="warning" :closable="false" show-icon style="margin-bottom:16px">
          <template #title>请先在右侧预览报告内容，确认无误后再做审核决定</template>
        </el-alert>

        <el-form label-width="100px">
          <el-form-item label="审核决定" required>
            <el-radio-group v-model="reviewDecision">
              <el-radio value="通过">
                {{ canApprove ? '批准 — 最终审核并签发报告' : '通过 — 预览确认，提交管理员签发' }}
              </el-radio>
              <el-radio value="退回">
                {{ canApprove ? '退回 — 退回质量负责人重新审核' : '退回 — 退回整改（任务将退回修改）' }}
              </el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="审核意见">
            <el-input v-model="reviewComment" type="textarea" :rows="3" placeholder="审核意见（退回时必填）" />
          </el-form-item>
          <el-form-item v-if="!canApprove">
            <el-alert type="info" :closable="false" show-icon style="width:100%">
              质量负责人仅进行报告内容预览确认，不形成电子签字。
            </el-alert>
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReview" :loading="reviewing">
          {{ reviewDecision === '通过' ? '确认通过' : '确认退回' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Void / Correct Dialog -->
    <el-dialog
      v-model="voidDialogVisible"
      :title="voidAction === 'void' ? '作废报告' : '更正并重新签发'"
      width="500px" :close-on-click-modal="false"
    >
      <el-alert type="error" :closable="false" show-icon style="margin-bottom:16px">
        <template #title>
          {{ voidAction === 'void'
            ? '作废后原报告立即停止使用，操作不可撤销且永久写入修改日志。'
            : '更正后将作废当前报告，需重新走审核签发流程。' }}
        </template>
      </el-alert>
      <el-form label-width="80px">
        <el-form-item :label="voidAction === 'void' ? '作废原因' : '更正原因'" required>
          <el-input v-model="voidReason" type="textarea" :rows="3" placeholder="请详细说明原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="voidDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="submitVoid" :loading="voiding">
          {{ voidAction === 'void' ? '确认作废' : '确认更正' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Delivery Dialog -->
    <el-dialog v-model="deliveryDialogVisible" title="报告发放登记" width="520px" :close-on-click-modal="false">
      <template v-if="selectedReport">
        <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
          <el-descriptions-item label="报告编号">{{ selectedReport.report_no }}</el-descriptions-item>
          <el-descriptions-item label="委托编号">{{ selectedReport.commission_no }}</el-descriptions-item>
        </el-descriptions>
        <el-form label-width="100px">
          <el-form-item label="发放方式" required>
            <el-select v-model="deliveryForm.delivery_method" style="width:100%">
              <el-option value="自取" label="自取" />
              <el-option value="邮寄" label="邮寄" />
              <el-option value="电子邮件" label="电子邮件" />
              <el-option value="其他" label="其他" />
            </el-select>
          </el-form-item>
          <el-form-item label="接收人" required>
            <el-input v-model="deliveryForm.recipient" placeholder="接收人姓名" />
          </el-form-item>
          <el-form-item label="联系方式">
            <el-input v-model="deliveryForm.recipient_contact" placeholder="电话/邮箱" />
          </el-form-item>
          <el-form-item label="快递单号" v-if="deliveryForm.delivery_method === '邮寄'">
            <el-input v-model="deliveryForm.tracking_no" placeholder="快递单号" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="deliveryForm.note" type="textarea" :rows="2" placeholder="备注" />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="deliveryDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitDelivery" :loading="delivering">确认发放</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.rc-page { max-width: 100%; }
.rc-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
.rc-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
.rc-subtitle { font-size: 13px; color: #64748B; margin-top: 4px; }
.rc-panes { display: flex; gap: 16px; align-items: flex-start; }
.rc-left { flex: 0 0 480px; min-width: 0; }
.rc-right { flex: 1; min-width: 0; }
.rc-table-card { margin-bottom: 0; }
.rc-selected-row { background-color: #EFF6FF !important; }
.rc-meta-card { margin-bottom: 12px; }
.rc-meta-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.rc-meta-main { flex: 1; }
.rc-report-no { font-size: 17px; font-weight: 700; color: #0F172A; }
.rc-meta-sub { font-size: 12px; color: #64748B; margin-top: 4px; display: flex; gap: 16px; flex-wrap: wrap; }
.rc-actions { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.rc-docs-card { margin-bottom: 0; }
.rc-doc-tabs { margin-top: -12px; }
.rc-preview-area { min-height: 400px; }
.rc-preview-toolbar { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; margin-bottom: 8px; }
.rc-iframe-wrap { border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden; }
.rc-iframe { width: 100%; height: calc(100vh - 420px); min-height: 500px; border: none; }

@media (max-width: 1200px) {
  .rc-panes { flex-direction: column; }
  .rc-left { flex: none; width: 100%; }
}
</style>
