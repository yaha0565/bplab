<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Clock, UserFilled, Link, CircleCheck, CircleClose, Lock, Timer } from '@element-plus/icons-vue'
import request from '../utils/request'

const commissionNo = ref('')
const loading = ref(false)

// Timeline data
const timeline = ref([])
const summary = ref(null)

// Chain verification
const verifying = ref(false)
const chainResult = ref(null)

function formatTime(d) {
  return d ? new Date(d).toLocaleString('zh-CN', { hour12: false }) : '—'
}
function formatDate(d) {
  return d ? new Date(d).toLocaleDateString('zh-CN') : '—'
}
function formatTimeShort(d) {
  return d ? new Date(d).toLocaleTimeString('zh-CN', { hour12: false }) : '—'
}

const actionIcons = {
  'create': '📝', 'submit': '📤', 'receive': '📥', 'start': '▶️',
  'complete': '✅', 'review': '🔍', 'approve': '👍', 'reject': '↩️',
  'publish': '📢', 'deliver': '📬', 'revoke': '⏪', 'void': '❌',
  'correct': '✏️', 'update': '✏️', 'sign': '🖊️', 'system': '🤖',
}

const actionColors = {
  'create': '#3B82F6', 'submit': '#8B5CF6', 'receive': '#06B6D4',
  'start': '#10B981', 'complete': '#22C55E', 'review': '#F59E0B',
  'approve': '#10B981', 'reject': '#EF4444', 'publish': '#3B82F6',
  'deliver': '#6366F1', 'revoke': '#F97316', 'void': '#EF4444',
  'correct': '#EAB308', 'update': '#8B5CF6', 'sign': '#EC4899',
  'system': '#6B7280',
}

const entityLabels = {
  'commission': '委托单', 'task': '实验任务', 'report': '检验报告',
  'sample': '样品', 'sample_group': '样品组', 'record': '原始记录',
  'objection': '异议', 'equipment_incident': '设备故障',
  'package_loan': '借出', 'user': '用户',
}

function actionIcon(action) {
  const k = action.toLowerCase()
  for (const [key, val] of Object.entries(actionIcons)) {
    if (k.includes(key)) return val
  }
  return '📋'
}

function actionColor(action) {
  const k = action.toLowerCase()
  for (const [key, val] of Object.entries(actionColors)) {
    if (k.includes(key)) return val
  }
  return '#6B7280'
}

function entityLabel(t) { return entityLabels[t] || t }

// ═══ Load audit trail for a commission ═══
async function loadTrail() {
  if (!commissionNo.value.trim()) { ElMessage.warning('请输入委托编号'); return }
  loading.value = true
  timeline.value = []
  summary.value = null
  chainResult.value = null
  try {
    const cno = commissionNo.value.trim()

    // 1. Load commission info
    let commissionInfo = null
    try {
      const cResp = await request.get('/commissions', { params: { search: cno, limit: 1 } })
      const clist = Array.isArray(cResp.data) ? cResp.data : (cResp.data?.items || [])
      commissionInfo = clist.find((c) => c.commission_no === cno) || null
    } catch { /* ignore */ }

    // 2. Load tasks
    let tasks = []
    try {
      const tResp = await request.get('/tasks', { params: { commission_no: cno, limit: 100 } })
      tasks = Array.isArray(tResp.data) ? tResp.data : (tResp.data?.items || [])
    } catch { /* ignore */ }

    // 3. Load reports
    let reports = []
    try {
      const rResp = await request.get('/reports', { params: { commission_no: cno, limit: 100 } })
      reports = Array.isArray(rResp.data) ? rResp.data : (rResp.data?.items || [])
    } catch { /* ignore */ }

    // 4. Load audit logs
    let logs = []
    try {
      const aResp = await request.get('/traceability/audit-logs', {
        params: { commission_no: cno, limit: 500 }
      })
      logs = Array.isArray(aResp.data) ? aResp.data : []
    } catch { /* ignore */ }

    // 5. Load modifications
    let mods = []
    try {
      const mResp = await request.get('/traceability/modifications', {
        params: { commission_no: cno, limit: 500 }
      })
      mods = Array.isArray(mResp.data) ? mResp.data : []
    } catch { /* ignore */ }

    // 6. Load sample events
    let sampleEvents = []
    try {
      const sResp = await request.get('/traceability/sample-events', {
        params: { commission_no: cno, limit: 200 }
      })
      sampleEvents = Array.isArray(sResp.data) ? sResp.data : []
    } catch { /* ignore */ }

    // ── Build unified timeline ──
    const events = []

    // Commission lifecycle
    if (commissionInfo) {
      if (commissionInfo.created_at) events.push({
        time: commissionInfo.created_at, type: 'commission', entity_id: cno,
        actor: commissionInfo.created_by || '系统', actor_role: '',
        action: '创建委托', detail: `委托 "${commissionInfo.client_name || cno}" 已创建`,
        color: '#3B82F6',
      })
      if (commissionInfo.status === '已作废' || commissionInfo.status === '作废') events.push({
        time: commissionInfo.updated_at || commissionInfo.created_at, type: 'commission',
        entity_id: cno, actor: '系统', actor_role: '',
        action: '委托作废', detail: `委托已作废`,
        color: '#EF4444',
      })
    }

    // Task lifecycle
    for (const t of tasks) {
      const tn = t.task_no || '?'
      if (t.created_at) events.push({
        time: t.created_at, type: 'task', entity_id: tn, actor: t.assignee || '系统',
        actor_role: '实验员', action: '任务创建', detail: `任务 ${tn} — ${t.experiment || ''} 已创建`,
        color: '#3B82F6',
      })
      if (t.received_at || (t.status === '进行中' && t.updated_at)) events.push({
        time: t.received_at || t.updated_at, type: 'task', entity_id: tn,
        actor: t.tester || t.assignee || '系统', actor_role: '实验员',
        action: '接收任务', detail: `任务 ${tn} — ${t.experiment || ''} 已接收, 实验开始`,
        color: '#06B6D4',
      })
      if (t.status === '已完成' || t.completed_at) events.push({
        time: t.completed_at || t.updated_at, type: 'task', entity_id: tn,
        actor: t.tester || t.assignee || '系统', actor_role: '实验员',
        action: '完成实验', detail: `任务 ${tn} — ${t.experiment || ''} 实验已完成`,
        color: '#10B981',
      })
      if (t.status === '待复核' || t.status === '复核中') events.push({
        time: t.updated_at || t.created_at, type: 'task', entity_id: tn,
        actor: t.tester || t.assignee || '', actor_role: '实验员',
        action: '提交复核', detail: `任务 ${tn} 已提交等待复核`,
        color: '#F59E0B',
      })
      if (t.status === '已退回') events.push({
        time: t.updated_at, type: 'task', entity_id: tn,
        actor: t.verifier || t.reviewer || '', actor_role: '复核员',
        action: '退回修改', detail: `任务 ${tn} 已被退回修改`,
        color: '#EF4444',
      })
      // Sample events for this task
      for (const se of sampleEvents) {
        if (se.task_no === tn) {
          events.push({
            time: se.created_at, type: 'sample', entity_id: se.sample_no || tn,
            actor: se.operator || '', actor_role: se.operator_role || '',
            action: se.event_type || '样品操作',
            detail: `样品 "${se.sample_name || se.sample_no || ''}" — ${se.event_type || se.description || ''}`,
            color: '#6366F1',
          })
        }
      }
    }

    // Report lifecycle
    for (const r of reports) {
      const rn = r.report_no || '?'
      if (r.created_at) events.push({
        time: r.created_at, type: 'report', entity_id: rn, actor: r.generator || '系统',
        actor_role: '复核员', action: '生成报告', detail: `报告 ${rn} 已生成`,
        color: '#8B5CF6',
      })
      if (r.reviewed_at || r.verifier) events.push({
        time: r.reviewed_at || r.created_at, type: 'report', entity_id: rn,
        actor: r.verifier || '', actor_role: '复核员',
        action: '复核报告', detail: `报告 ${rn} — ${r.conclusion || '复核通过'}`,
        color: '#F59E0B',
      })
      if (r.status === '已发布' || r.published_at || r.approve_date) events.push({
        time: r.published_at || r.approve_date || r.updated_at, type: 'report',
        entity_id: rn, actor: r.approver || r.quality_inspector || '',
        actor_role: '质量负责人', action: '签发报告',
        detail: `报告 ${rn} 已签发${r.conclusion ? ' — ' + r.conclusion : ''}`,
        color: '#10B981',
      })
      if (r.status === '已撤回') events.push({
        time: r.updated_at, type: 'report', entity_id: rn,
        actor: r.updated_by || '', actor_role: '质量负责人',
        action: '撤回报告', detail: `报告 ${rn} 已撤回`,
        color: '#F97316',
      })
    }

    // Audit logs from traceability
    for (const l of logs) {
      const detail = []
      if (l.field_name) detail.push(`字段: ${l.field_name}`)
      if (l.old_value) detail.push(`${l.old_value} → ${l.new_value || ''}`)
      if (l.reason) detail.push(`原因: ${l.reason}`)
      if (l.comment) detail.push(l.comment)

      events.push({
        time: l.created_at, type: l.entity_type, entity_id: l.entity_id,
        actor: l.actor_name || l.actor || '', actor_role: l.actor_role || '',
        action: l.action || '操作',
        detail: `${entityLabel(l.entity_type)} ${l.entity_id} — ${l.action}${detail.length ? ' [' + detail.join('; ') + ']' : ''}`,
        color: actionColor(l.action),
        field_name: l.field_name, old_value: l.old_value, new_value: l.new_value,
        reason: l.reason, comment: l.comment,
      })
    }

    // Modifications
    for (const m of mods) {
      events.push({
        time: m.created_at, type: m.entity_type, entity_id: m.entity_id,
        actor: m.actor || '', actor_role: '',
        action: m.action || '字段修改',
        detail: `${entityLabel(m.entity_type)} ${m.entity_id}: ${m.field_name} 由 "${m.old_value}" 改为 "${m.new_value}"${m.reason ? ' — ' + m.reason : ''}`,
        color: '#EAB308', is_mod: true,
        field_name: m.field_name, old_value: m.old_value, new_value: m.new_value,
        reason: m.reason,
      })
    }

    // Delivery events for each report
    for (const r of reports) {
      try {
        const dResp = await request.get(`/reports/${r.report_no}/deliveries`)
        for (const d of (dResp.data || [])) {
          events.push({
            time: d.delivered_at || d.created_at, type: 'report',
            entity_id: r.report_no, actor: d.delivered_by || d.recipient || '系统',
            actor_role: '样品管理员', action: '发放报告',
            detail: `报告 ${r.report_no} 通过 ${d.delivery_method || ''} 发放给 ${d.recipient || ''}，签收状态: ${d.receipt_status || '未知'}`,
            color: '#6366F1',
          })
        }
      } catch { /* no deliveries */ }
    }

    // Sort by time
    events.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())

    // Group by date
    const groups = []
    let currentDate = ''
    for (const e of events) {
      const d = formatDate(e.time)
      if (d !== currentDate) {
        currentDate = d
        groups.push({ date: d, events: [] })
      }
      groups[groups.length - 1].events.push(e)
    }

    timeline.value = groups

    // Summary
    const actors = [...new Set(events.map(e => e.actor).filter(Boolean))]
    const entityTypesCount = [...new Set(events.map(e => e.type))]
    summary.value = {
      commission_no: cno,
      total_events: events.length,
      actors: actors.length,
      entity_types: entityTypesCount.length,
      date_range: events.length > 0
        ? `${formatDate(events[0].time)} ~ ${formatDate(events[events.length - 1].time)}`
        : '—',
    }

    if (!events.length) ElMessage.info('该委托暂无审计追踪记录')
    else ElMessage.success(`追踪到 ${events.length} 条事件`)
  } catch (e) {
    ElMessage.error('加载审计追踪失败')
    timeline.value = []
  } finally { loading.value = false }
}

// ═══ Verify hash chain ═══
async function verifyChain() {
  if (!commissionNo.value.trim()) return
  verifying.value = true
  try {
    const params = { entity_type: 'commission', entity_id: commissionNo.value.trim(), limit: 500 }
    const { data } = await request.get('/traceability/audit-logs', { params })
    const entries = Array.isArray(data) ? data : []
    if (!entries.length) {
      chainResult.value = { ok: true, detail: '该委托暂无审计记录', entries: 0 }
      return
    }

    // Verify SHA-256 hash chain
    let prevHash = '0'.repeat(64)
    let broken = null
    for (const e of entries) {
      if (e.previous_hash && e.previous_hash !== prevHash) {
        broken = { id: e.id, expected: prevHash, found: e.previous_hash }
        break
      }
      prevHash = e.entry_hash || '0'.repeat(64)
    }
    chainResult.value = broken
      ? { ok: false, detail: `哈希链在记录 #${broken.id} 处断裂`, entries: entries.length, broken }
      : { ok: true, detail: `哈希链完整，共 ${entries.length} 条审计记录`, entries: entries.length }
  } catch {
    ElMessage.error('校验失败')
    chainResult.value = null
  } finally { verifying.value = false }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2><el-icon><Lock /></el-icon> 审计追踪链</h2>
      <p class="desc">按委托编号查看完整审计时间线：谁在什么时间对什么做了什么操作、流程走向、所有修改记录</p>
    </div>

    <!-- Search & Verify -->
    <div class="search-bar">
      <el-input v-model="commissionNo" placeholder="输入委托编号，如 WT20260811001" clearable style="width:320px"
        @keyup.enter="loadTrail">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button type="primary" :loading="loading" @click="loadTrail">
        <el-icon><Clock /></el-icon> 查看追踪链
      </el-button>
      <el-button :loading="verifying" @click="verifyChain">
        <el-icon><Link /></el-icon> 验证哈希链
      </el-button>
    </div>

    <!-- Chain verification result -->
    <div v-if="chainResult" class="chain-result">
      <el-alert v-if="chainResult.ok"
        :title="`✅ ${chainResult.detail}`" type="success" :closable="false" show-icon />
      <el-alert v-else
        :title="`❌ ${chainResult.detail}`" type="error" :closable="false" show-icon>
        <template #default>
          <div style="margin-top:4px;font-size:12px">
            <div>期望前序哈希: <code>{{ chainResult.broken?.expected?.slice(0, 32) }}…</code></div>
            <div>实际前序哈希: <code>{{ chainResult.broken?.found?.slice(0, 32) }}…</code></div>
          </div>
        </template>
      </el-alert>
    </div>

    <!-- Summary -->
    <div v-if="summary" class="summary-bar">
      <el-tag type="primary">委托: {{ summary.commission_no }}</el-tag>
      <el-tag>总事件: {{ summary.total_events }}</el-tag>
      <el-tag type="warning">参与人: {{ summary.actors }}</el-tag>
      <el-tag>时间范围: {{ summary.date_range }}</el-tag>
    </div>

    <!-- Timeline -->
    <div v-if="timeline.length" v-loading="loading" class="timeline">
      <div v-for="group in timeline" :key="group.date" class="date-group">
        <div class="date-divider">
          <span class="date-line"></span>
          <span class="date-label">{{ group.date }}</span>
          <span class="date-line"></span>
        </div>

        <div v-for="(evt, idx) in group.events" :key="idx" class="tl-item">
          <!-- Time column -->
          <div class="tl-time">
            <span class="tl-clock"><el-icon><Timer /></el-icon></span>
            <span class="tl-timestamp">{{ formatTimeShort(evt.time) }}</span>
          </div>

          <!-- Dot + line -->
          <div class="tl-dot-col">
            <div class="tl-dot" :style="{ background: evt.color }">
              <span class="tl-dot-icon">{{ actionIcon(evt.action) }}</span>
            </div>
            <div v-if="idx < group.events.length - 1" class="tl-line"></div>
          </div>

          <!-- Content -->
          <div class="tl-content">
            <div class="tl-card">
              <div class="tl-card-header">
                <el-tag size="small" :color="evt.color" effect="dark" style="border:none">
                  {{ evt.action }}
                </el-tag>
                <span class="tl-entity">{{ entityLabel(evt.type) }} — {{ evt.entity_id }}</span>
              </div>
              <div class="tl-detail">{{ evt.detail }}</div>
              <div class="tl-meta">
                <span class="tl-actor"><el-icon><UserFilled /></el-icon> {{ evt.actor || '系统' }}</span>
                <span v-if="evt.actor_role" class="tl-role">{{ evt.actor_role }}</span>
                <!-- Old → New value indicator for modifications -->
                <span v-if="evt.field_name" style="margin-left:8px;font-size:12px;color:#64748B">
                  字段 {{ evt.field_name }}
                  <template v-if="evt.old_value">: <span style="color:#EF4444">{{ evt.old_value }}</span> → <span style="color:#10B981">{{ evt.new_value }}</span></template>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-empty v-if="!loading && !timeline.length && commissionNo && !summary"
      description="未找到该委托的审计记录" />
    <el-empty v-if="!commissionNo" description="输入委托编号查看完整审计追踪时间线" />

    <!-- Legacy: raw audit logs table -->
    <details style="margin-top:16px">
      <summary style="cursor:pointer;color:#64748B;font-size:13px">原始审计日志（表格视图）</summary>
      <div style="margin-top:8px;max-height:400px;overflow:auto;border:1px solid #E2E8F0;border-radius:6px;padding:8px">
        <p style="color:#94A3B8;font-size:12px;text-align:center;padding:20px">
          时间线视图已提供完整信息。如需查看原始日志，请前往
          <a href="/traceability" style="color:#3B82F6">附件与内部追溯</a> 页面。
        </p>
      </div>
    </details>
  </div>
</template>

<style scoped>
.page { max-width: 1000px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-header h2 { display: flex; align-items: center; gap: 8px; font-size: 20px; color: #1E293B; }
.page-header .desc { color: #64748B; margin: 4px 0 0; font-size: 14px; }

.search-bar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }

.chain-result { margin-bottom: 16px; }

.summary-bar { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 24px; padding: 12px 16px;
  background: #F8FAFC; border-radius: 8px; border: 1px solid #E2E8F0; }

/* ── Timeline ── */
.timeline { position: relative; }
.date-group { margin-bottom: 4px; }
.date-divider { display: flex; align-items: center; gap: 12px; margin: 24px 0 16px; }
.date-line { flex: 1; height: 1px; background: #E2E8F0; }
.date-label { font-size: 13px; font-weight: 600; color: #64748B; white-space: nowrap; }

.tl-item { display: flex; gap: 12px; min-height: 80px; }
.tl-time { width: 50px; display: flex; flex-direction: column; align-items: center; padding-top: 12px; }
.tl-clock { color: #CBD5E1; font-size: 14px; }
.tl-timestamp { font-size: 11px; color: #94A3B8; font-family: monospace; margin-top: 2px; }

.tl-dot-col { display: flex; flex-direction: column; align-items: center; width: 32px; padding-top: 14px; }
.tl-dot {
  width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; box-shadow: 0 2px 8px rgba(0,0,0,.12); z-index: 1;
}
.tl-dot-icon { font-size: 14px; line-height: 1; }
.tl-line { width: 2px; flex: 1; background: #E2E8F0; min-height: 20px; }

.tl-content { flex: 1; padding-bottom: 12px; }
.tl-card {
  background: #FFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px;
  transition: box-shadow .2s;
}
.tl-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,.06); }
.tl-card-header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tl-entity { font-size: 13px; color: #1E293B; font-weight: 500; font-family: monospace; }
.tl-detail { font-size: 14px; color: #334155; margin-top: 6px; line-height: 1.5; }
.tl-meta { display: flex; align-items: center; gap: 6px; margin-top: 8px; font-size: 12px; color: #94A3B8; }
.tl-actor { display: flex; align-items: center; gap: 4px; }
.tl-role { color: #64748B; padding: 1px 6px; background: #F1F5F9; border-radius: 4px; font-size: 11px; }
</style>
