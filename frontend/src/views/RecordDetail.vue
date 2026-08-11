<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '../utils/request'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const recordNo = route.params.recordNo
const version = parseInt(route.params.version) || 1

const record = ref(null)
const task = ref(null)
const config = ref(null)
const manifestFields = ref([])
const loading = ref(true)
const wordPreviewVisible = ref(false)
const wordPreviewLoading = ref(false)
const wordPreviewHtml = ref('')

const userRole = computed(() => authStore.user?.role || '')
const userName = computed(() => authStore.user?.username || '')

// ═══════════════════════════════════════════════════════════════
// Parse payload
// ═══════════════════════════════════════════════════════════════

const payload = computed(() => {
  if (!record.value?.payload) return {}
  return typeof record.value.payload === 'string'
    ? JSON.parse(record.value.payload)
    : record.value.payload
})

const formData = computed(() => payload.value._form || {})
const measurementRows = computed(() => payload.value._rows || [])
const equipmentChecks = computed(() => payload.value._equipment_checks || [])
const photos = computed(() => payload.value._photos || [])
const taskConfirmations = computed(() => payload.value._task_confirmations || {})
const prechecks = computed(() => payload.value._prechecks || [])
const precheckNote = computed(() => payload.value._precheck_note || '')
const precheckAllItems = computed(() => payload.value._precheck_all_items || [])
const fixedParamMode = computed(() => payload.value._fixed_param_mode || '')
const overallStatus = computed(() => payload.value._overall_status || '')
const deviation = computed(() => payload.value._deviation || '')
const retest = computed(() => payload.value._retest || '')
const reportSummary = computed(() => payload.value._report_summary || '')
const reportConclusion = computed(() => payload.value._report_conclusion || '')
const testerSelfCheck = computed(() => payload.value._tester_self_check || false)
const templateFields = computed(() => {
  const tf = payload.value._template_fields
  if (!tf) return []
  return Array.isArray(tf) ? tf : Object.entries(tf).map(([k, v]) => ({ key: k, value: v }))
})

// ═══════════════════════════════════════════════════════════════
// Helpers (copied from ExperimentRun.vue)
// ═══════════════════════════════════════════════════════════════

const BLANK_RE = /_{2,}|＿{2,}|…{2,}/
const HIDDEN_PARAM_KEYS = new Set([
  'detection_location', 'software', 'data_path', 'start_time', 'end_time',
  'equipment_name', 'equipment_model', 'equipment_no',
  'calibration_certificate', 'calibration_due', 'equipment_status',
  'image_path', 'image_before_path', 'image_after_path', 'curve_path',
])
const ENV_KEYS = ['test_date', 'temperature_before', 'temperature_after', 'humidity_before', 'humidity_after']
const PROCESS_PREFIXES = ['iqi_gray_', 'monitor_', 'color_monitor_']

function getFieldType(f) { const t = f.type || 'text'; return ['select','multiselect','number','date','datetime','time','textarea'].includes(t) ? t : 'text' }
function getFieldOptions(f) { if (f.options?.length) return f.options; if (f.type?.startsWith('select:')) return f.type.replace('select:', '').split('|'); if (f.type?.startsWith('multiselect:')) return f.type.replace('multiselect:', '').split('|'); return [] }
function isFieldRequired(f) { return f.is_required || f.required || f.is_actual || false }
function getColumnType(c) { if (c.column_type === 'number') return 'number'; if (c.column_type?.startsWith('select:') || c.column_type === 'select') return 'select'; return 'text' }
function getColumnOptions(c) {
  if (c.column_type?.startsWith('select:')) return c.column_type.replace('select:', '').split('|')
  if (c.column_type === 'select' && c.column_default && String(c.column_default).includes('|')) return String(c.column_default).split('|')
  return []
}

function _checkboxChoices(original) {
  const choices = []
  const parts = (original || '').split(/[□☐☑]/)
  for (let i = 1; i < parts.length; i++) {
    let value = parts[i].replace(new RegExp(BLANK_RE.source, 'g'), '')
    value = value.split(/[；;，,]/)[0].trim().replace(/^[：: ]+/, '').replace(/[：: ]+$/, '')
    if (value) choices.push(value)
  }
  return [...new Set(choices)]
}

function _selectedCheckboxChoices(original, current) {
  const selected = []
  for (const choice of _checkboxChoices(original)) {
    if (new RegExp('☑\\s*' + choice.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).test(current || '')) {
      selected.push(choice)
    }
  }
  return selected
}

function _parseCheckboxValue(original, current) {
  const selected = _selectedCheckboxChoices(original, current || '')
  const hasBlank = BLANK_RE.test(current || '')
  const match = (current || '').match(new RegExp(BLANK_RE.source))
  const note = match ? current.replace(/.*?[_＿…]{2,}.*?/, '').replace(/[_＿…]+/g, '').trim() : ''
  return { selected, note: hasBlank ? (note || '') : '' }
}

function _checkboxFieldMeta(label, choices) {
  if (!choices.length) return { multi: false }
  const exclusiveTokens = ['类别', '来源', '依据', '状态', '结果', '结论', '方向', '方法', '是否', '判定']
  if (exclusiveTokens.some(t => (label || '').includes(t))) return { multi: false }
  const negativeTokens = ['不符合', '不合格', '异常', '不可', '暂停', '未完成', '无效', '破损', '裂纹', '崩瓷', '污染', '锈蚀', '磨损', '偏离', '失败']
  const hasNegative = choices.some(c => negativeTokens.some(t => c.includes(t)))
  if (!hasNegative && choices.length > 2) return { multi: true }
  return { multi: false }
}

function _choiceNeedsNote(selected) {
  const triggerTokens = ['其他', '异常', '不符合', '不合格', '有', '调整', '维修', '无效']
  return selected.some(c => triggerTokens.some(t => c.includes(t)))
}

function formatFieldValue(val) {
  if (val == null || val === '') return '-'
  if (Array.isArray(val)) return val.join('、')
  return String(val)
}

// ═══════════════════════════════════════════════════════════════
// Calculation engine (ported from ExperimentRun.vue)
// ═══════════════════════════════════════════════════════════════

function _num(val, def = 0) { if (val === null || val === '') return def; const n = Number(val); return isNaN(n) ? def : n }
function _n(val) { if (val === null || val === '') return null; const n = Number(val); return isNaN(n) ? null : n }
function _finite(n) { return n != null && isFinite(n) ? n : null }
function _safeDiv(a, b) { if (!b) return null; const r = a / b; return isFinite(r) ? r : null }

function calculateRows(kind, rows) {
  return rows.map(raw => {
    const row = { ...raw }
    try {
      if (kind === 'mc_crack') {
        const vs = [_n(row.dm1), _n(row.dm2), _n(row.dm3)]
        if (vs.every(v => v !== null)) row.dm_mean = +((vs[0] + vs[1] + vs[2]) / 3).toFixed(4)
        const k = _n(row.k), f = _n(row.ffail)
        if (k !== null && f !== null) row.tau = +(k * f).toFixed(2)
        row.conclusion = row.tau != null ? (row.tau > 25 ? '符合' : '不符合') : ''
      } else if (kind === 'rough') {
        const vs = [_n(row.ra1), _n(row.ra2), _n(row.ra3)]
        if (vs.every(v => v !== null)) row.mean = +((vs[0] + vs[1] + vs[2]) / 3).toFixed(3)
        row.conclusion = row.mean != null ? (row.mean <= _num(row.limit, 15) ? '符合' : '不符合') : ''
      } else if (kind === 'warp') {
        const h1 = _n(row.h1), h2 = _n(row.h2)
        if (h1 !== null && h2 !== null) row.delta = +(h1 - h2).toFixed(4)
        row.conclusion = row.delta != null ? (Math.abs(row.delta) <= _num(row.limit, 0.5) ? '合格' : '不合格') : ''
      } else if (kind === 'cte') {
        const t1 = _n(row.t1), t2 = _n(row.t2)
        if (t1 !== null && t2 !== null) row.delta_t = +(t2 - t1).toFixed(3)
        const l0 = _n(row.l0), dt = _n(row.delta_t), dl = _n(row.delta_l)
        if (l0 && dt && dl !== null) {
          const alpha = _safeDiv(dl / 1000, l0 * dt)
          if (alpha !== null) row.alpha = +(alpha * 1000000).toFixed(3)
        }
        row.conclusion = row.judgement_result || row.conclusion || ''
      } else if (kind === 'shock') {
        row.conclusion = ['crack', 'chipping', 'fracture'].every(k => (row[k] || '无') === '无') ? '符合' : '不符合'
      } else if (kind === 'bend') {
        row.conclusion = _num(row.stress_02) >= 800 ? '符合' : '不符合'
      } else if (kind === 'hv') {
        const vs = [_n(row.indent1), _n(row.indent2), _n(row.indent3)]
        if (vs.every(v => v !== null)) row.mean = +((vs[0] + vs[1] + vs[2]) / 3).toFixed(1)
      } else if (kind === 'thickness') {
        let all = []
        for (const sec of ['fixed', 'middle', 'free']) {
          const keys = []
          for (let r = 1; r <= 3; r++) for (let p = 1; p <= 3; p++) keys.push(`r${r}_${sec}_p${p}`)
          const vs = keys.map(k => _n(row[k]))
          if (vs.every(v => v !== null)) row[`${sec}_mean`] = +((vs.reduce((a, b) => a + b, 0)) / vs.length).toFixed(4)
          all = all.concat(vs)
        }
        if (all.every(v => v !== null)) row.mean = +(all.reduce((a, b) => a + b, 0) / all.length).toFixed(4)
        const design = _n(row._design_thickness) || _n(row.design_thickness)
        if (row.mean != null && design !== null) row.deviation = +(row.mean - design).toFixed(4)
        row.conclusion = row.deviation != null ? (Math.abs(row.deviation) <= 0.05 ? '符合' : '不符合') : ''
      } else if (kind === 'color') {
        const obs = [row.observer1, row.observer2, row.observer3]
        const severe = obs.filter(x => x === '明显差异').length
        const unable = obs.filter(x => x === '无法判定').length
        row.overall = unable >= 2 ? '无法判定' : (severe >= 2 ? '明显差异' : '未见明显差异/轻微差异')
        row.conclusion = severe >= 2 ? '不符合' : (unable >= 2 ? '需复核' : '符合')
      } else if (kind === 'xray') {
        let roiMeans = []
        for (let roi = 1; roi <= 3; roi++) {
          let vs = []
          for (let rd = 1; rd <= 3; rd++) vs.push(_n(row[`roi${roi}_reading${rd}`]))
          const m = vs.every(v => v !== null) ? +((vs[0] + vs[1] + vs[2]) / 3).toFixed(2) : _n(row[`roi${roi}`])
          row[`roi${roi}`] = m
          roiMeans.push(m)
        }
        if (roiMeans.every(v => v !== null)) row.roi_mean = +((roiMeans[0] + roiMeans[1] + roiMeans[2]) / 3).toFixed(2)
      }
    } catch (e) { /* ignore */ }
    return row
  })
}

const calculatedRows = computed(() => {
  const kind = config.value?.kind || task.value?.experiment_code || ''
  if (!kind || !measurementRows.value.length) return measurementRows.value
  return calculateRows(kind, measurementRows.value)
})

// ═══════════════════════════════════════════════════════════════
// Section ③—⑥ computed properties
// ═══════════════════════════════════════════════════════════════

// ── Section ③: Field categorization ──
const fieldSections = computed(() => {
  if (!config.value?.fields?.length) return []
  const secMap = {}
  for (const f of config.value.fields) {
    const so = f.section_order ?? 0
    if (!secMap[so]) secMap[so] = { title: f.section_title || `第${so + 1}部分`, fields: [], sectionOrder: so }
    secMap[so].fields.push(f)
  }
  return Object.values(secMap).sort((a, b) => a.sectionOrder - b.sectionOrder)
})

const visibleFieldSections = computed(() => {
  return fieldSections.value.map(s => ({
    ...s,
    fields: s.fields.filter(f => !HIDDEN_PARAM_KEYS.has(f.key)),
  })).filter(s => s.fields.length)
})

const visibleReadonly = computed(() => visibleFieldSections.value.map(s => ({ ...s, fields: s.fields.filter(f => f.readonly) })).filter(s => s.fields.length))
const visibleEditable = computed(() => visibleFieldSections.value.map(s => ({ ...s, fields: s.fields.filter(f => !f.readonly) })).filter(s => s.fields.length))
const editableFields = computed(() => visibleEditable.value.flatMap(s => s.fields))
const envFields = computed(() => editableFields.value.filter(f => ENV_KEYS.includes(f.key)))
const processFields = computed(() => editableFields.value.filter(f => PROCESS_PREFIXES.some(p => f.key.startsWith(p))))
const coreManualFields = computed(() => editableFields.value.filter(f => !ENV_KEYS.includes(f.key) && !PROCESS_PREFIXES.some(p => f.key.startsWith(p))))
const fixedFields = computed(() => visibleEditable.value.flatMap(s => s.fields).filter(f => f.default != null && f.default !== '' && !f.readonly))

// ── Section ④: Measurement columns ──
const visibleColumns = computed(() => {
  const cols = config.value?.columns || []
  if (!cols.length) return null
  return cols.filter(c => c.column_key !== 'sample_no')
})
const calcColumns = computed(() => visibleColumns.value ? visibleColumns.value.filter(c => c.column_type === 'calc') : [])
const inputColumns = computed(() => visibleColumns.value ? visibleColumns.value.filter(c => c.column_type !== 'calc') : [])

const sampleIds = computed(() => {
  const sn = task.value?.sample_nos
  if (!sn) return measurementRows.value.map(r => r.sample_no).filter((v, i, a) => v && a.indexOf(v) === i)
  return String(sn).split(',').map(s => s.trim()).filter(Boolean)
})

const sampleGroups = computed(() => {
  const rows = calculatedRows.value
  const map = {}
  for (let i = 0; i < rows.length; i++) {
    const sno = rows[i].sample_no || `#${i + 1}`
    if (!map[sno]) map[sno] = []
    map[sno].push({ ...rows[i], _index: i })
  }
  return Object.entries(map)
})

// ── Section ⑤: Template fields grouped ──
const templateFieldsGrouped = computed(() => {
  const tf = templateFields.value
  if (!tf.length) return {}
  const groups = {}
  for (const f of tf) {
    const sec = f.section || '其他补充字段'
    if (!groups[sec]) groups[sec] = []
    groups[sec].push(f)
  }
  return groups
})

// Merge stored template fields with manifest for display
const mergedTemplateFields = computed(() => {
  if (!manifestFields.value.length) return templateFields.value
  const storedMap = {}
  for (const f of templateFields.value) { storedMap[f.key] = f }
  return manifestFields.value.map(mf => ({
    ...mf,
    value: storedMap[mf.key]?.value || '',
  }))
})

const mergedTemplateGrouped = computed(() => {
  const groups = {}
  for (const f of mergedTemplateFields.value) {
    const sec = f.section || '其他补充字段'
    if (!groups[sec]) groups[sec] = []
    groups[sec].push(f)
  }
  return groups
})

// ── Section ⑥: Photo checkpoints ──
const photoCheckpoints = computed(() => {
  if (!photos.value.length) return []
  // Try to get metadata from config if available
  const configMap = {}
  if (config.value?.photo_checkpoints) {
    for (const cp of config.value.photo_checkpoints) {
      configMap[cp.code || cp.checkpoint_code] = cp
    }
  }
  return photos.value.map(p => {
    const code = p.code || p.checkpoint_code || ''
    const meta = configMap[code] || {}
    return {
      code,
      label: p.label || p.checkpoint_label || meta.label || meta.checkpoint_label || '',
      checkpointGroup: p.checkpoint_group || meta.checkpoint_group || meta.checkpointGroup || '未分组',
      isSampleLevel: p.isSampleLevel || p.is_sample_level || meta.isSampleLevel || meta.is_sample_level || false,
      required: meta.required !== false,
      previewUrl: p.previewUrl || '',
      samplePhotos: p.samplePhotos || {},
      hasPhoto: !!(p.previewUrl || (p.samplePhotos && Object.keys(p.samplePhotos || {}).length)),
    }
  })
})

const photoCheckpointGroups = computed(() => {
  const groups = {}
  for (const cp of photoCheckpoints.value) {
    const g = cp.checkpointGroup || '其他拍照节点'
    if (!groups[g]) groups[g] = []
    groups[g].push(cp)
  }
  return groups
})

const photoCompletionCount = computed(() => {
  let count = 0
  for (const cp of photoCheckpoints.value) {
    if (cp.isSampleLevel) {
      for (const sno of sampleIds.value) {
        if (cp.samplePhotos[sno]?.previewUrl) count++
      }
    } else {
      if (cp.previewUrl) count++
    }
  }
  return count
})

const totalPhotoRequired = computed(() => {
  let total = 0
  for (const cp of photoCheckpoints.value) {
    if (cp.required === false) continue
    if (cp.isSampleLevel) { total += sampleIds.value.length }
    else { total++ }
  }
  return total
})

const missingPhotos = computed(() => {
  let count = 0
  for (const cp of photoCheckpoints.value) {
    if (cp.required === false) continue
    if (cp.isSampleLevel) {
      for (const sno of sampleIds.value) {
        if (!cp.samplePhotos[sno]?.previewUrl) count++
      }
    } else {
      if (!cp.previewUrl) count++
    }
  }
  return count
})

// ═══════════════════════════════════════════════════════════════
// Data loading
// ═══════════════════════════════════════════════════════════════

async function loadRecord() {
  loading.value = true
  try {
    const { data } = await request.get(`/records/${recordNo}/v${version}`)
    record.value = data
    if (data.task_no) {
      try {
        const taskRes = await request.get(`/tasks/${data.task_no}`)
        task.value = taskRes.data?.task || taskRes.data
        // Load experiment config
        if (task.value?.experiment_code) {
          try {
            const [cfgRes, manifestRes] = await Promise.all([
              request.get(`/config/${task.value.experiment_code}`),
              request.get(`/config/${task.value.experiment_code}/template-manifest`),
            ])
            config.value = cfgRes.data
            manifestFields.value = manifestRes.data?.fields || []
          } catch { config.value = null }
        }
      } catch { }
    }
  } catch (e) {
    ElMessage.error('加载记录失败')
  } finally {
    loading.value = false
  }
}

// ═══════════════════════════════════════════════════════════════
// Word preview / export
// ═══════════════════════════════════════════════════════════════

async function openWordPreview() {
  wordPreviewVisible.value = true
  wordPreviewLoading.value = true
  wordPreviewHtml.value = ''
  try {
    const resp = await request.get(`/records/${recordNo}/v${version}/preview`, { responseType: 'text' })
    wordPreviewHtml.value = typeof resp === 'string' ? resp : resp.data
  } catch (e) {
    ElMessage.error('加载Word预览失败')
  } finally {
    wordPreviewLoading.value = false
  }
}

async function downloadWord() {
  try {
    const resp = await request.get(`/records/${recordNo}/v${version}/export`, { responseType: 'blob' })
    const blob = new Blob([resp.data || resp], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${recordNo}_V${version}.docx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('Word文档下载成功')
  } catch (e) {
    ElMessage.error('下载失败: ' + (e.response?.data?.detail || e.message))
  }
}

// ═══════════════════════════════════════════════════════════════
// Review dialog
// ═══════════════════════════════════════════════════════════════

const reviewDialogVisible = ref(false)
const reviewDecision = ref('通过')
const reviewComment = ref('')
const reviewCorrectionFields = ref([])
const reviewing = ref(false)

const CORRECTION_FIELD_OPTIONS = [
  { value: '①任务与样品确认', label: '① 任务与样品确认｜样品接收、编号或状态确认' },
  { value: '②设备与实验前检查', label: '② 设备与实验前检查｜设备状态、校准信息或异常说明' },
  { value: '③环境与参数', label: '③ 环境与参数｜温湿度、实验参数' },
  { value: '④原始数据', label: '④ 原始数据｜测量数据、计算结果' },
  { value: '⑤母版过程确认', label: '⑤ 母版过程确认｜受控模板补充字段' },
  { value: '⑥照片留档', label: '⑥ 照片留档｜实验照片和证据' },
  { value: '⑦实验员自查', label: '⑦ 实验员自查｜提交前自查确认' },
]

const canReview = computed(() => {
  if (userRole.value !== '复核员') return false
  if (!record.value?.status || !['待复核', '更正待复核'].includes(record.value.status)) return false
  return true
})

function openReviewDialog() {
  reviewDecision.value = '通过'
  reviewComment.value = ''
  reviewCorrectionFields.value = []
  reviewDialogVisible.value = true
}

async function submitReview() {
  if (reviewDecision.value === '退回') {
    if (!reviewComment.value.trim()) { ElMessage.warning('退回时必须填写复核意见'); return }
    if (!reviewCorrectionFields.value.length) { ElMessage.warning('退回时必须至少指定一个需要修改的字段'); return }
  }
  reviewing.value = true
  try {
    const resp = await request.post(`/records/${recordNo}/review`, {
      decision: reviewDecision.value,
      comment: reviewComment.value,
      correction_fields: reviewCorrectionFields.value,
    })
    ElMessage.success(resp.data?.message || `复核${reviewDecision.value}`)
    reviewDialogVisible.value = false
    await loadRecord()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '复核失败')
  } finally {
    reviewing.value = false
  }
}

// Status tag type
function getStatusType(status) {
  const map = { '草稿': 'info', '待复核': 'warning', '更正待复核': 'danger', '已锁定': 'success', '复核退回': 'info' }
  return map[status] || 'info'
}

onMounted(loadRecord)
</script>

<template>
  <div class="page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1>原始记录查看</h1>
        <div class="subtitle">
          {{ record?.record_no }} V{{ record?.version }}
          <el-tag :type="getStatusType(record?.status)" size="small" style="margin-left:8px">{{ record?.status }}</el-tag>
        </div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <el-button type="primary" @click="openWordPreview" :loading="wordPreviewLoading">📄 Word预览</el-button>
        <el-button v-if="['管理员','质量负责人','复核员'].includes(userRole)" @click="downloadWord">📥 下载Word</el-button>
        <el-button v-if="canReview" type="warning" @click="openReviewDialog">复核</el-button>
        <el-button @click="router.back()">返回</el-button>
      </div>
    </div>

    <div v-if="loading" style="text-align:center;padding:60px"><el-icon class="is-loading" :size="32"><Loading /></el-icon></div>

    <template v-if="record && !loading">
      <!-- Info bar -->
      <el-descriptions :column="4" border size="small" style="margin-bottom:16px">
        <el-descriptions-item label="实验项目">{{ record.experiment || '-' }}</el-descriptions-item>
        <el-descriptions-item label="任务编号">{{ record.task_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="实验员">{{ record.owner || '-' }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ record.created_at || '-' }}</el-descriptions-item>
        <el-descriptions-item label="检测方法">{{ task?.method_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="检测依据">{{ task?.standard || '-' }}</el-descriptions-item>
        <el-descriptions-item label="材料">{{ task?.material_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="检测地点">{{ task?.detection_location || '-' }}</el-descriptions-item>
      </el-descriptions>

      <!-- Review history -->
      <el-card v-if="record.reviews?.length" shadow="never" class="mb-card">
        <template #header><strong>复核历史</strong></template>
        <el-timeline>
          <el-timeline-item v-for="(r, i) in record.reviews" :key="i"
            :timestamp="r.reviewed_at" :type="r.decision === '通过' ? 'success' : 'danger'"
            :hollow="r.decision === '通过'">
            <div><strong>{{ r.reviewer }}</strong> — {{ r.decision }}</div>
            <div v-if="r.comment" style="color:#64748B">{{ r.comment }}</div>
            <div v-if="r.correction_fields" style="font-size:12px;color:#94A3B8">
              指定修改字段：{{ Array.isArray(r.correction_fields) ? r.correction_fields.join('、') : r.correction_fields }}
            </div>
          </el-timeline-item>
        </el-timeline>
      </el-card>

      <!-- ① Task Confirmation -->
      <el-card shadow="never" class="mb-card">
        <template #header><strong>① 任务与样品确认</strong></template>
        <div style="display:flex;gap:32px">
          <el-checkbox :model-value="taskConfirmations.sample_received" disabled>样品已收到</el-checkbox>
          <el-checkbox :model-value="taskConfirmations.number_match" disabled>样品编号一致</el-checkbox>
          <el-checkbox :model-value="taskConfirmations.sample_condition" disabled>样品状态正常</el-checkbox>
        </div>
      </el-card>

      <!-- ② Equipment -->
      <el-card shadow="never" class="mb-card">
        <template #header><strong>② 设备与实验前检查</strong></template>
        <el-empty v-if="!equipmentChecks.length" description="无设备记录" />
        <div v-else class="equip-grid">
          <el-card v-for="(eq,i) in equipmentChecks" :key="i" shadow="never"
            :class="{'equip-err':eq.status==='异常'}" style="margin-bottom:8px">
            <div style="display:flex;gap:16px">
              <div style="flex:1.3">
                <div style="font-weight:600">{{ eq.equipment_name }}</div>
                <div style="color:#64748B;font-size:13px">管理编号：<code>{{ eq.management_no }}</code></div>
              </div>
              <div style="flex:1;font-size:12px;color:#64748B;line-height:1.6">
                <div>测量范围：{{ eq.measuring_range || '-' }}</div>
                <div>校准日期：{{ eq.calibration_time || '-' }}</div>
                <div>负责人：{{ eq.responsible || '-' }}</div>
              </div>
              <div style="flex:1">
                <el-tag :type="eq.status==='异常'?'danger':'success'" size="small">{{ eq.status }}</el-tag>
                <div v-if="eq.note" style="font-size:12px;color:#EF4444;margin-top:4px">{{ eq.note }}</div>
              </div>
            </div>
          </el-card>
        </div>
        <div v-if="precheckAllItems.length" style="margin-top:12px">
          <div style="font-weight:600;margin-bottom:6px">实验前检查项</div>
          <el-checkbox-group :model-value="prechecks" disabled>
            <el-checkbox v-for="(item,i) in precheckAllItems" :key="i" :value="item" style="margin-right:12px">{{ item }}</el-checkbox>
          </el-checkbox-group>
          <div v-if="precheckNote" style="margin-top:8px;color:#EF4444;font-size:13px">异常说明：{{ precheckNote }}</div>
        </div>
      </el-card>

      <!-- ③ Environment & Parameters — restructured -->
      <el-card shadow="never" class="mb-card">
        <template #header><strong>③ 环境与参数</strong></template>

        <!-- Fallback: no config loaded -->
        <template v-if="!config">
          <el-descriptions v-if="Object.keys(formData).length" :column="3" border size="small">
            <el-descriptions-item v-for="(val, key) in formData" :key="key" :label="key">{{ val || '-' }}</el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="无环境参数数据" />
        </template>

        <!-- Config-driven layout -->
        <template v-else>
          <!-- Readonly sections -->
          <el-card v-for="(sec,si) in visibleReadonly" :key="'ri'+si" shadow="never" class="mb-card-sm">
            <template #header><strong>{{ sec.title }}</strong></template>
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item v-for="f in sec.fields" :key="f.key" :label="f.label">{{ formatFieldValue(formData[f.key]) }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- Environment fields -->
          <el-card v-if="envFields.length" shadow="never" class="mb-card-sm">
            <template #header><strong>环境与实验参数</strong></template>
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item v-for="f in envFields" :key="f.key" :label="f.label">
                {{ formatFieldValue(formData[f.key]) }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- Fixed parameters -->
          <el-card v-if="fixedFields.length" shadow="never" class="mb-card-sm">
            <template #header><strong>固定参数</strong></template>
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item v-for="f in fixedFields" :key="f.key" :label="f.label">
                {{ formatFieldValue(formData[f.key] || f.default) }}
              </el-descriptions-item>
            </el-descriptions>
            <div v-if="fixedParamMode" style="margin-top:8px">
              <span style="font-size:13px;color:#475569">固定参数执行情况：</span>
              <el-tag size="small" :type="fixedParamMode==='存在偏离'?'warning':'success'">{{ fixedParamMode }}</el-tag>
            </div>
          </el-card>

          <!-- Core manual fields -->
          <el-card v-if="coreManualFields.length" shadow="never" class="mb-card-sm">
            <template #header><strong>本次核查与实际记录</strong></template>
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item v-for="f in coreManualFields" :key="f.key" :label="f.label">
                {{ formatFieldValue(formData[f.key]) }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- Process monitoring fields -->
          <el-card v-if="processFields.length" shadow="never" class="mb-card-sm">
            <template #header><strong>过程监测明细</strong></template>
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item v-for="f in processFields" :key="f.key" :label="f.label">
                {{ formatFieldValue(formData[f.key]) }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-empty v-if="!visibleReadonly.length && !envFields.length && !fixedFields.length && !coreManualFields.length && !processFields.length" description="无环境参数数据" />
        </template>
      </el-card>

      <!-- ④ Measurement Data — restructured -->
      <el-card shadow="never" class="mb-card">
        <template #header>
          <strong>④ 原始数据</strong>
          <span style="margin-left:8px;font-size:12px;color:#94A3B8">{{ measurementRows.length }} 条记录</span>
        </template>

        <!-- Fallback: no config -->
        <template v-if="!config || !visibleColumns">
          <el-empty v-if="!measurementRows.length" description="无测量数据" />
          <el-table v-else :data="measurementRows" border stripe size="small" max-height="500">
            <el-table-column v-for="col in Object.keys(measurementRows[0] || {}).filter(k => !k.startsWith('_'))" :key="col" :prop="col" :label="col" min-width="100" show-overflow-tooltip />
          </el-table>
        </template>

        <!-- Config-driven layout: per-sample cards -->
        <template v-else>
          <el-empty v-if="!visibleColumns.length" description="本实验无测量数据表格" />
          <div v-else>
            <div v-for="[sno, rows] in sampleGroups" :key="sno" style="margin-bottom:16px">
              <el-card shadow="never" class="mb-card-sm">
                <template #header><strong>样品：{{ sno }}</strong></template>
                <div v-for="row in rows" :key="'row-'+row._index" style="margin-bottom:12px;padding:10px;border:1px solid #E2E8F0;border-radius:8px;background:#FAFBFC">
                  <div v-if="row.face" style="font-weight:600;font-size:13px;color:#0F172A;margin-bottom:8px">{{ row.face }}</div>

                  <!-- Input fields -->
                  <el-row :gutter="12">
                    <el-col v-for="col in inputColumns" :key="col.column_key" :span="8" style="margin-bottom:8px">
                      <div style="font-size:11px;color:#64748B;margin-bottom:2px">{{ col.column_label }}</div>
                      <div style="font-size:14px;color:#0F172A;font-weight:500">{{ row[col.column_key] != null && row[col.column_key] !== '' ? row[col.column_key] : '-' }}</div>
                    </el-col>
                  </el-row>

                  <!-- Calculated fields -->
                  <div v-if="calcColumns.length" style="margin-top:10px;padding:8px 12px;background:#F1F5F9;border-radius:6px">
                    <div style="font-size:11px;font-weight:600;color:#475569;margin-bottom:4px">实时计算与判定</div>
                    <el-row :gutter="12">
                      <el-col v-for="col in calcColumns" :key="col.column_key" :span="8">
                        <div style="font-size:11px;color:#64748B">{{ col.column_label }}</div>
                        <div style="font-size:15px;font-weight:600;color:#0F172A">{{ row[col.column_key] != null && row[col.column_key] !== '' ? row[col.column_key] : '等待原始数据' }}</div>
                      </el-col>
                    </el-row>
                    <div v-if="row.conclusion" style="margin-top:6px">
                      <el-tag v-if="['符合','合格'].includes(row.conclusion)" type="success" size="small">✓ {{ row.conclusion }}</el-tag>
                      <el-tag v-else-if="['不符合','不合格'].includes(row.conclusion)" type="danger" size="small">✗ {{ row.conclusion }}</el-tag>
                      <el-tag v-else type="info" size="small">{{ row.conclusion }}</el-tag>
                    </div>
                  </div>

                  <!-- Note -->
                  <div v-if="row.note" style="margin-top:6px;font-size:12px;color:#EF4444">备注：{{ row.note }}</div>
                </div>
              </el-card>
            </div>
          </div>
        </template>

        <!-- ── Photos embedded in section ④ (same as ExperimentRun.vue) ── -->
        <el-card v-if="photoCheckpoints.length" shadow="never" class="mb-card" style="margin-top:16px">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <strong>拍照留档</strong>
              <span style="font-size:12px" :style="{color:missingPhotos?'#EA580C':'#22C55E'}">{{ photoCompletionCount }}/{{ totalPhotoRequired }} 已完成{{ missingPhotos ? '（'+missingPhotos+'张未拍）' : ' ✓' }}</span>
            </div>
          </template>
          <div v-for="(cps, groupName) in photoCheckpointGroups" :key="groupName" style="margin-bottom:16px">
            <div style="font-size:13px;font-weight:600;color:#475569;margin-bottom:8px;padding:4px 8px;background:#F1F5F9;border-radius:4px">
              {{ groupName }}
              <span style="font-weight:400;color:#94A3B8;font-size:12px;margin-left:8px">{{ cps.filter(cp=>cp.hasPhoto).length }}/{{ cps.length }} 节点已拍照</span>
            </div>
            <div v-for="cp in cps" :key="cp.code" style="margin-bottom:10px;padding:10px;border:1px solid #E2E8F0;border-radius:8px;background:#FAFBFC">
              <div style="font-size:13px;font-weight:500;color:#0F172A;margin-bottom:6px">
                <span v-if="cp.required!==false" style="color:#EF4444;font-weight:700">*</span> {{ cp.label }}
                <el-tag v-if="cp.isSampleLevel" size="small" type="info" style="margin-left:4px">逐样拍摄</el-tag>
                <el-tag v-if="cp.hasPhoto" size="small" type="success" style="margin-left:6px">已拍摄</el-tag>
                <el-tag v-else size="small" type="info" style="margin-left:6px">未拍摄</el-tag>
              </div>

              <!-- Task-level photo -->
              <template v-if="!cp.isSampleLevel">
                <div v-if="cp.previewUrl" style="text-align:center;margin-bottom:6px">
                  <img :src="cp.previewUrl" style="max-width:300px;max-height:200px;border-radius:6px;border:1px solid #E2E8F0" loading="lazy" />
                </div>
              </template>

              <!-- Per-sample photos -->
              <div v-if="cp.isSampleLevel && sampleIds.length" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:6px">
                <div v-for="sno in sampleIds" :key="sno" style="display:flex;flex-direction:column;align-items:center;gap:4px;padding:6px;background:#F8FAFC;border-radius:6px;border:1px solid #E2E8F0">
                  <span style="font-size:11px;font-weight:500;color:#64748B">{{ sno }}</span>
                  <img v-if="cp.samplePhotos[sno]?.previewUrl" :src="cp.samplePhotos[sno].previewUrl" style="max-width:180px;max-height:120px;border-radius:4px;border:1px solid #CBD5E1" loading="lazy" />
                  <span v-else style="font-size:11px;color:#EF4444">未拍摄</span>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-card>

      <!-- ⑤ Template Supplement — restructured -->
      <el-card shadow="never" class="mb-card">
        <template #header><strong>⑤ 母版过程确认</strong></template>

        <!-- Fallback: no manifest -->
        <template v-if="!manifestFields.length">
          <el-descriptions v-if="templateFields.length" :column="2" border size="small">
            <el-descriptions-item v-for="tf in templateFields" :key="tf.key" :label="tf.label || tf.key">
              {{ tf.value || '-' }}
            </el-descriptions-item>
          </el-descriptions>
          <div v-if="!templateFields.length" style="padding:16px;background:#F0FDF4;border-radius:8px;border:1px solid #BBF7D0">
            <span style="color:#166534">✅ 受控原始记录模板全部字段已由前序数据、实验记录或系统规则覆盖。</span>
          </div>
        </template>

        <!-- Template-manifest-driven layout -->
        <template v-else>
          <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
            <el-descriptions-item label="SOP版本">{{ config?.sop_version || 'A/0' }}</el-descriptions-item>
            <el-descriptions-item label="原始记录模板">{{ config?.record_template_file || config?.record_template_version || '-' }}</el-descriptions-item>
            <el-descriptions-item label="实验配置版本">{{ config?.version || '-' }}</el-descriptions-item>
            <el-descriptions-item label="检测标准">{{ task?.standard || '-' }}</el-descriptions-item>
          </el-descriptions>

          <div v-if="!mergedTemplateFields.length" style="padding:16px;background:#F0FDF4;border-radius:8px;border:1px solid #BBF7D0">
            <span style="color:#166534">✅ 受控原始记录模板全部字段已由前序数据、实验记录或系统规则覆盖。</span>
          </div>

          <div v-else>
            <div style="margin-bottom:12px;padding:8px 12px;background:#EFF6FF;border-radius:6px;border:1px solid #BFDBFE">
              <span style="color:#1E40AF;font-size:13px">母版过程确认：{{ mergedTemplateFields.filter(f => f.value).length }}/{{ mergedTemplateFields.length }} 项已完成。</span>
            </div>

            <div v-for="(sectionFields, sectionName) in mergedTemplateGrouped" :key="sectionName" style="margin-bottom:16px">
              <el-collapse>
                <el-collapse-item :title="`${sectionName}｜${sectionFields.filter(f=>f.value).length}/${sectionFields.length} 已完成`" :name="sectionName">
                  <el-row :gutter="16">
                    <el-col v-for="f in sectionFields" :key="f.key" :span="8" style="margin-bottom:12px">
                      <div style="font-size:12px;color:#64748B;margin-bottom:3px">{{ f.label || f.position || f.key }}</div>
                      <!-- Checkbox fields: show parsed selections -->
                      <template v-if="(f.template_text || '').includes('□') || (f.template_text || '').includes('☐')">
                        <div style="font-size:11px;color:#94A3B8;margin-bottom:3px">
                          选项：{{ _checkboxChoices(f.template_text || '').join('、') }}
                        </div>
                        <div style="font-size:13px;font-weight:500;color:#0F172A">
                          {{ _parseCheckboxValue(f.template_text || '', f.value || '').selected.join('、') || '未选择' }}
                        </div>
                      </template>
                      <!-- Blank-fill fields -->
                      <template v-else>
                        <div style="font-size:13px;font-weight:500;color:#0F172A">{{ f.value || '-' }}</div>
                      </template>
                    </el-col>
                  </el-row>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </template>
      </el-card>

      <!-- ⑦ Tester Self-Check & Conclusion -->
      <el-card shadow="never" class="mb-card">
        <template #header><strong>⑦ 实验员自查与结论</strong></template>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="整体状态">{{ overallStatus || '-' }}</el-descriptions-item>
          <el-descriptions-item label="实验员自查">
            <el-tag :type="testerSelfCheck ? 'success' : 'info'" size="small">{{ testerSelfCheck ? '已完成' : '未完成' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="异常与偏离" :span="2">{{ deviation || '无' }}</el-descriptions-item>
          <el-descriptions-item label="复验说明" :span="2">{{ retest || '-' }}</el-descriptions-item>
          <el-descriptions-item label="结果摘要" :span="2">{{ reportSummary || '-' }}</el-descriptions-item>
          <el-descriptions-item label="结论" :span="2">{{ reportConclusion || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </template>

    <!-- Word Preview Dialog -->
    <el-dialog v-model="wordPreviewVisible" title="受控Word在线预览" width="90%" top="3vh" :close-on-click-modal="false" destroy-on-close>
      <div v-if="wordPreviewLoading" style="display:flex;justify-content:center;align-items:center;min-height:400px">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <span style="margin-left:12px">正在生成Word预览…</span>
      </div>
      <iframe v-else :srcdoc="wordPreviewHtml" style="width:100%;height:70vh;border:1px solid #E2E8F0;border-radius:8px" sandbox="allow-same-origin" />
    </el-dialog>

    <!-- Review Dialog -->
    <el-dialog v-model="reviewDialogVisible" title="复核原始记录" width="580px" :close-on-click-modal="false">
      <template v-if="record">
        <el-descriptions :column="2" border size="small" style="margin-bottom:20px">
          <el-descriptions-item label="记录编号">{{ record.record_no }}</el-descriptions-item>
          <el-descriptions-item label="版本">V{{ record.version }}</el-descriptions-item>
          <el-descriptions-item label="检测项目" :span="2">{{ record.experiment }}</el-descriptions-item>
          <el-descriptions-item label="实验员">{{ record.owner }}</el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ record.created_at }}</el-descriptions-item>
        </el-descriptions>

        <el-form label-width="100px">
          <el-form-item label="复核决定" required>
            <el-radio-group v-model="reviewDecision">
              <el-radio value="通过">通过 — 锁定记录并自动生成检验报告</el-radio>
              <el-radio value="退回">退回 — 退回实验员修改</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="复核意见" required>
            <el-input v-model="reviewComment" type="textarea" :rows="3" placeholder="填写复核意见（退回时必须填写）" />
          </el-form-item>
          <el-form-item v-if="reviewDecision === '退回'" label="修改字段" required>
            <el-select v-model="reviewCorrectionFields" multiple placeholder="至少选择一个需要修改的字段" style="width:100%">
              <el-option v-for="opt in CORRECTION_FIELD_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
            <div style="font-size:11px;color:#94A3B8;margin-top:4px">
              只有被选中的字段和步骤才允许实验员修改，其余字段将被锁定只读
            </div>
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
  </div>
</template>

<style scoped>
.page { max-width: 1400px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
.subtitle { font-size: 14px; color: #64748B; margin-top: 4px; }
.mb-card { margin-bottom: 16px; }
.mb-card-sm { margin-bottom: 12px; }
.equip-grid { display: flex; flex-direction: column; gap: 8px; }
.equip-err { border-left: 3px solid #EF4444; }
</style>
