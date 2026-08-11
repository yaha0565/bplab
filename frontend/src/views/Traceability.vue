<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Link, Clock, Document, Picture } from '@element-plus/icons-vue'
import request from '../utils/request'

const activeTab = ref('attachments')
const loading = ref(false)

// 附件
const attFilters = reactive({ commission_no: '', task_no: '', attachment_type: '', search: '' })
const attachments = ref([])

// 审计日志
const auditFilters = reactive({ entity_type: '', entity_id: '', actor: '', action: '', commission_no: '' })
const auditLogs = ref([])

// 修改日志
const modFilters = reactive({ entity_type: '', entity_id: '', actor: '', commission_no: '' })
const modifications = ref([])

// 委托追溯聚合
const traceCommissionNo = ref('')
const traceResult = ref(null)
const traceLoading = ref(false)

const attTypeMap = { photo: '照片', doc: '文档', scan: '扫描件', other: '其他' }
const entityTypeMap = { commission: '委托', task: '任务', report: '报告', user: '用户', package_loan: '借出记录', record: '原始记录', sample: '样品' }

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('zh-CN')
}

async function loadAttachments() {
  loading.value = true
  try {
    const params = {}
    if (attFilters.commission_no) params.commission_no = attFilters.commission_no
    if (attFilters.task_no) params.task_no = attFilters.task_no
    if (attFilters.attachment_type) params.attachment_type = attFilters.attachment_type
    if (attFilters.search) params.search = attFilters.search
    const { data } = await request.get('/traceability/attachments', { params })
    attachments.value = data
  } catch {
    ElMessage.warning('加载附件列表失败')
  } finally {
    loading.value = false
  }
}

async function loadAuditLogs() {
  loading.value = true
  try {
    const params = {}
    if (auditFilters.entity_type) params.entity_type = auditFilters.entity_type
    if (auditFilters.entity_id) params.entity_id = auditFilters.entity_id
    if (auditFilters.actor) params.actor = auditFilters.actor
    if (auditFilters.action) params.action = auditFilters.action
    if (auditFilters.commission_no) params.commission_no = auditFilters.commission_no
    const { data } = await request.get('/traceability/audit-logs', { params })
    auditLogs.value = data
  } catch {
    ElMessage.warning('加载审计日志失败')
  } finally {
    loading.value = false
  }
}

async function loadModifications() {
  loading.value = true
  try {
    const params = {}
    if (modFilters.entity_type) params.entity_type = modFilters.entity_type
    if (modFilters.entity_id) params.entity_id = modFilters.entity_id
    if (modFilters.actor) params.actor = modFilters.actor
    if (modFilters.commission_no) params.commission_no = modFilters.commission_no
    const { data } = await request.get('/traceability/modifications', { params })
    modifications.value = data
  } catch {
    ElMessage.warning('加载修改日志失败')
  } finally {
    loading.value = false
  }
}

async function traceCommission() {
  if (!traceCommissionNo.value.trim()) return
  traceLoading.value = true
  try {
    const { data } = await request.get(`/traceability/commission/${traceCommissionNo.value.trim()}`)
    traceResult.value = data
    ElMessage.success(`追溯完成：${data.attachments.length} 个附件, ${data.audit_logs.length} 条审计, ${data.modifications.length} 条修改`)
  } catch {
    ElMessage.error('追溯查询失败')
    traceResult.value = null
  } finally {
    traceLoading.value = false
  }
}

const totalCount = computed(() => {
  if (!traceResult.value) return 0
  return traceResult.value.attachments.length + traceResult.value.audit_logs.length + traceResult.value.modifications.length
})

onMounted(() => {
  loadAttachments()
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2><el-icon><Link /></el-icon> 附件与内部追溯</h2>
      <p class="desc">浏览附件、审计日志、修改记录，按委托号聚合追溯</p>
    </div>

    <el-tabs v-model="activeTab" @tab-change="(t) => { if (t === 'audit') loadAuditLogs(); if (t === 'mod') loadModifications() }">
      <!-- Tab 1: 附件列表 -->
      <el-tab-pane label="附件管理" name="attachments">
        <div class="filter-bar">
          <el-input v-model="attFilters.commission_no" placeholder="委托编号" clearable style="width:180px" @keyup.enter="loadAttachments" />
          <el-input v-model="attFilters.task_no" placeholder="任务编号" clearable style="width:180px" @keyup.enter="loadAttachments" />
          <el-select v-model="attFilters.attachment_type" placeholder="附件类型" clearable style="width:130px" @change="loadAttachments">
            <el-option label="照片" value="photo" />
            <el-option label="文档" value="doc" />
            <el-option label="扫描件" value="scan" />
            <el-option label="其他" value="other" />
          </el-select>
          <el-input v-model="attFilters.search" placeholder="搜索文件名" clearable style="width:200px" @keyup.enter="loadAttachments">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button type="primary" @click="loadAttachments">查询</el-button>
        </div>

        <el-table :data="attachments" v-loading="loading && activeTab === 'attachments'" stripe border>
          <el-table-column prop="original_name" label="文件名" min-width="200" show-overflow-tooltip />
          <el-table-column label="类型" width="80">
            <template #default="{ row }">
              <el-tag size="small">{{ attTypeMap[row.attachment_type] || row.attachment_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="commission_no" label="委托编号" width="160" />
          <el-table-column prop="task_no" label="任务编号" width="140" />
          <el-table-column prop="checkpoint_label" label="检查点" width="120" />
          <el-table-column prop="uploader" label="上传者" width="90" />
          <el-table-column prop="evidence_status" label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.evidence_status === '有效' ? 'success' : 'info'" size="small">{{ row.evidence_status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="时间" width="160">
            <template #default="{ row }">{{ formatDate(row.captured_at || row.created_at) }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab 2: 审计日志 -->
      <el-tab-pane label="审计日志" name="audit">
        <div class="filter-bar">
          <el-select v-model="auditFilters.entity_type" placeholder="实体类型" clearable style="width:130px" @change="loadAuditLogs">
            <el-option label="委托" value="commission" />
            <el-option label="任务" value="task" />
            <el-option label="报告" value="report" />
            <el-option label="用户" value="user" />
          </el-select>
          <el-input v-model="auditFilters.entity_id" placeholder="实体ID" clearable style="width:180px" @keyup.enter="loadAuditLogs" />
          <el-input v-model="auditFilters.actor" placeholder="操作人" clearable style="width:130px" @keyup.enter="loadAuditLogs" />
          <el-input v-model="auditFilters.commission_no" placeholder="委托编号" clearable style="width:160px" @keyup.enter="loadAuditLogs" />
          <el-button type="primary" @click="loadAuditLogs">查询</el-button>
        </div>

        <el-table :data="auditLogs" v-loading="loading && activeTab === 'audit'" stripe border>
          <el-table-column label="时间" width="160">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="actor_name" label="操作人" width="100" />
          <el-table-column prop="actor_role" label="角色" width="100" />
          <el-table-column prop="action" label="操作" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ row.action }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="entity_type" label="实体类型" width="90" />
          <el-table-column prop="entity_id" label="实体ID" width="180" />
          <el-table-column prop="commission_no" label="委托编号" width="160" />
          <el-table-column prop="field_name" label="字段" width="120" />
          <el-table-column label="变更" min-width="200">
            <template #default="{ row }">
              <span v-if="row.old_value" style="color:#EF4444">{{ row.old_value }}</span>
              <span v-if="row.old_value && row.new_value" style="margin:0 4px">→</span>
              <span v-if="row.new_value" style="color:#10B981">{{ row.new_value }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab 3: 修改日志 -->
      <el-tab-pane label="修改日志" name="mod">
        <div class="filter-bar">
          <el-select v-model="modFilters.entity_type" placeholder="实体类型" clearable style="width:130px" @change="loadModifications">
            <el-option label="委托" value="commission" />
            <el-option label="任务" value="task" />
            <el-option label="报告" value="report" />
          </el-select>
          <el-input v-model="modFilters.entity_id" placeholder="实体ID" clearable style="width:180px" @keyup.enter="loadModifications" />
          <el-input v-model="modFilters.actor" placeholder="修改人" clearable style="width:130px" @keyup.enter="loadModifications" />
          <el-input v-model="modFilters.commission_no" placeholder="委托编号" clearable style="width:160px" @keyup.enter="loadModifications" />
          <el-button type="primary" @click="loadModifications">查询</el-button>
        </div>

        <el-table :data="modifications" v-loading="loading && activeTab === 'mod'" stripe border>
          <el-table-column label="时间" width="160">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="actor" label="修改人" width="100" />
          <el-table-column prop="entity_type" label="实体类型" width="90" />
          <el-table-column prop="entity_id" label="实体ID" width="180" />
          <el-table-column prop="commission_no" label="委托编号" width="160" />
          <el-table-column prop="field_name" label="字段" width="130" />
          <el-table-column label="旧值 → 新值" min-width="220">
            <template #default="{ row }">
              <span style="color:#EF4444">{{ row.old_value || '—' }}</span>
              <span style="margin:0 4px">→</span>
              <span style="color:#10B981">{{ row.new_value || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="修改原因" width="160" show-overflow-tooltip />
        </el-table>
      </el-tab-pane>

      <!-- Tab 4: 按委托追溯 -->
      <el-tab-pane label="按委托追溯" name="trace">
        <div class="filter-bar">
          <el-input v-model="traceCommissionNo" placeholder="输入委托编号，如 WT20260809001" clearable style="width:280px" @keyup.enter="traceCommission">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button type="primary" :loading="traceLoading" @click="traceCommission">开始追溯</el-button>
          <span v-if="traceResult" style="color:#64748B; font-size:13px">
            共找到 <b>{{ totalCount }}</b> 条追溯记录
          </span>
        </div>

        <div v-if="traceResult" style="display:flex; flex-direction:column; gap:16px">
          <!-- 附件 -->
          <el-card v-if="traceResult.attachments.length" shadow="never">
            <template #header><span><el-icon><Picture /></el-icon> 附件 ({{ traceResult.attachments.length }})</span></template>
            <el-table :data="traceResult.attachments" size="small" border>
              <el-table-column prop="original_name" label="文件名" min-width="180" show-overflow-tooltip />
              <el-table-column prop="attachment_type" label="类型" width="70" />
              <el-table-column prop="checkpoint_label" label="检查点" width="110" />
              <el-table-column prop="uploader" label="上传者" width="80" />
              <el-table-column label="时间" width="150">
                <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
              </el-table-column>
            </el-table>
          </el-card>

          <!-- 审计日志 -->
          <el-card v-if="traceResult.audit_logs.length" shadow="never">
            <template #header><span><el-icon><Clock /></el-icon> 审计日志 ({{ traceResult.audit_logs.length }})</span></template>
            <el-table :data="traceResult.audit_logs" size="small" border>
              <el-table-column label="时间" width="150">
                <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
              </el-table-column>
              <el-table-column prop="actor_name" label="操作人" width="90" />
              <el-table-column prop="action" label="操作" width="110" />
              <el-table-column prop="field_name" label="字段" width="110" />
              <el-table-column label="变更" min-width="180">
                <template #default="{ row }">
                  <span v-if="row.old_value" style="color:#EF4444">{{ row.old_value }}</span>
                  <span v-if="row.old_value && row.new_value" style="margin:0 4px">→</span>
                  <span v-if="row.new_value" style="color:#10B981">{{ row.new_value }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <!-- 修改日志 -->
          <el-card v-if="traceResult.modifications.length" shadow="never">
            <template #header><span><el-icon><Document /></el-icon> 修改日志 ({{ traceResult.modifications.length }})</span></template>
            <el-table :data="traceResult.modifications" size="small" border>
              <el-table-column label="时间" width="150">
                <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
              </el-table-column>
              <el-table-column prop="actor" label="修改人" width="90" />
              <el-table-column prop="field_name" label="字段" width="110" />
              <el-table-column label="变更" min-width="180">
                <template #default="{ row }">
                  <span style="color:#EF4444">{{ row.old_value || '—' }}</span>
                  <span style="margin:0 4px">→</span>
                  <span style="color:#10B981">{{ row.new_value || '—' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="reason" label="原因" min-width="150" show-overflow-tooltip />
            </el-table>
          </el-card>

          <el-empty v-if="totalCount === 0" description="该委托暂无追溯记录" />
        </div>
        <el-empty v-if="!traceResult && !traceLoading" description="输入委托编号后点击【开始追溯】" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.page { max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 16px; }
.page-header h2 { display: flex; align-items: center; gap: 8px; font-size: 20px; color: #1E293B; }
.page-header .desc { color: #64748B; margin: 4px 0 0; font-size: 14px; }
.filter-bar { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
</style>
