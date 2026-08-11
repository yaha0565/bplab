<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '../utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, VideoPause, Plus, Delete, Camera } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const user = JSON.parse(localStorage.getItem('user') || '{}')
const isAssignee = computed(() => task.value?.assignee === user.username)
const isTester = computed(() => user.role === '实验员')
const taskNo = route.params.taskNo

const task = ref(null)
const config = ref(null)
const commission = ref(null)
const sampleGroup = ref(null)
const loading = ref(true)
const saving = ref(false)
const acting = ref(false)
const activeTab = ref('1')

const formData = reactive({})
const measurementRows = ref([])
const photoCheckpoints = ref([])
const cameraHints = ref({})

// ── Inline camera state (replaces global camera) ──
const activeCameraCp = ref(null)     // which checkpoint's camera is open
const activeCameraSample = ref('')   // which sample within that checkpoint
import CameraCapture from '../components/CameraCapture.vue'

// ── Tab 1: Task confirmations ──
const taskConfirmations = reactive({ sample_received: true, number_match: true, sample_condition: true })

// ── Tab 2: Equipment & Prechecks ──
const equipmentChecks = ref([])
const precheckAllItems = ref([])
const precheckSelected = ref([])
const precheckNote = ref('')
const addingEquipment = ref(false)
const addEquipmentSelection = ref('')
const availableEquipment = ref([])
const loadingEquipment = ref(false)

async function loadAvailableEquipment() {
  loadingEquipment.value = true
  try {
    const { data } = await request.get('/equipment', { params: { limit: 200 } })
    availableEquipment.value = data || []
  } catch { availableEquipment.value = [] }
  finally { loadingEquipment.value = false }
}

function addEquipment(mgmtNo) {
  const eq = availableEquipment.value.find(e => e.management_no === mgmtNo)
  if (!eq) return
  if (equipmentChecks.value.some(e => e.management_no === mgmtNo)) {
    ElMessage.warning('该设备已在列表中')
    return
  }
  equipmentChecks.value.push({
    management_no: eq.management_no || '',
    equipment_name: eq.equipment_name || '',
    model: eq.model || '',
    binding_role: 'auxiliary',
    measuring_range: eq.measuring_range || '',
    manufacturer: eq.manufacturer || '',
    serial_no: eq.serial_no || '',
    calibration_time: eq.calibration_time || '',
    equipment_class: eq.equipment_class || '',
    responsible: eq.responsible || '',
    status: '正常', note: '', required: false,
  })
  addingEquipment.value = false
}

function removeEquipment(index) {
  const eq = equipmentChecks.value[index]
  if (eq.required) {
    ElMessage.warning('配置必需设备不可移除，仅可移除手动添加的辅助设备')
    return
  }
  equipmentChecks.value.splice(index, 1)
}

// ── Tab 4: Parameters ──
const fixedParamMode = ref('按默认参数执行')

// ── Tab 5: Template supplement ──
const templateFields = ref([])

// ── Tab 6: Exception & device files ──
const overallStatus = ref('正常完成')
const deviation = ref('')
const retest = ref('否')

// ── Tab 7: Save ──
const reportSummary = ref('')
const reportConclusion = ref('')
const testerSelfCheck = ref(false)
const changeReason = ref('')
const validationReady = ref(false)
const syncing = ref(false)

// ── Emergency interruption ──
const emergencyForm = reactive({
  fault_equipment: '', fault_type: '', error_code: '无',
  fault_description: '', current_stage: '原始数据采集',
  completed_steps: '', collected_data: '', sample_condition: '',
  site_risks: [], immediate_actions: [],
})
const emergencyConfirm = ref(false)
const submittingEmergency = ref(false)

async function submitEmergency() {
  if (!emergencyForm.fault_equipment || !emergencyForm.fault_type) {
    ElMessage.warning('请至少填写故障设备和故障类型')
    return
  }
  if (!emergencyConfirm.value) {
    ElMessage.warning('请确认故障信息，勾选确认后提交')
    return
  }
  submittingEmergency.value = true
  try {
    await request.post('/incidents', {
      task_no: taskNo,
      incident_type: '设备故障',
      fault_equipment: emergencyForm.fault_equipment,
      fault_type: emergencyForm.fault_type,
      error_code: emergencyForm.error_code,
      fault_description: emergencyForm.fault_description,
      current_stage: emergencyForm.current_stage,
      completed_steps: emergencyForm.completed_steps,
      collected_data: emergencyForm.collected_data,
      sample_condition: emergencyForm.sample_condition,
      site_risks: emergencyForm.site_risks,
      immediate_actions: emergencyForm.immediate_actions,
    })
    ElMessage.success('故障中断已提交，任务已冻结')
    router.push('/my-tasks')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '提交故障中断失败')
  } finally {
    submittingEmergency.value = false
  }
}

// ── Device file upload ──
const deviceFileType = ref('设备原始数据文件')
const deviceFileSampleNo = ref('')
const deviceFiles = ref([])
const uploadingFiles = ref(false)

function handleDeviceFileChange(file) {
  deviceFiles.value.push(file.raw)
}

async function uploadDeviceFiles() {
  if (!deviceFileType.value || !deviceFiles.value.length) {
    ElMessage.warning('请选择文件类型并上传文件')
    return
  }
  uploadingFiles.value = true
  try {
    const fd = new FormData()
    fd.append('task_no', taskNo)
    fd.append('attachment_type', deviceFileType.value)
    fd.append('capture_source', 'device_export')
    if (deviceFileSampleNo.value) fd.append('sample_no', deviceFileSampleNo.value)
    for (const f of deviceFiles.value) {
      fd.append('files', f)
    }
    await request.post('/attachments/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const sampleInfo = deviceFileSampleNo.value ? `（关联样品 ${deviceFileSampleNo.value}）` : ''
    ElMessage.success(`已保存 ${deviceFiles.value.length} 个设备文件${sampleInfo}`)
    deviceFiles.value = []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '上传失败')
  } finally {
    uploadingFiles.value = false
  }
}

// ── Inline camera helpers ──
function openCamera(cp, sampleNo) {
  activeCameraCp.value = cp
  activeCameraSample.value = sampleNo || ''
}
function closeCamera() {
  activeCameraCp.value = null
  activeCameraSample.value = ''
}

// ── Full state reset before loading a new task (data isolation) ──
function resetAllState() {
  recordVersion.value = 1
  for (const key of Object.keys(formData)) delete formData[key]
  measurementRows.value = []
  photoCheckpoints.value = []
  equipmentChecks.value = []
  precheckAllItems.value = []
  precheckSelected.value = []
  precheckNote.value = ''
  templateFields.value = []
  reviewReturn.value = null
  correctionFields.value = []
  reportSummary.value = ''
  reportConclusion.value = ''
  testerSelfCheck.value = false
  changeReason.value = ''
  overallStatus.value = '正常完成'
  deviation.value = ''
  retest.value = '否'
  fixedParamMode.value = '按默认参数执行'
  activeTab.value = '1'
  closeCamera()
  task.value = null
  config.value = null
  commission.value = null
  sampleGroup.value = null
}

// ── Data Loading ──
async function loadExperimentData() {
  resetAllState()
  loading.value = true
  const currentTaskNo = route.params.taskNo
  try {
    const { data: taskData } = await request.get(`/tasks/${currentTaskNo}`)
    task.value = taskData.task
    if (!task.value) { ElMessage.error('任务不存在'); loading.value = false; return }

    // Load correction info from task API for 退回修改 tasks
    if (taskData.correction) {
      reviewReturn.value = taskData.correction
      try {
        correctionFields.value = typeof taskData.correction.correction_fields === 'string'
          ? JSON.parse(taskData.correction.correction_fields)
          : (taskData.correction.correction_fields || [])
      } catch { correctionFields.value = [] }
    }

    if (task.value.experiment_code) {
      try {
        const cfgRes = await request.get(`/config/${task.value.experiment_code}`)
        const raw = cfgRes.data || {}
        if ((!raw.fields || !raw.fields.length) && (!raw.columns || !raw.columns.length)) {
          config.value = null
        } else {
          config.value = raw
          initFormDefaults()
          initMeasurementRows()
          initEquipmentChecks()
          initPhotoCheckpoints()
          const kind = config.value?.kind || ''
          const rawPrechecks = (raw.prechecks || []).map(pc => pc.label || pc)
          precheckAllItems.value = rawPrechecks.length ? rawPrechecks
            : (PRECHECKS_BY_KIND[kind] || PRECHECKS_BY_KIND.generic)
          precheckSelected.value = [...precheckAllItems.value]
          // Load template manifest for Tab ⑤
          loadTemplateManifest(task.value.experiment_code)
        }
      } catch (e) { config.value = null }
    }

    if (task.value.commission_no) {
      try {
        const { data: commData } = await request.get(`/commissions/${task.value.commission_no}`)
        commission.value = commData
        if (commData.sample_groups?.length && task.value.group_no) {
          sampleGroup.value = commData.sample_groups.find(g => g.group_no === task.value.group_no) || commData.sample_groups[0]
        }
      } catch { }
    }

    // Restore draft from server — fetch latest version, not hardcoded v1
    let hasServerDraft = false
    try {
      let latestVersion = 0
      try {
        const verRes = await request.get(`/records/${currentTaskNo}/versions`)
        if (verRes.data?.length) {
          latestVersion = verRes.data[0].version
        }
      } catch { latestVersion = 0 }

      if (latestVersion > 0) {
        const recRes = await request.get(`/records/${currentTaskNo}/v${latestVersion}`)
        if (recRes.data) {
          recordVersion.value = latestVersion
          if (recRes.data.payload) {
            hasServerDraft = true
            const pl = typeof recRes.data.payload === 'string' ? JSON.parse(recRes.data.payload) : recRes.data.payload
          if (pl._form) Object.assign(formData, pl._form)
          if (pl._rows) { measurementRows.value = pl._rows; measurementRows.value.forEach(r => { if (r._showNote === undefined) r._showNote = false }) }
          if (pl._photos) restorePhotos(pl._photos)
          if (pl._task_confirmations) Object.assign(taskConfirmations, pl._task_confirmations)
          if (pl._equipment_checks) {
            const savedMap = new Map(pl._equipment_checks.map(e => [e.management_no, e]))
            for (const eq of equipmentChecks.value) {
              const saved = savedMap.get(eq.management_no)
              if (saved) { eq.status = saved.status || '正常'; eq.note = saved.note || '' }
            }
          }
          if (pl._prechecks) precheckSelected.value = pl._prechecks
          if (pl._precheck_note) precheckNote.value = pl._precheck_note
          if (pl._precheck_all_items) precheckAllItems.value = pl._precheck_all_items
          if (pl._fixed_param_mode) fixedParamMode.value = pl._fixed_param_mode
          if (pl._overall_status) overallStatus.value = pl._overall_status
          if (pl._deviation) deviation.value = pl._deviation
          if (pl._retest) retest.value = pl._retest
          reportSummary.value = pl._report_summary || recRes.data.report_summary || ''
          reportConclusion.value = pl._report_conclusion || recRes.data.report_conclusion || ''
          testerSelfCheck.value = pl._tester_self_check || recRes.data.tester_self_check || false
          changeReason.value = recRes.data.change_reason || ''
          if (pl._template_fields) {
            for (const tf of pl._template_fields) {
              const existing = templateFields.value.find(f => f.key === tf.key)
              if (existing) existing.value = tf.value || ''
            }
          }
        }
        const reviews = recRes.data.reviews || []
        const returnReview = [...reviews].reverse().find(r => r.decision === '退回')
        if (returnReview) {
          reviewReturn.value = reviewReturn.value || returnReview
          if (!correctionFields.value.length) {
            try {
              correctionFields.value = typeof returnReview.correction_fields === 'string'
                ? JSON.parse(returnReview.correction_fields)
                : (returnReview.correction_fields || [])
            } catch { correctionFields.value = [] }
          }
        }
      }
      }
    } catch { }

    if (!hasServerDraft) {
      restoreFromLocalStorage()
    }

    if (isSecondaryEdit.value && correctionFields.value.length) {
      setTimeout(() => focusReturnedStep(), 300)
    }
  } catch (e) {
    ElMessage.error('加载实验页面失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => { loadExperimentData() })

// Detect navigation between tasks and reload (data isolation)
watch(() => route.params.taskNo, (newVal, oldVal) => {
  if (newVal && oldVal && newVal !== oldVal) {
    saveDraftToLocalStorage()
    loadExperimentData()
  }
})

onBeforeUnmount(() => { closeCamera(); saveDraftToLocalStorage() })

// ── localStorage draft persistence (matching Streamlit save_form_draft/load_form_draft) ──
const DRAFT_KEY = `experiment_draft_${taskNo}`

function saveDraftToLocalStorage() {
  if (!canEdit.value) return
  try {
    const draft = {
      _form: { ...formData },
      _rows: measurementRows.value.map(r => {
        const clean = {}
        for (const [k, v] of Object.entries(r)) {
          if (v instanceof File || v instanceof Blob) continue
          if (typeof v === 'number' && !isFinite(v)) clean[k] = null
          else clean[k] = v
        }
        return clean
      }),
      _photos: photoCheckpoints.value.map(cp => ({
        code: cp.code, label: cp.label,
        previewUrl: cp.previewUrl || '',
        samplePhotos: Object.fromEntries(
          Object.entries(cp.samplePhotos || {}).map(([sn, data]) => [sn, { previewUrl: data?.previewUrl || '' }])
        ),
      })),
      _task_confirmations: { ...taskConfirmations },
      _equipment_checks: equipmentChecks.value.map(e => ({ ...e })),
      _prechecks: [...precheckSelected.value], _precheck_note: precheckNote.value,
      _precheck_all_items: [...precheckAllItems.value], _fixed_param_mode: fixedParamMode.value,
      _overall_status: overallStatus.value, _deviation: deviation.value, _retest: retest.value,
      _report_summary: reportSummary.value || '', _report_conclusion: reportConclusion.value || '',
      _tester_self_check: testerSelfCheck.value, _change_reason: changeReason.value,
      _template_fields: templateFields.value.map(f => ({ key: f.key, value: f.value || '' })),
      _active_tab: activeTab.value,
      _saved_at: new Date().toISOString(),
    }
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))
  } catch { /* localStorage may be full or unavailable */ }
}

function restoreFromLocalStorage() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    if (!raw) return false
    const pl = JSON.parse(raw)
    if (pl._form) Object.assign(formData, pl._form)
    if (pl._rows) { measurementRows.value = pl._rows; measurementRows.value.forEach(r => { if (r._showNote === undefined) r._showNote = false }) }
    if (pl._photos) restorePhotos(pl._photos)
    if (pl._task_confirmations) Object.assign(taskConfirmations, pl._task_confirmations)
    if (pl._equipment_checks) {
      // Merge saved status/note into fresh config equipment ONLY
      const savedMap = new Map(pl._equipment_checks.map(e => [e.management_no, e]))
      for (const eq of equipmentChecks.value) {
        const saved = savedMap.get(eq.management_no)
        if (saved) { eq.status = saved.status || '正常'; eq.note = saved.note || '' }
      }
    }
    if (pl._prechecks) precheckSelected.value = pl._prechecks
    if (pl._precheck_note) precheckNote.value = pl._precheck_note
    if (pl._precheck_all_items) precheckAllItems.value = pl._precheck_all_items
    if (pl._fixed_param_mode) fixedParamMode.value = pl._fixed_param_mode
    if (pl._overall_status) overallStatus.value = pl._overall_status
    if (pl._deviation) deviation.value = pl._deviation
    if (pl._retest) retest.value = pl._retest
    if (pl._report_summary) reportSummary.value = pl._report_summary
    if (pl._report_conclusion) reportConclusion.value = pl._report_conclusion
    if (pl._tester_self_check) testerSelfCheck.value = pl._tester_self_check
    if (pl._change_reason) changeReason.value = pl._change_reason
    if (pl._template_fields) {
      for (const tf of pl._template_fields) {
        const existing = templateFields.value.find(f => f.key === tf.key)
        if (existing) existing.value = tf.value || ''
      }
    }
    if (pl._active_tab) activeTab.value = pl._active_tab
    return true
  } catch { return false }
}

function clearLocalDraft() {
  try { localStorage.removeItem(DRAFT_KEY) } catch { }
}

// ── File upload fallback (when camera unavailable) ──
function handleFileUpload(uploadFile, cp, sampleNo) {
  const file = uploadFile.raw || uploadFile
  if (!file) return
  const url = URL.createObjectURL(file)
  const sn = sampleNo || null
  if (sn && cp.isSampleLevel) {
    if (!cp.samplePhotos) cp.samplePhotos = {}
    const old = cp.samplePhotos[sn]
    if (old?.previewUrl && old.previewUrl.startsWith('blob:')) URL.revokeObjectURL(old.previewUrl)
    cp.samplePhotos[sn] = { file, previewUrl: url }
  } else {
    if (cp.previewUrl && cp.previewUrl.startsWith('blob:')) URL.revokeObjectURL(cp.previewUrl)
    cp.file = file
    cp.previewUrl = url
  }
  ElMessage.success('照片已导入')
}

// ── Auto-save draft on tab change (server + localStorage) ──
watch(activeTab, async (newTab, oldTab) => {
  // 切换标签页时释放摄像头（避免占用导致后续无法打开）
  if (activeCameraCp.value && newTab !== oldTab) {
    closeCamera()
  }
  if (oldTab !== '7' && newTab !== oldTab && canEdit.value) {
    saveDraftToLocalStorage()
    try {
      const businessRecord = buildBusinessRecord()
      await request.post('/records', {
        task_no: taskNo, business_record: businessRecord,
        report_summary: reportSummary.value || autoReport.value.summary || '',
        report_conclusion: reportConclusion.value || autoReport.value.conclusion || '',
        tester_self_check: testerSelfCheck.value, submit_for_review: false,
      })
    } catch { /* server may be unavailable, localStorage saves locally */ }
  }
})

// ── Periodic localStorage save (debounced, every 10s) ──
let _draftTimer = null
watch([formData, measurementRows, photoCheckpoints, templateFields, equipmentChecks, precheckSelected], () => {
  if (!canEdit.value) return
  if (_draftTimer) clearTimeout(_draftTimer)
  _draftTimer = setTimeout(() => saveDraftToLocalStorage(), 10000)
}, { deep: true })

// ── Helper for auto-save ──
function buildBusinessRecord() {
  // Sanitize rows: remove non-serializable values
  const cleanRows = calculatedRows.value.map(r => {
    const clean = {}
    for (const [k, v] of Object.entries(r)) {
      if (v instanceof File || v instanceof Blob) continue
      if (typeof v === 'number' && !isFinite(v)) clean[k] = null
      else clean[k] = v
    }
    return clean
  })
  // Sanitize form data
  const cleanForm = {}
  for (const [k, v] of Object.entries(formData)) {
    if (v instanceof File || v instanceof Blob) continue
    if (typeof v === 'number' && !isFinite(v)) cleanForm[k] = null
    else cleanForm[k] = v
  }
  return {
    _form: cleanForm, _rows: cleanRows,
    _photos: photoCheckpoints.value.filter(cp => cp.file || Object.keys(cp.samplePhotos || {}).length).map(cp => ({
      code: cp.code, label: cp.label,
      samples: Object.keys(cp.samplePhotos || {}).filter(sn => cp.samplePhotos[sn]?.file),
    })),
    _task_confirmations: { ...taskConfirmations },
    _equipment_checks: equipmentChecks.value.map(e => ({ ...e })),
    _prechecks: [...precheckSelected.value], _precheck_note: precheckNote.value,
    _precheck_all_items: [...precheckAllItems.value], _fixed_param_mode: fixedParamMode.value,
    _overall_status: overallStatus.value, _deviation: deviation.value, _retest: retest.value,
    _report_summary: reportSummary.value || '', _report_conclusion: reportConclusion.value || '',
    _tester_self_check: testerSelfCheck.value, _change_reason: changeReason.value,
    _template_fields: templateFields.value.map(f => ({ key: f.key, value: f.value || '' })),
    // Include standard block average for template fill (rough/HV)
    _standard_block_measured: standardBlockAvg.value?.value ?? null,
  }
}

// ── Ported from Streamlit business_record_engine.py ──
const POSITIVE_OPTIONS = [
  '委托检测', '完好', '正常', '符合', '合格', '是', '无', '清晰', '已确认', '已完成',
  '允许曝光', '清洁', '干燥', '无明显干扰', '已清洁', '平整', '无油污', '无氧化皮',
  '无影响压痕缺陷', '平稳', '测试面与压头轴线垂直', '有效', '牢固', '持续供给',
  '可用于本次试验', '未见明显差异', '产品标准', '通过', '不适用', '平行纹理', '否',
]

const OPTIONAL_PARAMETER_KEYS = new Set([
  'cutoff_filter', 'measurement_direction', 'zero_force', 'atmosphere',
  'pv_range', 'objective', 'magnification', 'calibration_scale',
  'observer_1', 'observer_2', 'observer_3', 'lamp_no', 'lamp_hours',
  'filter_no', 'filter_hours', 'background', 'sample_preparation',
  'procedure_summary', 'acceptance_criteria', 'test_conditions',
  'spindle_speed', 'metal_batch', 'em_source_file', 'parallel_block_no',
  ...[1, 2, 3, 4, 5].map(p => `monitor_${p}_note`),
  ...[1, 2, 3, 4, 5, 6].map(p => `color_monitor_${p}_note`),
])

const OPTIONAL_ROW_KEYS = new Set([
  'position', 'note', 'crack_position', 'thickness_relation',
  'estimated_thickness', 'defect', 'edge_condition', 'control_no',
  'shape', 'size', 'cover_method', 'cover_direction', 'measurement_item',
  'unit', 'calculated_value', 'retest_mean', 'failure_mode', 'retake',
  'cut_start', 'cut_end',
])

// File/index fields filled from internal trace index rather than manual entry.
const AUTO_ROW_KEYS = new Set([
  'file_no', 'curve_no', 'image_no', 'photo_no', 'image_path', 'data_path',
])

const PRECHECKS_BY_KIND = {
  rough: ['样品编号已核对', 'Z轴方向标识清晰', '试样表面清洁', '探针状态正常', '测量平台水平稳定'],
  mc_crack: ['样品编号已核对', '金属与陶瓷层外观正常', '金瓷结合试验夹具跨距已确认', '试样居中放置'],
  xray: ['样品表面清洁干燥', '检测区域无无关人员', '辐射警示装置正常', '防护装置有效', '操作人员已授权'],
  warp: ['打印及后处理已完成', '样品表面无污染', '样品无裂纹', '样品编号已核对', '切割前基准线清晰'],
  cte: ['样品编号已核对', '试样安装牢固', '测温系统状态正常', '升温程序已核对', '基线稳定'],
  shock: ['样品外观完好', '烘箱温度稳定', '冰水已准备', '计时器状态正常', '观察照度符合要求'],
  bend: ['样品编号已核对', '试样表面无影响试验的缺陷', '夹具平行度已确认', '支点距离已确认', '挠度计接触状态正常', '加载前力值已清零'],
  hv: ['样品编号已核对', '测试面平整清洁', '压头状态正常', '测量镜头清晰', '标准硬度块核查合格', '试样与压头轴线垂直'],
  thickness: ['样品编号已核对', '试样及标签信息一致', '测量系统状态正常', '测量点位已确认'],
  color: ['样品与对照编号已核对', '观察人员资格已确认', 'D65灯箱状态正常', '照射条件已确认', '观察背景已准备'],
  generic: ['样品编号已核对', '设备状态正常', '试验条件已确认'],
}

// ── SELECT_DEFAULTS (from Streamlit business_record_engine.py) ──
const SELECT_DEFAULTS = {
  standard_block_result: '合格', probe_condition: '正常', platform_level: '符合',
  surface_state: '原打印表面', parallel_check: '符合', orientation: '金属面朝上、陶瓷面朝下',
  radiation_safety: '允许曝光', baseline_before: '符合', coolant: '持续供给',
  baseline_after: '符合', sample_install: '牢固', sample_processing_state: '原始状态',
  crack: '无', chipping: '无', fracture: '无', fixture_parallel: '是',
  deflectometer_contact: '轻微接触', surface_condition: '平整清洁',
  perpendicularity: '符合', calibration_result: '合格', source_type: '氙灯',
  water_medium: '蒸馏水', background: 'N5中性灰', cover_secure: '是',
  image_valid: '有效', iqi_display: '清晰', sample_state: '完整',
  indent_quality: '有效', observer1: '未见明显差异', observer2: '未见明显差异',
  observer3: '未见明显差异', environment_interference: '无明显干扰',
  parameter_adjustment: '无调整', coolant_status: '是', remade: '否',
  initial_appearance: '无异常', sample_status: '完好', retake: '否',
  installation_direction: '正确', sample_secure: '是', run_status: '正常',
  auto_stop: '是', validity: '有效', judgement_result: '符合',
  surface_confirm: '符合', start_permission: '可以开始试验',
  indent_measurement_method: '切线测量', report_exported: '是',
  observer_qualification: '均已确认合格', lamp_box_ready: '已完成',
}

function initFormDefaults() {
  if (!config.value?.fields) return
  const kind = config.value?.kind || ''
  // ── Data isolation: remove keys from other experiment types ──
  const currentFieldKeys = new Set(config.value.fields.map(f => f.key).filter(Boolean))
  for (const key of Object.keys(formData)) {
    if (!currentFieldKeys.has(key)) delete formData[key]
  }
  for (const f of config.value.fields) {
    if (f.key && !(f.key in formData)) {
      if (f.key === 'detection_location') formData[f.key] = task.value?.detection_location || f.default || ''
      else if (f.key === 'start_time') formData[f.key] = task.value?.experiment_started_at || ''
      else if (f.key === 'end_time') formData[f.key] = task.value?.experiment_ended_at || ''
      else if (f.key === 'test_date' || f.type === 'date') formData[f.key] = new Date().toISOString().slice(0, 10)
      else if (f.type === 'select' && f.default == null) {
        formData[f.key] = SELECT_DEFAULTS[f.key] || (f.options?.length ? f.options[0] : '')
      } else if (f.type === 'multiselect') {
        // multiselect defaults: keep as array (from hardcoded) or parse comma-joined string (from DB)
        const def = f.default
        if (Array.isArray(def)) {
          formData[f.key] = [...def]
        } else if (typeof def === 'string' && def) {
          formData[f.key] = def.split(',').map(s => s.trim()).filter(Boolean)
        } else {
          formData[f.key] = []
        }
      } else formData[f.key] = f.default ?? ''
    }
  }
  // ── Remove obsolete keys (matches Streamlit initialize_business_record) ──
  const obsoleteKeys = {
    mc_crack: ['parallel_block_height_diff', 'max_gap', 'zero_force_before', 'zero_force',
               'loading_zero_confirmation', 'k_source', 'method_execution_confirmation'],
    thickness: ['calibration_scale', 'cleaning_time', 'software_version', 'image_path',
                'conditioning_start', 'conditioning_end', 'sample_preparation_actual',
                'method_execution_confirmation'],
  }[kind] || []
  for (const key of obsoleteKeys) {
    delete formData[key]
  }
  // ── Legacy temperature/humidity migration ──
  if (formData.temperature != null && formData.temperature !== '') {
    if (!formData.temperature_before) formData.temperature_before = formData.temperature
    if (!formData.temperature_after) formData.temperature_after = formData.temperature
  }
  if (formData.humidity != null && formData.humidity !== '') {
    if (!formData.humidity_before) formData.humidity_before = formData.humidity
    if (!formData.humidity_after) formData.humidity_after = formData.humidity
  }
  // ── Kind-specific parameter prefill (matches Streamlit initialize_business_record) ──
  const sg = sampleGroup.value || {}
  if (kind === 'hv') {
    if (!formData.sample_production_date) formData.sample_production_date = sg.product_no || ''
  }
  if (kind === 'mc_crack') {
    if (!formData.metal_name) formData.metal_name = sg.sample_name || ''
    if (!formData.metal_batch) formData.metal_batch = sg.product_no || ''
  }
  if (kind === 'thickness') {
    if (!formData.sample_production_date) formData.sample_production_date = sg.product_no || ''
    if (!formData.production_date) formData.production_date = sg.production_date || ''
  }
  // CTE: no start/end time displayed; just keep test_date
  if (task.value?.experiment_started_at) {
    formData.start_time = String(task.value.experiment_started_at).replace('T', ' ')
    if (!formData.test_date || formData.test_date === new Date().toISOString().slice(0, 10))
      formData.test_date = String(task.value.experiment_started_at).slice(0, 10)
  }
  if (task.value?.experiment_ended_at) {
    formData.end_time = String(task.value.experiment_ended_at).replace('T', ' ')
  }
}

function initMeasurementRows() {
  const cols = config.value?.columns || []
  if (!cols.length) return
  const sampleNos = task.value?.sample_nos
    ? task.value.sample_nos.split(',').map(s => s.trim()).filter(Boolean)
    : task.value?.sample_nos_list?.length ? task.value.sample_nos_list : [task.value?.group_no || taskNo]
  const kind = config.value?.kind || ''
  // match Streamlit initial_rows / normalize_rows
  const faces = (config.value?.row_expansion === 'faces' || kind === 'hv')
    ? (kind === 'hv' ? ['Z轴方向', 'X轴方向'] : ['面1', '面2'])
    : [null]
  const rows = []
  const perSample = {}
  for (const sno of sampleNos) {
    for (const face of faces) {
      const row = {}
      for (const c of cols) {
        if (c.column_key === 'sample_no') row[c.column_key] = String(sno).trim()
        else if (c.column_key === 'face') row[c.column_key] = face || ''
        else if (c.column_type === 'number' || c.column_type === 'calc') {
          // column defaults from experiment_engine.py _default_for_column
          const defaults = {
            rough_limit: 15.0, warp_limit: 0.5, bend_length: 25.0, bend_width: 2.0,
            bend_height: 2.0, bend_span: 20.0, bend_speed: 1.0,
            cte_t1: 25.0, cte_t2: 550.0,
          }
          row[c.column_key] = defaults[`${kind}_${c.column_key}`] ?? c.column_default ?? ''
        } else if (c.column_type?.startsWith('select:')) {
          const options = c.column_type.replace('select:', '').split('|')
          row[c.column_key] = options.length ? options[0] : ''
        } else row[c.column_key] = c.column_default ?? ''
      }
      // normalize_rows for HV: first face is Z, second is X/Y
      if (kind === 'hv') {
        const pos = perSample[sno] || 0
        if (pos === 0) row.face = 'Z轴方向'
        else if (row.face === 'Z轴方向') row.face = 'X轴方向'
        perSample[sno] = pos + 1
      }
      row._showNote = false
      rows.push(row)
    }
  }
  if (rows.length > 0) measurementRows.value = rows
}

function initPhotoCheckpoints() {
  const raw = config.value?.photo_checkpoints || []
  cameraHints.value = config.value?.camera_hints || {}
  photoCheckpoints.value = raw.map(cp => ({
    code: cp.code || cp.checkpoint_code,
    label: cp.label || cp.checkpoint_label,
    required: cp.required !== false,
    isSampleLevel: cp.is_sample_level || cp.isSampleLevel || false,
    checkpointGroup: cp.checkpoint_group || cp.checkpointGroup || '',
    file: null, previewUrl: '',
    // Per-sample photo slots for sample-level checkpoints
    samplePhotos: {},
  }))
}

function initEquipmentChecks() {
  const equip = config.value?.equipment || []
  equipmentChecks.value = equip.map(e => ({
    management_no: e.management_no || '', equipment_name: e.equipment_name || '',
    model: e.model || '', binding_role: e.binding_role || 'primary',
    measuring_range: e.measuring_range || '',
    manufacturer: e.manufacturer || '', serial_no: e.serial_no || '',
    calibration_time: e.calibration_time || '',
    equipment_class: e.equipment_class || '',
    responsible: e.responsible || '',
    status: '正常', note: '', required: e.required !== false,
  }))
}

function restorePhotos(photos) {
  for (const p of photos) {
    const cp = photoCheckpoints.value.find(c => c.code === (p.code || p.checkpoint_code))
    if (!cp) continue
    cp.file = p.file || null; cp.previewUrl = p.previewUrl || ''
    // Restore per-sample photos
    if (p.samplePhotos || p.samples) {
      if (!cp.samplePhotos) cp.samplePhotos = {}
      const samples = p.samplePhotos || {}
      for (const [sno, data] of Object.entries(samples)) {
        cp.samplePhotos[sno] = { file: data.file || null, previewUrl: data.previewUrl || '' }
      }
      // Handle legacy format with samples array
      if (p.samples && Array.isArray(p.samples)) {
        for (const sno of p.samples) {
          if (!cp.samplePhotos[sno]) cp.samplePhotos[sno] = { file: null, previewUrl: '' }
        }
      }
    }
  }
}

// ── Photo helpers ──

function removePhoto(cp, sampleNo) {
  if (sampleNo) {
    const s = cp.samplePhotos?.[sampleNo]
    if (s?.previewUrl && s.previewUrl.startsWith('blob:')) URL.revokeObjectURL(s.previewUrl)
    delete cp.samplePhotos[sampleNo]
  } else {
    if (cp.previewUrl && cp.previewUrl.startsWith('blob:')) URL.revokeObjectURL(cp.previewUrl)
    cp.file = null; cp.previewUrl = ''
  }
}

// Called by CameraCapture component when photo is taken
function onPhotoTaken(result) {
  const { file, previewUrl, sampleNo } = result
  const cp = activeCameraCp.value
  if (!cp) return
  if (sampleNo && cp.isSampleLevel) {
    if (!cp.samplePhotos) cp.samplePhotos = {}
    const old = cp.samplePhotos[sampleNo]
    if (old?.previewUrl && old.previewUrl.startsWith('blob:')) URL.revokeObjectURL(old.previewUrl)
    cp.samplePhotos[sampleNo] = { file, previewUrl }
  } else {
    if (cp.previewUrl && cp.previewUrl.startsWith('blob:')) URL.revokeObjectURL(cp.previewUrl)
    cp.file = file
    cp.previewUrl = previewUrl
  }
}

// ── Measurement ──
function addMeasurementRow() {
  const cols = config.value?.columns || []
  const row = {}
  for (const c of cols) row[c.column_key] = c.column_default ?? ''
  row._showNote = false
  measurementRows.value.push(row)
}
function removeMeasurementRow(index) { if (measurementRows.value.length > 1) measurementRows.value.splice(index, 1) }

async function loadTemplateManifest(experimentCode) {
  try {
    const { data } = await request.get(`/config/${experimentCode}/template-manifest`)
    const manifestFields = data.fields || []
    // Filter to fields that still need user input (have blanks or checkboxes)
    templateFields.value = manifestFields.map(f => ({
      ...f,
      value: templateFields.value.find(tf => tf.key === f.key)?.value || '',
      _showNote: false,
      _note: '',
    }))
    // Pre-fill from business data after loading
    prefillTemplateSupplement()
  } catch {
    templateFields.value = []
  }
}

// ── PARAM_ALIASES — maps template field labels to formData parameter keys ──
const PARAM_ALIASES = {
  '委托单位': 'client_name', '委托方': 'client_name', '委托方名称': 'client_name',
  '委托方地址': 'client_address', '委托单位地址': 'client_address',
  '生产单位': 'production_unit', '生产厂家': 'production_unit',
  '样品名称': 'sample_name', '试样名称': 'sample_name',
  '规格型号': 'model', '型号规格': 'model', '样品规格': 'model',
  '材料名称': 'material_name', '材料工艺': 'material_name',
  '产品编号': 'product_no', '批号': 'product_no', '样品批号': 'product_no',
  '样品编号': 'sample_nos', '试样编号': 'sample_nos', '实验室样品编号': 'sample_nos',
  '检测依据': 'standard', '检测方法': 'method_code',
  '检测地点': 'detection_location', '检测场所': 'detection_location',
  '接收日期': 'received_date', '收样日期': 'received_date',
  '检测日期': 'test_date', '实验日期': 'test_date', '试验日期': 'test_date',
  '检验日期': 'test_date', '测量日期': 'test_date',
  '检测人员': 'operator', '实验员': 'operator', '操作人': 'operator', '记录人': 'operator',
  '核验人员': 'reviewer', '复核人': 'reviewer',
  '报告编号': 'report_no',
  '样品数量': 'sample_quantity', '试样数量': 'sample_quantity',
  '温度': 'temperature_before', '环境温度': 'temperature_before',
  '湿度': 'humidity_before', '环境湿度': 'humidity_before',
  '实验前温度': 'temperature_before', '实验后温度': 'temperature_after',
  '实验前湿度': 'humidity_before', '实验后湿度': 'humidity_after',
  '试验温度': 'temperature_before', '试验湿度': 'humidity_before',
  '开始时间': 'start_time', '结束时间': 'end_time',
  '升温速率': 'heating_rate', '保温时间': 'hold_time',
  '载荷': 'load', '试验力': 'load',
  '硬度标尺': 'hardness_scale', '试验力值': 'test_force',
  '压头类型': 'indenter_type', '保载时间': 'dwell_time',
  '放大倍数': 'magnification', '物镜': 'objective',
  '评定长度': 'evaluation_length', '截止波长': 'cutoff_filter',
  '测量方向': 'measurement_direction',
  '材料牌号': 'metal_name', '金属牌号': 'metal_name', '金属批号': 'metal_batch',
  '陶瓷牌号': 'ceramic_name', '烤瓷程序': 'porcelain_program',
  'K值': 'k', '跨距': 'span',
  'X射线管电压': 'tube_voltage', '管电压': 'tube_voltage',
  'X射线管电流': 'tube_current', '管电流': 'tube_current',
  '曝光时间': 'exposure_time', '焦距': 'focal_distance',
  '源类型': 'source_type', '辐照度': 'irradiance',
  '水温': 'water_medium', '浸泡时间': 'exposure_duration',
  '观察者1': 'observer1', '观察者2': 'observer2', '观察者3': 'observer3',
  '标准试样': 'standard_sample', '标准号': 'standard_no',
  '压痕测量方式': 'indent_measurement_method',
  '设备名称': 'equipment_name', '设备型号': 'equipment_model',
  '管理编号': 'management_no', '设备编号': 'equipment_no',
  '校准证书': 'calibration_certificate', '校准有效期': 'calibration_due',
  '测量范围': 'measuring_range', '溯源机构': 'traceability_agency',
}

// ── ROW_ALIASES — maps template field labels to measurement row column keys ──
const ROW_ALIASES = {
  'Ra1': 'ra1', 'Ra2': 'ra2', 'Ra3': 'ra3', '平均值Ra': 'mean', '粗糙度平均值': 'mean',
  'dm1': 'dm1', 'dm2': 'dm2', 'dm3': 'dm3', 'dm平均': 'dm_mean',
  'Ffail': 'ffail', 'τb': 'tau', '结合强度': 'tau',
  'ROI1': 'roi1', 'ROI2': 'roi2', 'ROI3': 'roi3', 'ROI平均': 'roi_mean',
  'H1': 'h1', 'H2': 'h2', 'ΔH': 'delta',
  'T1': 't1', 'T2': 't2', 'ΔT': 'delta_t', 'α': 'alpha',
  '裂纹': 'crack', '崩瓷': 'chipping', '断裂': 'fracture',
  '0.2%弯曲应力': 'stress_02', 'Fmax': 'fmax',
  '压痕1': 'indent1', '压痕2': 'indent2', '压痕3': 'indent3', 'HV平均': 'mean',
  '厚度平均': 'mean', '偏差': 'deviation',
  '观察者1': 'observer1', '观察者2': 'observer2', '观察者3': 'observer3',
}

// ── Pre-fill template supplement from business data ──
function prefillTemplateSupplement() {
  if (!templateFields.value.length) return
  for (const tf of templateFields.value) {
    if (tf.value && tf.value.trim()) continue // Already has a value
    const label = tf.label || ''
    const rowLabel = tf.row_label || ''
    const colHeader = tf.col_header || ''

    // Step 1: Try PARAM_ALIASES for matching formData keys
    for (const [alias, key] of Object.entries(PARAM_ALIASES)) {
      if (label.includes(alias) || rowLabel.includes(alias) || colHeader.includes(alias)) {
        const val = formData[key]
        if (val != null && String(val).trim()) {
          tf.value = _composeCellText(tf.template_text || '', String(val))
          break
        }
      }
    }
    if (tf.value && tf.value.trim()) continue

    // Step 2: Try ROW_ALIASES for measurement data
    const rows = measurementRows.value
    if (rows.length) {
      for (const [alias, colKey] of Object.entries(ROW_ALIASES)) {
        if (label.includes(alias) || rowLabel.includes(alias) || colHeader.includes(alias)) {
          // Collect values from all rows
          const vals = rows.map(r => r[colKey]).filter(v => v != null && String(v).trim())
          if (vals.length) {
            const joined = [...new Set(vals)].join('；')
            tf.value = _composeCellText(tf.template_text || '', joined)
            break
          }
        }
      }
    }
    if (tf.value && tf.value.trim()) continue

    // Step 3: Equipment matching via row_label
    if (rowLabel) {
      const normLabel = rowLabel.replace(/\s+/g, '').toLowerCase()
      for (const eq of equipmentChecks.value) {
        const eqName = (eq.equipment_name || '').replace(/\s+/g, '').toLowerCase()
        if (eqName && normLabel.includes(eqName)) {
          if (label.includes('型号') || label.includes('规格')) tf.value = _composeCellText(tf.template_text || '', eq.model || '')
          else if (label.includes('管理编号') || label.includes('设备编号')) tf.value = _composeCellText(tf.template_text || '', eq.management_no || '')
          else if (label.includes('校准证书') || label.includes('证书编号')) tf.value = _composeCellText(tf.template_text || '', eq.calibration_certificate || '')
          else if (label.includes('有效期') || label.includes('校准日期')) tf.value = _composeCellText(tf.template_text || '', eq.calibration_due || '')
          else if (label.includes('测量范围')) tf.value = _composeCellText(tf.template_text || '', eq.measuring_range || '')
          else if (label.includes('溯源机构')) tf.value = _composeCellText(tf.template_text || '', eq.traceability_agency || '')
          else if (label.includes('状态') || label.includes('确认')) tf.value = eq.status === '正常' ? '☑正常 □异常' : '□正常 ☑异常'
          break
        }
      }
    }
  }
}

// ── Time ──
async function markTime(action) {
  try {
    const label = action === '开始' ? '开始实验' : '结束实验'
    await ElMessageBox.confirm(`确认「${label}」？`, '', { type: 'info', confirmButtonText: '确认', cancelButtonText: '取消' })
    acting.value = true
    await request.put(`/tasks/${taskNo}/time`, { action })
    ElMessage.success(`已标记实验${action}`)
    const { data } = await request.get(`/tasks/${taskNo}`)
    task.value = data.task
    if (action === '开始' && task.value.experiment_started_at) formData.start_time = task.value.experiment_started_at
    if (action === '结束' && task.value.experiment_ended_at) formData.end_time = task.value.experiment_ended_at
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally { acting.value = false }
}

// ── Sync & Check (matching Streamlit synchronize-and-check) ──
async function syncAndCheck() {
  syncing.value = true
  try {
    const businessRecord = buildBusinessRecord()
    await request.post('/records', {
      task_no: taskNo, business_record: businessRecord,
      report_summary: reportSummary.value || autoReport.value.summary || '',
      report_conclusion: reportConclusion.value || autoReport.value.conclusion || '',
      tester_self_check: testerSelfCheck.value, submit_for_review: false,
    })
    saveDraftToLocalStorage()
    validationReady.value = true
    ElMessage.success('记录已同步，检查通过后可提交复核')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '同步失败')
  } finally { syncing.value = false }
}

// ── Save / Submit ──

function collectMissingRequired() {
  // Collect all missing required fields (actual=true fields that are empty)
  const missingFields = []
  if (config.value?.fields) {
    for (const f of config.value.fields) {
      if (f.readonly) continue
      // Required = actual flag is true, or type is select/multiselect with actual=true
      const isActual = f.actual === true || f.is_actual === true
      if (!isActual) continue
      const val = formData[f.key]
      const isEmpty = val == null || val === '' || (Array.isArray(val) && val.length === 0)
      if (isEmpty) {
        const sectionLabel = f.section_title || ''
        missingFields.push(sectionLabel ? `[${sectionLabel}] ${f.label}` : f.label)
      }
    }
  }

  // Collect all missing required photo checkpoints
  const missingPhotos = []
  for (const cp of photoCheckpoints.value) {
    if (cp.required === false) continue
    // Sample-level checkpoints: only count missing per-sample photos
    if (cp.isSampleLevel) {
      for (const sno of sampleIds.value) {
        if (!cp.samplePhotos[sno]?.previewUrl) {
          missingPhotos.push(`${cp.label} — 样品${sno}`)
        }
      }
    } else {
      // Task-level checkpoints: one photo per checkpoint
      if (!cp.file && !cp.previewUrl) {
        missingPhotos.push(cp.label)
      }
    }
  }

  return { missingFields, missingPhotos }
}

async function handleSave(submitForReview) {
  if (!task.value) return

  if (submitForReview) {
    const { missingFields, missingPhotos } = collectMissingRequired()
    const totalMissing = missingFields.length + missingPhotos.length

    if (totalMissing > 0) {
      let msg = `<p style="margin-bottom:8px">以下 <b>${totalMissing}</b> 项必填内容未完成，无法提交复核：</p>`
      if (missingFields.length > 0) {
        msg += `<p style="margin:4px 0;color:#DC2626;font-weight:600">▸ 必填字段 (${missingFields.length})：</p>`
        msg += `<ul style="margin:4px 0;padding-left:20px;font-size:13px;max-height:200px;overflow-y:auto">`
        for (const f of missingFields) msg += `<li>${f}</li>`
        msg += `</ul>`
      }
      if (missingPhotos.length > 0) {
        msg += `<p style="margin:4px 0;color:#DC2626;font-weight:600">▸ 必拍照节点 (${missingPhotos.length})：</p>`
        msg += `<ul style="margin:4px 0;padding-left:20px;font-size:13px;max-height:200px;overflow-y:auto">`
        for (const p of missingPhotos) msg += `<li>${p}</li>`
        msg += `</ul>`
      }
      await ElMessageBox.alert(msg, '提交校验未通过', {
        dangerouslyUseHTMLString: true,
        type: 'error',
        confirmButtonText: '返回修改',
      })
      return
    }
  }

  const businessRecord = buildBusinessRecord()
  const finalSummary = reportSummary.value || autoReport.value.summary || ''
  const finalConclusion = reportConclusion.value || autoReport.value.conclusion || ''
  saving.value = true
  try {
    await request.post('/records', {
      task_no: taskNo, business_record: businessRecord,
      report_summary: finalSummary, report_conclusion: finalConclusion,
      tester_self_check: testerSelfCheck.value, submit_for_review: submitForReview,
    })
    ElMessage.success(submitForReview ? '已提交复核' : '草稿已保存')
    if (submitForReview) { clearLocalDraft(); router.push('/my-tasks') }
    else { saveDraftToLocalStorage() }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally { saving.value = false }
}

// ── Computed helpers ──
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
const readonlySections = computed(() => fieldSections.value.map(s => ({ ...s, fields: s.fields.filter(f => f.readonly) })).filter(s => s.fields.length))
const envParamSections = computed(() => fieldSections.value.map(s => ({ ...s, fields: s.fields.filter(f => !f.readonly) })).filter(s => s.fields.length))
const sampleIds = computed(() => measurementRows.value.map(r => r.sample_no).filter((v, i, a) => v && a.indexOf(v) === i))
const missingPhotos = computed(() => {
  let count = 0
  for (const cp of photoCheckpoints.value) {
    if (cp.required === false) continue
    // Sample-level checkpoints: only count per-sample photos
    if (cp.isSampleLevel) {
      for (const sno of sampleIds.value) {
        if (!cp.samplePhotos[sno]?.previewUrl) count++
      }
    } else {
      // Task-level checkpoints: one photo per checkpoint
      if (!cp.file && !cp.previewUrl) count++
    }
  }
  return count
})
const photoCompletionCount = computed(() => {
  let count = 0
  for (const cp of photoCheckpoints.value) {
    // Sample-level checkpoints: only count per-sample photos
    if (cp.isSampleLevel) {
      for (const sno of sampleIds.value) {
        if (cp.samplePhotos[sno]?.previewUrl) count++
      }
    } else {
      // Task-level checkpoints: one photo per checkpoint
      if (cp.file && cp.previewUrl) count++
    }
  }
  return count
})
const totalPhotoRequired = computed(() => {
  let total = 0
  for (const cp of photoCheckpoints.value) {
    if (cp.required === false) continue
    // Sample-level: required photos = number of samples
    if (cp.isSampleLevel) {
      total += sampleIds.value.length
    } else {
      // Task-level: one photo per checkpoint
      total++
    }
  }
  return total
})
const samplePhotoSlots = computed(() => {
  // Precompute for the per-sample photo sections
  const groups = {}
  for (const cp of sortedPhotoCheckpoints.value) {
    if (!cp.isSampleLevel) continue
    const g = cp.checkpointGroup || '其他'
    if (!groups[g]) groups[g] = { checkpoints: [], sampleIds: sampleIds.value }
    groups[g].checkpoints.push(cp)
  }
  return groups
})

// ── Sorted photo checkpoints: mandatory-incomplete first, then by group ──
const sortedPhotoCheckpoints = computed(() => {
  const items = [...photoCheckpoints.value]
  const rank = (cp) => {
    const isReq = cp.required !== false
    const isDone = !!(cp.file && cp.previewUrl)
    // Sort: mandatory-incomplete (0) → mandatory-complete (1) → optional-incomplete (2) → optional-complete (3)
    if (isReq && !isDone) return 0
    if (isReq && isDone) return 1
    if (!isReq && !isDone) return 2
    return 3
  }
  items.sort((a, b) => {
    const ra = rank(a), rb = rank(b)
    if (ra !== rb) return ra - rb
    // Within same rank, group by checkpoint_group
    return (a.checkpointGroup || '').localeCompare(b.checkpointGroup || '')
  })
  return items
})

// Group photo checkpoints by checkpoint_group for organized display
const photoCheckpointGroups = computed(() => {
  const groups = {}
  for (const cp of sortedPhotoCheckpoints.value) {
    const g = cp.checkpointGroup || '其他拍照节点'
    if (!groups[g]) groups[g] = []
    groups[g].push(cp)
  }
  return groups
})
const canEdit = computed(() => isTester.value && isAssignee.value && (task.value?.status === '检测中' || task.value?.status === '退回修改'))
const hasException = computed(() => overallStatus.value === '存在异常' || fixedParamMode.value === '存在偏离')

// ── Secondary edit / review return support ──
const recordVersion = ref(1)
const reviewReturn = ref(null)   // { reviewer, comment, correction_fields, reviewed_at }
const correctionFields = ref([])  // list of "①标签名｜字段名" strings
const isSecondaryEdit = computed(() => task.value?.status === '退回修改' || !!reviewReturn.value)
const returnedStepLabels = computed(() => {
  const map = { '①': new Set(), '②': new Set(), '③': new Set(), '④': new Set(), '⑤': new Set(), '⑥': new Set(), '⑦': new Set() }
  for (const item of correctionFields.value) {
    const marker = String(item).charAt(0)
    if (map[marker] && item.includes('｜')) {
      map[marker].add(item.split('｜', 2)[1])
    }
  }
  return map
})
const photoEditAllowed = computed(() => !isSecondaryEdit.value || returnedStepLabels.value['⑥'].size > 0)
const deviceFileEditAllowed = computed(() => !isSecondaryEdit.value || returnedStepLabels.value['⑥'].size > 0)

// Auto-focus on the tab with the first returned field
function focusReturnedStep() {
  if (!correctionFields.value.length) return
  const marker = String(correctionFields.value[0]).charAt(0)
  const stepMap = { '①': '1', '②': '2', '③': '3', '④': '4', '⑤': '5', '⑥': '6', '⑦': '7' }
  activeTab.value = stepMap[marker] || '1'
}

const ALWAYS_EDIT_PARAMETER_KEYS = new Set([
  'test_date', 'temperature_before', 'temperature_after', 'humidity_before', 'humidity_after',
])

const fixedFields = computed(() => {
  return visibleEditable.value.flatMap(s => s.fields).filter(f =>
    f.default != null && f.default !== '' && !f.readonly && !ALWAYS_EDIT_PARAMETER_KEYS.has(f.key)
  )
})

const editableFields = computed(() => {
  return visibleEditable.value.flatMap(s => s.fields).filter(f => !fixedFields.value.includes(f))
})

const ENV_KEYS = ['test_date', 'temperature_before', 'temperature_after', 'humidity_before', 'humidity_after']
const PROCESS_PREFIXES = ['iqi_gray_', 'monitor_', 'color_monitor_']

const envFields = computed(() => editableFields.value.filter(f => ENV_KEYS.includes(f.key)))
const processFields = computed(() => editableFields.value.filter(f => PROCESS_PREFIXES.some(p => f.key.startsWith(p))))
const coreManualFields = computed(() => editableFields.value.filter(f => !ENV_KEYS.includes(f.key) && !PROCESS_PREFIXES.some(p => f.key.startsWith(p))))

function getFieldType(f) { const t = f.type || 'text'; return ['select','multiselect','number','date','datetime','time','textarea'].includes(t) ? t : 'text' }
const TIME_KEYS = new Set(['start_time', 'end_time'])

function captureTime(key) {
  const now = new Date()
  formData[key] = now.getFullYear() + '-'
    + String(now.getMonth() + 1).padStart(2, '0') + '-'
    + String(now.getDate()).padStart(2, '0') + ' '
    + String(now.getHours()).padStart(2, '0') + ':'
    + String(now.getMinutes()).padStart(2, '0') + ':'
    + String(now.getSeconds()).padStart(2, '0')
  ElMessage.success(`已记录${key === 'start_time' ? '开始' : '结束'}时间：${formData[key]}`)
}
function getFieldOptions(f) { if (f.options?.length) return f.options; if (f.type?.startsWith('select:')) return f.type.replace('select:', '').split('|'); if (f.type?.startsWith('multiselect:')) return f.type.replace('multiselect:', '').split('|'); return [] }
function isFieldRequired(f) { return f.is_required || f.required || f.is_actual || false }
function getColumnType(c) { if (c.column_type === 'number') return 'number'; if (c.column_type?.startsWith('select:') || c.column_type === 'select') return 'select'; return 'text' }
function getColumnOptions(c) {
  if (c.column_type?.startsWith('select:')) return c.column_type.replace('select:', '').split('|')
  // Fallback: DB-served columns may store pipe-separated options in column_default
  if (c.column_type === 'select' && c.column_default && String(c.column_default).includes('|')) return String(c.column_default).split('|')
  return []
}

// ── HIDDEN_PARAM_KEYS (from Streamlit business_record_engine.py) ──
const HIDDEN_PARAM_KEYS = new Set([
  'detection_location', 'software', 'data_path', 'start_time', 'end_time',
  'equipment_name', 'equipment_model', 'equipment_no',
  'calibration_certificate', 'calibration_due', 'equipment_status',
  'image_path', 'image_before_path', 'image_after_path', 'curve_path',
])

// Filter field sections to exclude hidden keys
const visibleFieldSections = computed(() => {
  return fieldSections.value.map(s => ({
    ...s,
    fields: s.fields.filter(f => !HIDDEN_PARAM_KEYS.has(f.key)),
  })).filter(s => s.fields.length)
})

// Override readonlySections and envParamSections to use visible fields
const visibleReadonly = computed(() => visibleFieldSections.value.map(s => ({ ...s, fields: s.fields.filter(f => f.readonly) })).filter(s => s.fields.length))
const visibleEditable = computed(() => visibleFieldSections.value.map(s => ({ ...s, fields: s.fields.filter(f => !f.readonly) })).filter(s => s.fields.length))

// ── Calculation Engine (ported from experiment_engine.py) ──
function _num(val, def = 0) { if (val === null || val === '') return def; const n = Number(val); return isNaN(n) ? def : n }
function _n(val) { if (val === null || val === '') return null; const n = Number(val); return isNaN(n) ? null : n }
function _finite(n) { return n != null && isFinite(n) ? n : null }
function _safeDiv(a, b) { if (!b) return null; const r = a / b; return isFinite(r) ? r : null }

const CALC_LABELS = {
  rough: ['平均Ra', 'μm', 'mean'],
  mc_crack: ['结合强度', 'MPa', 'tau'],
  xray: ['ROI平均灰度', '', 'roi_mean'],
  warp: ['翘曲变化量ΔH', 'mm', 'delta'],
  cte: ['线膨胀系数α', '×10⁻⁶/K', 'alpha'],
  bend: ['0.2%规定非比例弯曲应力', 'MPa', 'stress_02'],
  hv: ['平均维氏硬度', 'HV10', 'mean'],
  thickness: ['平均厚度', 'mm', 'mean'],
  color: ['目视比较结果', '', 'overall'],
  shock: ['耐急冷急热结果', '', 'conclusion'],
}

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
  return calculateRows(kind, measurementRows.value)
})

function resultSummary(kind, rows) {
  const conclusions = rows.map(r => r.conclusion).filter(Boolean)
  let overall = ''
  if (conclusions.length && conclusions.every(c => ['符合', '合格'].includes(c))) overall = '符合'
  else if (conclusions.some(c => ['不符合', '不合格'].includes(c))) overall = '不符合'
  else if (conclusions.length) overall = [...new Set(conclusions)].join('；')
  else overall = '仅描述结果'

  const [title, unit, valueKey] = CALC_LABELS[kind] || ['检验结果', '', 'calculated_value']
  const parts = []
  for (const row of rows) {
    let sid = row.sample_no || ''
    if (kind === 'hv' && row.face) sid = `${sid}-${row.face}`
    const val = row[valueKey]
    if (val != null && val !== '') {
      let disp = typeof val === 'number' ? String(val).replace(/(\.[0-9]*[1-9])0+$/, '$1').replace(/\.$/, '') : String(val)
      parts.push(`${sid}：${title}${disp}${unit}`)
    }
  }
  return { summary: parts.length ? parts.join('；') : '尚未形成有效检验结果', conclusion: overall }
}

const autoReport = computed(() => {
  const kind = config.value?.kind || task.value?.experiment_code || ''
  return resultSummary(kind, calculatedRows.value)
})

// ── validate_business_record (ported from Streamlit business_record_engine.py) ──
function validate_business_record() {
  const issues = []
  const confirmations = taskConfirmations || {}
  if (!confirmations.sample_received || !confirmations.number_match || !confirmations.sample_condition) {
    issues.push('任务与样品确认尚未全部完成')
  }
  const expected = new Set(precheckAllItems.value)
  const actual = new Set(precheckSelected.value)
  if ([...expected].some(x => !actual.has(x)) && !precheckNote.value.trim()) {
    issues.push('存在未通过的实验前检查项，但未填写说明')
  }
  const kind = config.value?.kind || ''
  if (kind !== 'cte') {
    if (!String(formData.start_time || '').trim()) issues.push('尚未通过时间轴记录实验开始时间')
    if (!String(formData.end_time || '').trim()) issues.push('尚未通过时间轴记录实验结束时间')
  }
  if (kind === 'cte') {
    const heatingRate = _num(formData.heating_rate)
    if (!(heatingRate >= 4.0 && heatingRate <= 6.0)) issues.push('升温速率应在5±1 ℃/min范围内')
  }
  // Check editable fields that are not optional
  const allEditable = editableFields.value
  for (const field of allEditable) {
    if (OPTIONAL_PARAMETER_KEYS.has(field.key)) continue
    if (formData[field.key] == null || formData[field.key] === '') {
      issues.push(`未填写：${field.label}`)
    }
  }
  // Check equipment
  for (const eq of equipmentChecks.value) {
    if (eq.required && eq.status !== '正常' && !(eq.note || '').trim()) {
      issues.push(`必需设备 ${eq.management_no} 状态异常但未填写说明`)
    }
  }
  // Check row fields
  const rows = measurementRows.value
  const allCols = visibleColumns.value
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i]
    const sid = row.sample_no || `第${i + 1}条`
    for (const col of allCols) {
      if (col.column_type === 'calc' || OPTIONAL_ROW_KEYS.has(col.column_key) || col.column_key === 'note') continue
      if (row[col.column_key] == null || row[col.column_key] === '') {
        issues.push(`${sid} 未填写：${col.column_label}`)
      }
    }
  }
  if (overallStatus.value === '存在异常' && !deviation.value.trim()) {
    issues.push('选择了存在异常，但未填写异常、偏离及处理说明')
  }
  if (!autoReport.value.summary || autoReport.value.summary === '尚未形成有效检验结果') {
    issues.push('检验报告用结果摘要尚未形成')
  }
  return issues
}

function business_completion_summary() {
  const issues = validate_business_record()
  const sections = {
    '任务与样品确认': taskConfirmations.sample_received && taskConfirmations.number_match && taskConfirmations.sample_condition,
    '设备与实验前确认': !issues.some(x => x.includes('设备') || x.includes('实验前')),
    '环境与实验参数': !issues.some(x => x.startsWith('未填写') && (x.includes('温度') || x.includes('湿度') || x.includes('时间') || x.includes('参数'))),
    '原始测量数据': !issues.some(x => x.includes('未填写：') && !x.includes('参数')),
    '异常与结果摘要': !issues.some(x => x.includes('异常') || x.includes('结果摘要')),
  }
  return { issues, sections, complete: !issues.length }
}

// Auto-calc standard block for roughness/HV
const standardBlockAvg = computed(() => {
  const kind = config.value?.kind || ''
  if (kind === 'rough') {
    const vs = [1, 2, 3].map(i => _n(formData[`repeat_check_${i}`]))
    if (vs.every(v => v !== null)) return { label: '标准样板实测平均值/μm（自动计算）', value: +((vs[0] + vs[1] + vs[2]) / 3).toFixed(3) }
  }
  if (kind === 'hv') {
    const vs = [1, 2, 3].map(i => _n(formData[`standard_block_reading_${i}`]))
    if (vs.every(v => v !== null)) return { label: '标准硬度块实测平均值/HV（自动计算）', value: +((vs[0] + vs[1] + vs[2]) / 3).toFixed(1) }
  }
  return null
})

// Per-sample groups for measurement data display
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

// Columns with only visible (non-hidden) fields
const visibleColumns = computed(() => {
  const cols = config.value?.columns || []
  return cols.filter(c => c.column_key !== 'sample_no' && !AUTO_ROW_KEYS.has(c.column_key))
})

const calcColumns = computed(() => visibleColumns.value.filter(c => c.column_type === 'calc'))
const inputColumns = computed(() => visibleColumns.value.filter(c => c.column_type !== 'calc'))

const ABNORMAL_VALUES = new Set(['异常','有','无效','不符合','不合格','需复检','超出适用范围','无法判定'])
function isRowAbnormal(row) {
  return Object.values(row).some(v => ABNORMAL_VALUES.has(String(v ?? '')))
}

const templateFieldsGrouped = computed(() => {
  const groups = {}
  for (const f of templateFields.value) {
    const sec = f.section || '其他补充字段'
    if (!groups[sec]) groups[sec] = []
    groups[sec].push(f)
  }
  return groups
})

// ── Template supplement checkbox helpers (ported from Streamlit render_template_supplement) ──
const BLANK_RE = /_{2,}|＿{2,}|…{2,}/
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

function _normalBatchChoices(label, choices) {
  const specificTokens = ['类别', '来源', '依据', '方向', '方法', '类型', '材质', '颜色', '制样', '后处理', '成型', '编号', '名称', '规格', '型号']
  if (specificTokens.some(t => label.includes(t))) return []
  const negativeTokens = ['不符合', '不合格', '异常', '不可', '暂停', '未完成', '无效', '破损', '裂纹', '崩瓷', '污染', '锈蚀', '磨损', '偏离', '失败']
  const positive = choices.filter(c => !negativeTokens.some(t => c.includes(t)))
  if (!positive.length) return []
  // Several independent observations can all be true
  if (choices.length > 2 && positive.length === choices.length) return positive
  const preferred = ['符合', '合格', '正常', '完好', '有效', '通过', '已完成', '已确认', '清晰', '牢固', '平整', '清洁', '无', '是']
  if (label.includes('附件') || label.includes('照片') || label.includes('图像') || label.includes('文件') || label.includes('曲线')) {
    const extraPref = ['有', '已归档', '已保存', '已导出', '是', '有效']
    for (const token of extraPref) {
      const match = positive.find(c => c.includes(token))
      if (match) return [match]
    }
  }
  for (const token of preferred) {
    const match = positive.find(c => c.includes(token))
    if (match) return [match]
  }
  return positive.length === 1 ? [positive[0]] : []
}

function _filledCheckboxText(original, selected, note = '') {
  let value = (original || '').replace(/☐/g, '□').replace(/☑/g, '□')
  for (const choice of selected) {
    const escaped = choice.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    value = value.replace(new RegExp('□\\s*' + escaped), m => '☑' + m.substring(1))
  }
  if (note) {
    value = value.replace(new RegExp(BLANK_RE.source), note)
  } else {
    value = value.replace(new RegExp(BLANK_RE.source, 'g'), '/')
  }
  return value
}

function batchConfirmSection(sectionName) {
  const sectionFields = templateFieldsGrouped.value[sectionName] || []
  const batchValues = {}
  for (const field of sectionFields) {
    const original = field.template_text || ''
    const choices = _checkboxChoices(original)
    if (!choices.length) continue
    const selected = _normalBatchChoices(field.label || '', choices)
    if (selected.length) {
      batchValues[field.key] = _filledCheckboxText(original, selected)
    }
  }
  if (Object.keys(batchValues).length) {
    for (const key of Object.keys(batchValues)) {
      const tf = templateFields.value.find(f => f.key === key)
      if (tf) tf.value = batchValues[key]
    }
    ElMessage.success(`已一键确认本区正常项（${Object.keys(batchValues).length}项）`)
  }
}

// ── Template supplement: compose cell text (fills blanks) ──
function _composeCellText(original, fillValue) {
  if (!fillValue && fillValue !== 0) return original || ''
  const val = String(fillValue)
  if (new RegExp(BLANK_RE.source).test(original || '')) {
    return (original || '').replace(new RegExp(BLANK_RE.source), val)
  }
  return val || original || ''
}

// ── Template supplement: determine if checkbox field is multi-choice ──
function _checkboxFieldMeta(label, choices) {
  if (!choices.length) return { multi: false }
  const exclusiveTokens = ['类别', '来源', '依据', '状态', '结果', '结论', '方向', '方法', '是否', '判定']
  // Single-choice fields: categories, results, yes/no decisions
  if (exclusiveTokens.some(t => (label || '').includes(t))) return { multi: false }
  // Multi-choice fields: independent positive confirmations (clean+flat+no-rust all at once)
  const negativeTokens = ['不符合', '不合格', '异常', '不可', '暂停', '未完成', '无效', '破损', '裂纹', '崩瓷', '污染', '锈蚀', '磨损', '偏离', '失败']
  const hasNegative = choices.some(c => negativeTokens.some(t => c.includes(t)))
  if (!hasNegative && choices.length > 2) return { multi: true }
  return { multi: false }
}

// ── Template supplement: parse checkbox selections from current value ──
function _parseCheckboxValue(original, current) {
  const selected = _selectedCheckboxChoices(original, current || '')
  const hasBlank = BLANK_RE.test(current || '')
  // Extract free-text note (the portion in blanks)
  const match = (current || '').match(new RegExp(BLANK_RE.source))
  const note = match ? current.replace(/.*?[_＿…]{2,}.*?/, '').replace(/[_＿…]+/g, '').trim() : ''
  return { selected, note: hasBlank ? (note || '') : '' }
}

// ── Template supplement: determine if a selected value needs a note ──
function _choiceNeedsNote(selected) {
  const triggerTokens = ['其他', '异常', '不符合', '不合格', '有', '调整', '维修', '无效']
  return selected.some(c => triggerTokens.some(t => c.includes(t)))
}
</script>

<template>
  <div class="experiment-run" v-loading="loading">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1>实验执行 <span class="task-no">{{ task?.task_no }}</span></h1>
        <div class="task-meta">
          <span>{{ task?.experiment }}</span>
          <el-divider direction="vertical" />
          <span>{{ task?.method_code }}</span>
          <el-divider direction="vertical" />
          <span>{{ task?.detection_location }}</span>
        </div>
      </div>
      <div class="header-actions">
        <el-button @click="router.back()">返回</el-button>
        <template v-if="config?.kind !== 'cte'">
          <el-button v-if="isTester && isAssignee && task?.status==='待接收'" type="primary" :icon="VideoPlay" :loading="acting" @click="markTime('开始')">开始实验</el-button>
          <el-button v-if="isTester && isAssignee && task?.status==='检测中'" type="danger" :icon="VideoPause" :loading="acting" @click="markTime('结束')">结束实验</el-button>
        </template>
        <span v-if="config?.kind==='cte'" style="font-size:12px;color:#94A3B8">CTE实验不显示开始/结束时间操作，系统仍在后台保留任务进入时间等审计记录。</span>
      </div>
    </div>

    <!-- Status bar -->
    <div class="status-bar" v-if="task">
      <el-tag :type="task.status==='检测中'?'warning':task.status==='已完成'?'success':task.status==='退回修改'?'danger':'info'" size="small">{{ task.status }}</el-tag>
      <span v-if="recordVersion>1" style="color:#DC2626;font-weight:500">V{{ recordVersion }}</span>
      <span v-if="config" class="config-source">配置: {{ config._source==='database'?`v${config.version}`:'默认模板' }}｜SOP: {{ config.sop_version || 'A/0' }}｜模板: {{ config.record_template_file || config.record_template_version || 'A/0' }}</span>
      <span v-if="task.experiment_started_at" class="time-info">开始: {{ task.experiment_started_at }}</span>
      <span v-if="task.experiment_ended_at" class="time-info">结束: {{ task.experiment_ended_at }}</span>
    </div>

    <!-- Review return / correction warning -->
    <el-alert v-if="isSecondaryEdit" :title="task?.status === '退回修改' ? '⚠️ 此实验已被复核员退回，请根据修改意见修正后重新提交' : '⚠️ 此实验为二次编辑：上一提交版本已由复核员退回'" type="error" :closable="false" show-icon style="margin-bottom:16px">
      <template v-if="reviewReturn">
        <div style="font-size:13px;line-height:1.6">
          <div>复核员：{{ reviewReturn.reviewer_name || reviewReturn.reviewer || '-' }}｜退回时间：{{ reviewReturn.reviewed_at || '-' }}</div>
          <div>复核意见：{{ reviewReturn.comment || '无' }}</div>
        </div>
        <div v-if="correctionFields.length" style="margin-top:8px">
          <strong>复核员指定修改字段：</strong>
          <ul style="margin:4px 0;padding-left:20px;font-size:13px">
            <li v-for="item in correctionFields" :key="item">{{ item }}</li>
          </ul>
        </div>
      </template>
      <div style="margin-top:8px;font-size:13px;color:#B91C1C">上一版本已填写的实验数据、设备信息、照片原件和结论已完整保留在当前草稿中，请按复核意见修改后重新提交。</div>
    </el-alert>

    <!-- No config -->
    <el-result v-if="!loading && task && !config" icon="warning" title="暂无实验配置" sub-title="该实验暂无现行配置版本，请联系管理员在「实验配置管理」中创建配置。" />


    <!-- 7-TAB WORKFLOW -->
    <div v-if="task && config" class="workflow-area">
      <el-tabs v-model="activeTab" type="card">

        <!-- ═══════════════ ① 任务确认 ═══════════════ -->
        <el-tab-pane label="①任务确认" name="1">
          <div class="tab-inner">
            <el-card shadow="never" class="mb-card">
              <template #header><strong>任务信息</strong></template>
              <el-descriptions :column="3" border size="small">
                <el-descriptions-item label="委托单位">{{ commission?.client_name || '-' }}</el-descriptions-item>
                <el-descriptions-item label="生产单位">{{ commission?.production_org_name || '-' }}</el-descriptions-item>
                <el-descriptions-item label="样品名称">{{ sampleGroup?.sample_name || '-' }}</el-descriptions-item>
                <el-descriptions-item label="规格型号">{{ sampleGroup?.model || '-' }}</el-descriptions-item>
                <el-descriptions-item label="材料名称">{{ task.material_name || sampleGroup?.material_name || '-' }}</el-descriptions-item>
                <el-descriptions-item label="实体样品编号">{{ sampleIds.length ? sampleIds.join('、') : '-' }}</el-descriptions-item>
                <el-descriptions-item label="检测方法">{{ task.method_code || '-' }}</el-descriptions-item>
                <el-descriptions-item label="检测依据">{{ task.standard || '-' }}</el-descriptions-item>
                <el-descriptions-item label="检测地点">{{ task.detection_location || '-' }}</el-descriptions-item>
              </el-descriptions>
              <div style="margin-top:8px;font-size:12px;color:#94A3B8">以上信息来自委托、入库、任务和配置快照，实验员不可修改。</div>
            </el-card>

            <el-card shadow="never" class="mb-card">
              <template #header><strong>样品接收确认</strong> <span style="font-size:12px;color:#94A3B8">正常情况下保持默认选中；发现问题时取消对应项，并在异常说明中记录。</span></template>
              <div style="display:flex;gap:32px">
                <el-checkbox v-model="taskConfirmations.sample_received" :disabled="!canEdit">样品已收到</el-checkbox>
                <el-checkbox v-model="taskConfirmations.number_match" :disabled="!canEdit">样品编号一致</el-checkbox>
                <el-checkbox v-model="taskConfirmations.sample_condition" :disabled="!canEdit">样品状态正常</el-checkbox>
              </div>
            </el-card>

            <div class="step-nav"><el-button type="primary" @click="activeTab='2'">下一步：设备与实验前检查</el-button></div>
          </div>
        </el-tab-pane>

        <!-- ═══════════════ ② 设备与实验前检查 ═══════════════ -->
        <el-tab-pane label="②设备与实验前检查" name="2">
          <div class="tab-inner">
            <!-- Equipment -->
            <el-card shadow="never" class="mb-card">
              <template #header>
                <div style="display:flex;justify-content:space-between;align-items:center">
                  <strong>设备确认</strong>
                  <span style="font-size:12px;color:#94A3B8">设备由任务配置自动带入，也可手动添加辅助设备。正常情况下仅确认状态；选择异常后才填写说明。</span>
                </div>
              </template>
              <el-empty v-if="!equipmentChecks.length" description="该实验配置尚未绑定设备。" />
              <div v-else class="equip-grid">
                <el-card v-for="(eq,i) in equipmentChecks" :key="i" shadow="never" :class="{'equip-err':eq.status==='异常'}">
                  <div style="display:flex;gap:16px">
                    <div style="flex:1.3">
                      <div style="font-weight:600;display:flex;align-items:center;gap:6px">
                        {{ eq.equipment_name }}
                        <el-tag v-if="eq.required!==false" size="small" type="warning">必需</el-tag>
                        <el-tag v-else size="small" type="info">手动添加</el-tag>
                      </div>
                      <div style="color:#64748B;font-size:13px">{{ eq.model }}</div>
                      <div style="font-size:12px;color:#94A3B8">管理编号：<code>{{ eq.management_no }}</code></div>
                    </div>
                    <div style="flex:1;font-size:12px;color:#64748B;line-height:1.6">
                      <div>角色：{{ eq.binding_role==='primary'||eq.binding_role==='主设备'||eq.binding_role==='主要设备'?'主设备':'辅助' }}</div>
                      <div>测量范围：{{ eq.measuring_range || '-' }}</div>
                      <div>厂家/型号：{{ [eq.manufacturer, eq.model].filter(Boolean).join(' / ') || '-' }}</div>
                      <div>出厂编号：{{ eq.serial_no || '-' }}</div>
                      <div>校准日期：{{ eq.calibration_time || '未填写' }}</div>
                      <div>负责人：{{ eq.responsible || '-' }}</div>
                    </div>
                    <div style="flex:1">
                      <div style="font-size:13px;color:#475569;margin-bottom:4px">使用前状态：</div>
                      <el-radio-group v-model="eq.status" :disabled="!canEdit" size="small">
                        <el-radio value="正常">正常</el-radio>
                        <el-radio value="异常">异常</el-radio>
                      </el-radio-group>
                      <div v-if="eq.status==='异常'" style="margin-top:6px">
                        <el-input v-model="eq.note" type="textarea" :rows="2" placeholder="异常说明及处理" size="small" :disabled="!canEdit" />
                      </div>
                      <div v-if="eq.required===false && canEdit" style="margin-top:10px">
                        <el-button size="small" type="danger" plain @click="removeEquipment(i)">✕ 移除此设备</el-button>
                      </div>
                    </div>
                  </div>
                </el-card>
              </div>
              <!-- Add equipment -->
              <div v-if="canEdit" style="margin-top:12px">
                <template v-if="!addingEquipment">
                  <el-button size="small" @click="addingEquipment=true; loadAvailableEquipment()"><el-icon style="margin-right:3px"><Plus /></el-icon>添加辅助设备</el-button>
                </template>
                <div v-else style="display:flex;gap:8px;align-items:center">
                  <el-select v-model="addEquipmentSelection" filterable placeholder="搜索设备名称或管理编号" :loading="loadingEquipment" style="flex:1;max-width:480px" @change="addEquipment">
                    <el-option v-for="eq in availableEquipment" :key="eq.management_no" :label="`${eq.equipment_name}｜${eq.model||'-'}｜${eq.management_no}`" :value="eq.management_no">
                      <div style="font-size:13px">{{ eq.equipment_name }} <span style="color:#94A3B8;font-size:11px">{{ eq.model }}</span></div>
                      <div style="font-size:11px;color:#64748B">{{ eq.management_no }}</div>
                    </el-option>
                  </el-select>
                  <el-button size="small" @click="addingEquipment=false">取消</el-button>
                </div>
              </div>
            </el-card>

            <!-- Prechecks -->
            <el-card shadow="never" class="mb-card">
              <template #header><strong>实验前检查</strong></template>
              <el-empty v-if="!precheckAllItems.length" description="本实验无预检查项" />
              <div v-else>
                <div style="margin-bottom:8px;font-size:13px;color:#475569">已确认项目</div>
                <el-checkbox-group v-model="precheckSelected" :disabled="!canEdit" style="display:flex;flex-direction:column;gap:6px">
                  <el-checkbox v-for="(item,i) in precheckAllItems" :key="i" :value="item">{{ item }}</el-checkbox>
                </el-checkbox-group>
                <div v-if="precheckSelected.length === precheckAllItems.length" style="color:#22C55E;margin-top:8px;font-size:13px">实验前检查默认全部正常。</div>
                <div v-else style="margin-top:12px">
                  <el-input v-model="precheckNote" type="textarea" :rows="2" placeholder="未通过项目说明及处理" :disabled="!canEdit" />
                </div>
              </div>
            </el-card>

            <div class="step-nav">
              <el-button @click="activeTab='1'">上一步</el-button>
              <el-button type="primary" @click="activeTab='3'">下一步：环境与参数</el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- ═══════════════ ③ 环境与参数 ═══════════════ -->
        <el-tab-pane label="③环境与参数" name="3">
          <div class="tab-inner">
            <!-- Readonly sections -->
            <el-card v-for="(sec,si) in visibleReadonly" :key="'ri'+si" shadow="never" class="mb-card-sm">
              <template #header><strong>{{ sec.title }}</strong></template>
              <el-descriptions :column="3" border size="small">
                <el-descriptions-item v-for="f in sec.fields" :key="f.key" :label="f.label">{{ formData[f.key] || '-' }}</el-descriptions-item>
              </el-descriptions>
            </el-card>

            <!-- Environment fields (test_date, temperature, humidity) -->
            <el-card v-if="envFields.length" shadow="never" class="mb-card-sm">
              <template #header><strong>环境与实验参数</strong></template>
              <el-form label-width="160px" label-position="left" size="small">
                <el-row :gutter="16">
                  <el-col v-for="f in envFields" :key="f.key" :span="8">
                    <el-form-item :label="f.label" :required="isFieldRequired(f)">
                      <!-- number -->
                      <el-input-number v-if="getFieldType(f)==='number'" v-model="formData[f.key]" :disabled="!canEdit" style="width:100%" controls-position="right" />
                      <!-- date -->
                      <el-date-picker v-else-if="getFieldType(f)==='date'" v-model="formData[f.key]" type="date" value-format="YYYY-MM-DD" :disabled="!canEdit" style="width:100%" />
                      <!-- datetime -->
                      <template v-else-if="TIME_KEYS.has(f.key)">
                        <div style="display:flex;align-items:center;gap:8px">
                          <el-input :model-value="formData[f.key] || '未记录'" readonly style="flex:1" />
                          <el-button size="small" type="primary" :disabled="!canEdit" @click="captureTime(f.key)">记录</el-button>
                        </div>
                      </template>
                      <el-date-picker v-else-if="getFieldType(f)==='datetime'" v-model="formData[f.key]" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" :disabled="!canEdit" style="width:100%" />
                      <!-- select -->
                      <el-select v-else-if="getFieldType(f)==='select'" v-model="formData[f.key]" :disabled="!canEdit" style="width:100%" clearable>
                        <el-option v-for="opt in getFieldOptions(f)" :key="opt" :label="opt" :value="opt" />
                      </el-select>
                      <!-- multiselect -->
                      <el-select v-else-if="getFieldType(f)==='multiselect'" v-model="formData[f.key]" :disabled="!canEdit" style="width:100%" multiple collapse-tags>
                        <el-option v-for="opt in getFieldOptions(f)" :key="opt" :label="opt" :value="opt" />
                      </el-select>
                      <!-- textarea -->
                      <el-input v-else-if="getFieldType(f)==='textarea'" v-model="formData[f.key]" :disabled="!canEdit" type="textarea" :rows="2" />
                      <!-- text (default) -->
                      <el-input v-else v-model="formData[f.key]" :disabled="!canEdit" />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
            </el-card>

            <!-- Fixed parameters -->
            <el-card v-if="fixedFields.length" shadow="never" class="mb-card-sm">
              <template #header><strong>固定参数</strong></template>
              <div v-if="fixedParamMode !== '存在偏离'">
                <el-descriptions :column="3" border size="small">
                  <el-descriptions-item v-for="f in fixedFields" :key="f.key" :label="f.label">{{ formData[f.key] || f.default || '-' }}</el-descriptions-item>
                </el-descriptions>
              </div>
              <el-form v-else label-width="160px" label-position="left" size="small">
                <el-row :gutter="16">
                  <el-col v-for="f in fixedFields" :key="f.key" :span="8">
                    <el-form-item :label="f.label" :required="isFieldRequired(f)">
                      <el-input v-if="getFieldType(f)==='text'" v-model="formData[f.key]" :disabled="!canEdit" />
                      <el-input-number v-else-if="getFieldType(f)==='number'" v-model="formData[f.key]" :disabled="!canEdit" style="width:100%" controls-position="right" />
                      <el-date-picker v-else-if="getFieldType(f)==='date'" v-model="formData[f.key]" type="date" value-format="YYYY-MM-DD" :disabled="!canEdit" style="width:100%" />
                      <template v-else-if="TIME_KEYS.has(f.key)">
                        <div style="display:flex;align-items:center;gap:8px">
                          <el-input :model-value="formData[f.key] || '未记录'" readonly style="flex:1" />
                          <el-button size="small" type="primary" :disabled="!canEdit" @click="captureTime(f.key)">记录</el-button>
                        </div>
                      </template>
                      <el-date-picker v-else-if="getFieldType(f)==='datetime'" v-model="formData[f.key]" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" :disabled="!canEdit" style="width:100%" />
                      <el-select v-else-if="getFieldType(f)==='select'" v-model="formData[f.key]" :disabled="!canEdit" style="width:100%" clearable>
                        <el-option v-for="opt in getFieldOptions(f)" :key="opt" :label="opt" :value="opt" />
                      </el-select>
                      <el-select v-else-if="getFieldType(f)==='multiselect'" v-model="formData[f.key]" :disabled="!canEdit" style="width:100%" multiple collapse-tags>
                        <el-option v-for="opt in getFieldOptions(f)" :key="opt" :label="opt" :value="opt" />
                      </el-select>
                      <el-input v-else-if="getFieldType(f)==='textarea'" v-model="formData[f.key]" :disabled="!canEdit" type="textarea" :rows="2" />
                      <span v-else>{{ formData[f.key] }}</span>
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
              <div style="margin-top:12px">
                <span style="font-size:13px;color:#475569">固定参数执行情况：</span>
                <el-radio-group v-model="fixedParamMode" :disabled="!canEdit" size="small">
                  <el-radio value="按默认参数执行">按默认参数执行</el-radio>
                  <el-radio value="存在偏离">存在偏离</el-radio>
                </el-radio-group>
              </div>
              <div v-if="fixedParamMode==='存在偏离'" style="margin-top:8px;padding:8px 12px;background:#FEF3C7;border-radius:6px;font-size:12px;color:#92400E">
                仅修改实际发生偏离的参数，并在⑥异常与设备文件中记录原因。
              </div>
            </el-card>

            <!-- Core manual fields (本次核查与实际记录) -->
            <el-card v-if="coreManualFields.length" shadow="never" class="mb-card-sm">
              <template #header><strong>本次核查与实际记录</strong></template>
              <div style="font-size:12px;color:#94A3B8;margin-bottom:8px">这里只填写仪器核查、过程实测和本次特有信息；前序已录入的数据不会重复询问。</div>
              <el-form label-width="160px" label-position="left" size="small">
                <el-row :gutter="16">
                  <el-col v-for="f in coreManualFields" :key="f.key" :span="8">
                    <el-form-item :label="f.label" :required="isFieldRequired(f)">
                      <el-input v-if="getFieldType(f)==='text'" v-model="formData[f.key]" :disabled="!canEdit" />
                      <el-input-number v-else-if="getFieldType(f)==='number'" v-model="formData[f.key]" :disabled="!canEdit" style="width:100%" controls-position="right" />
                      <el-date-picker v-else-if="getFieldType(f)==='date'" v-model="formData[f.key]" type="date" value-format="YYYY-MM-DD" :disabled="!canEdit" style="width:100%" />
                      <template v-else-if="TIME_KEYS.has(f.key)">
                        <div style="display:flex;align-items:center;gap:8px">
                          <el-input :model-value="formData[f.key] || '未记录'" readonly style="flex:1" />
                          <el-button size="small" type="primary" :disabled="!canEdit" @click="captureTime(f.key)">记录</el-button>
                        </div>
                      </template>
                      <el-date-picker v-else-if="getFieldType(f)==='datetime'" v-model="formData[f.key]" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" :disabled="!canEdit" style="width:100%" />
                      <el-select v-else-if="getFieldType(f)==='select'" v-model="formData[f.key]" :disabled="!canEdit" style="width:100%" clearable>
                        <el-option v-for="opt in getFieldOptions(f)" :key="opt" :label="opt" :value="opt" />
                      </el-select>
                      <el-select v-else-if="getFieldType(f)==='multiselect'" v-model="formData[f.key]" :disabled="!canEdit" style="width:100%" multiple collapse-tags>
                        <el-option v-for="opt in getFieldOptions(f)" :key="opt" :label="opt" :value="opt" />
                      </el-select>
                      <el-input v-else-if="getFieldType(f)==='textarea'" v-model="formData[f.key]" :disabled="!canEdit" type="textarea" :rows="2" />
                      <span v-else>{{ formData[f.key] }}</span>
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
            </el-card>

            <!-- Standard block auto-calc (rough/HV only) -->
            <el-card v-if="standardBlockAvg" shadow="never" class="mb-card-sm">
              <template #header><strong>标准样品核查（自动计算）</strong></template>
              <div style="padding:12px;background:#EFF6FF;border-radius:8px;border:1px solid #BFDBFE">
                <div style="font-size:12px;color:#1E40AF;margin-bottom:4px">{{ standardBlockAvg.label }}</div>
                <div style="font-size:20px;font-weight:700;color:#0F172A">{{ standardBlockAvg.value }}</div>
              </div>
            </el-card>

            <!-- Process monitoring fields -->
            <el-card v-if="processFields.length" shadow="never" class="mb-card-sm">
              <template #header><strong>过程监测明细（按原始记录母版）</strong></template>
              <div style="font-size:12px;color:#94A3B8;margin-bottom:8px">母版要求的重复核查和过程监测集中在这里；正常状态已预设，只需填写本次实际读数与时间。</div>
              <el-form label-width="160px" label-position="left" size="small">
                <el-row :gutter="16">
                  <el-col v-for="f in processFields" :key="f.key" :span="8">
                    <el-form-item :label="f.label" :required="isFieldRequired(f)">
                      <el-input v-if="getFieldType(f)==='text'" v-model="formData[f.key]" :disabled="!canEdit" />
                      <el-input-number v-else-if="getFieldType(f)==='number'" v-model="formData[f.key]" :disabled="!canEdit" style="width:100%" controls-position="right" />
                      <el-date-picker v-else-if="getFieldType(f)==='date'" v-model="formData[f.key]" type="date" value-format="YYYY-MM-DD" :disabled="!canEdit" style="width:100%" />
                      <template v-else-if="TIME_KEYS.has(f.key)">
                        <div style="display:flex;align-items:center;gap:8px">
                          <el-input :model-value="formData[f.key] || '未记录'" readonly style="flex:1" />
                          <el-button size="small" type="primary" :disabled="!canEdit" @click="captureTime(f.key)">记录</el-button>
                        </div>
                      </template>
                      <el-date-picker v-else-if="getFieldType(f)==='datetime'" v-model="formData[f.key]" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" :disabled="!canEdit" style="width:100%" />
                      <el-select v-else-if="getFieldType(f)==='select'" v-model="formData[f.key]" :disabled="!canEdit" style="width:100%" clearable>
                        <el-option v-for="opt in getFieldOptions(f)" :key="opt" :label="opt" :value="opt" />
                      </el-select>
                      <el-select v-else-if="getFieldType(f)==='multiselect'" v-model="formData[f.key]" :disabled="!canEdit" style="width:100%" multiple collapse-tags>
                        <el-option v-for="opt in getFieldOptions(f)" :key="opt" :label="opt" :value="opt" />
                      </el-select>
                      <el-input v-else-if="getFieldType(f)==='textarea'" v-model="formData[f.key]" :disabled="!canEdit" type="textarea" :rows="2" />
                      <span v-else>{{ formData[f.key] }}</span>
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
            </el-card>

            <div class="step-nav">
              <el-button @click="activeTab='2'">上一步</el-button>
              <el-button type="primary" @click="activeTab='4'">下一步：原始数据</el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- ═══════════════ ④ 原始数据 ═══════════════ -->
        <el-tab-pane label="④原始数据" name="4">
          <div class="tab-inner">
            <el-empty v-if="!config?.columns?.length" description="本实验无测量数据表格" />
            <div v-else>
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                <span style="font-size:12px;color:#94A3B8">按样品逐个填写；平均值和计算结果会实时刷新。</span>
                <el-button v-if="canEdit" type="primary" size="small" :icon="Plus" @click="addMeasurementRow">添加行</el-button>
              </div>

              <!-- Per-sample groups with per-row expanders -->
              <div v-for="[sno, rows] in sampleGroups" :key="sno" style="margin-bottom:16px">
                <el-card shadow="never" class="mb-card-sm">
                  <template #header><strong>样品：{{ sno }}</strong></template>

                  <!-- Per-row (per-face) containers -->
                  <div v-for="row in rows" :key="'row-'+row._index" style="margin-bottom:12px;padding:10px;border:1px solid #E2E8F0;border-radius:8px;background:#FAFBFC">
                    <!-- Face label -->
                    <div v-if="row.face" style="font-weight:600;font-size:13px;color:#0F172A;margin-bottom:8px">{{ row.face }}</div>

                    <!-- HV face direction select (2nd+ direction) -->
                    <div v-if="config?.kind==='hv' && row.face" style="margin-bottom:8px">
                      <span style="font-size:12px;color:#64748B;margin-right:8px">测量方向</span>
                      <el-select v-if="row._index > 0" v-model="measurementRows[row._index].face" :disabled="!canEdit" size="small" style="width:160px">
                        <el-option v-for="d in ['X轴方向','Y轴方向']" :key="d" :label="d" :value="d" />
                      </el-select>
                      <el-tag v-else size="small" type="info">Z轴方向</el-tag>
                    </div>

                    <!-- Thickness: 3 repeat expanders -->
                    <div v-if="config?.kind==='thickness'">
                      <el-collapse>
                        <el-collapse-item v-for="rp in [1,2,3]" :key="'rp'+rp" :title="'第'+rp+'次测量（固定端 / 中点 / 自由端）'" :name="'rp'+rp">
                          <el-row :gutter="12">
                            <el-col v-for="col in inputColumns.filter(c=>c.column_key.startsWith('r'+rp+'_'))" :key="col.column_key" :span="8" style="margin-bottom:8px">
                              <div style="font-size:11px;color:#64748B;margin-bottom:2px">{{ col.column_label }}</div>
                              <el-input-number v-if="getColumnType(col)==='number'" v-model="measurementRows[row._index][col.column_key]" :disabled="!canEdit" size="small" controls-position="right" style="width:100%" />
                              <el-input v-else v-model="measurementRows[row._index][col.column_key]" :disabled="!canEdit" size="small" />
                            </el-col>
                          </el-row>
                        </el-collapse-item>
                      </el-collapse>
                    </div>

                    <!-- Input fields in compact 3-col grid -->
                    <el-row :gutter="12">
                      <template v-for="col in inputColumns.filter(c => c.column_key !== 'note' && !c.column_key.startsWith('r') && (config?.kind!=='hv' || c.column_key!=='face'))" :key="col.column_key">
                        <el-col :span="8" v-if="!(config?.kind==='thickness' && c.column_key.startsWith('r'))" style="margin-bottom:8px">
                          <div style="font-size:11px;color:#64748B;margin-bottom:2px">{{ col.column_label }}</div>
                          <el-select v-if="getColumnType(col)==='select'" v-model="measurementRows[row._index][col.column_key]" :disabled="!canEdit" size="small" clearable style="width:100%">
                            <el-option v-for="opt in getColumnOptions(col)" :key="opt" :label="opt" :value="opt" />
                          </el-select>
                          <el-input-number v-else-if="getColumnType(col)==='number'" v-model="measurementRows[row._index][col.column_key]" :disabled="!canEdit" size="small" controls-position="right" style="width:100%" />
                          <el-input v-else v-model="measurementRows[row._index][col.column_key]" :disabled="!canEdit" size="small" />
                        </el-col>
                      </template>
                    </el-row>

                    <!-- Calculated fields (per row) -->
                    <div v-if="calcColumns.length" style="margin-top:10px;padding:8px 12px;background:#F1F5F9;border-radius:6px">
                      <div style="font-size:11px;font-weight:600;color:#475569;margin-bottom:4px">实时计算与判定</div>
                      <el-row :gutter="12">
                        <el-col v-for="col in calcColumns.filter(c => !(c.column_key==='retest_mean' && !(hasException || retest==='是')))" :key="col.column_key" :span="8">
                          <div style="font-size:11px;color:#64748B">{{ col.column_label }}</div>
                          <div style="font-size:15px;font-weight:600;color:#0F172A">{{ row[col.column_key] != null && row[col.column_key] !== '' ? row[col.column_key] : '等待原始数据' }}</div>
                        </el-col>
                      </el-row>
                      <!-- Conclusion badge per row -->
                      <div v-if="row.conclusion" style="margin-top:6px">
                        <el-tag v-if="['符合','合格'].includes(row.conclusion)" type="success" size="small">✓ {{ row.conclusion }}</el-tag>
                        <el-tag v-else-if="['不符合','不合格'].includes(row.conclusion)" type="danger" size="small">✗ {{ row.conclusion }}</el-tag>
                        <el-tag v-else type="info" size="small">{{ row.conclusion }}</el-tag>
                      </div>
                    </div>

                    <!-- Note toggle (per row, auto-shown when abnormal) -->
                    <div style="margin-top:6px">
                      <template v-if="isRowAbnormal(row)">
                        <el-input v-model="measurementRows[row._index].note" type="textarea" :rows="1" placeholder="备注/异常说明" :disabled="!canEdit" size="small" style="margin-top:4px" />
                      </template>
                      <template v-else>
                        <el-input v-if="measurementRows[row._index]._showNote" v-model="measurementRows[row._index].note" type="textarea" :rows="1" placeholder="备注/异常说明" :disabled="!canEdit" size="small" style="margin-top:4px" />
                        <el-button size="small" text @click="measurementRows[row._index]._showNote = !measurementRows[row._index]._showNote">{{ measurementRows[row._index]._showNote ? '收起备注' : '补充说明' }}</el-button>
                      </template>
                    </div>
                  </div>
                </el-card>
              </div>
            </div>

            <!-- ALL photos consolidated here, sorted by importance and grouped by category -->
            <el-card v-if="photoCheckpoints.length" shadow="never" class="mb-card" style="margin-top:16px">
              <template #header>
                <div style="display:flex;justify-content:space-between;align-items:center">
                  <strong>拍照留档</strong>
                  <span style="font-size:12px" :style="{color:missingPhotos.length?'#EA580C':'#22C55E'}">{{ photoCompletionCount }}/{{ totalPhotoRequired }} 已完成{{ missingPhotos.length ? '（'+missingPhotos.length+'张未拍）' : ' ✓' }}</span>
                </div>
              </template>
              <div v-if="isSecondaryEdit && !photoEditAllowed" style="font-size:12px;color:#94A3B8;margin-bottom:8px">照片留档未被退回，本步骤照片已锁定。</div>
              <!-- Grouped by checkpoint_group -->
              <div v-for="(cps, groupName) in photoCheckpointGroups" :key="groupName" style="margin-bottom:16px">
                <div style="font-size:13px;font-weight:600;color:#475569;margin-bottom:8px;padding:4px 8px;background:#F1F5F9;border-radius:4px">
                  {{ groupName }}
                  <span style="font-weight:400;color:#94A3B8;font-size:12px;margin-left:8px">{{ cps.filter(cp=>cp.file&&cp.previewUrl).length }}/{{ cps.length }}</span>
                </div>
                <div v-for="cp in cps" :key="cp.code" class="photo-cl-item" :class="{missing:cp.required!==false&&!cp.previewUrl}">
                  <div class="photo-cl-label">
                    <span v-if="cp.required!==false" style="color:#EF4444;font-weight:700">*</span>
                    <span :style="{color:cp.previewUrl?'#166534':'#334155'}">{{ cp.label }}</span>
                    <el-tag v-if="cp.isSampleLevel" size="small" type="info" style="margin-left:4px">逐样拍摄</el-tag>
                    <el-tag v-if="cp.previewUrl" size="small" type="success" style="margin-left:6px">已拍摄</el-tag>
                  </div>
                  <!-- Camera hint -->
                  <div v-if="cameraHints[cp.code]" style="font-size:11px;color:#94A3B8;margin-bottom:4px">📷 {{ cameraHints[cp.code] }}</div>
                  <!-- Task-level photo (only for non-sample-level checkpoints) -->
                  <template v-if="!cp.isSampleLevel">
                    <div v-if="cp.previewUrl" style="margin-bottom:6px"><img :src="cp.previewUrl" style="max-width:100%;max-height:140px;border-radius:6px;border:1px solid #E2E8F0" /></div>
                    <div v-if="activeCameraCp !== cp || activeCameraSample !== ''" style="display:flex;gap:6px;margin-bottom:6px">
                      <el-button size="small" :type="cp.previewUrl?'default':'primary'" @click="openCamera(cp)" :disabled="!canEdit || !photoEditAllowed"><el-icon style="margin-right:3px"><Camera /></el-icon>{{ cp.previewUrl?'重拍':'拍照' }}</el-button>
                      <el-button v-if="cp.previewUrl" size="small" type="danger" @click="removePhoto(cp)" :disabled="!canEdit || !photoEditAllowed">删除</el-button>
                    </div>
                    <CameraCapture v-if="activeCameraCp === cp && activeCameraSample === ''" :checkpoint="cp" :sampleNo="''" :cameraHint="cameraHints[cp.code] || ''" @photo-taken="onPhotoTaken" @close="closeCamera" />
                  </template>
                  <!-- Per-sample slots for sample-level checkpoints -->
                  <div v-if="cp.isSampleLevel && sampleIds.length" class="sample-photo-slots">
                    <div style="font-size:11px;font-weight:600;color:#64748B;margin-bottom:6px">逐样拍照（共{{ sampleIds.length }}个样品）</div>
                    <div v-for="sno in sampleIds" :key="sno" style="display:flex;align-items:center;gap:8px;margin-bottom:6px;padding:6px 8px;background:#F8FAFC;border-radius:4px;border:1px solid #E2E8F0">
                      <span style="font-size:12px;font-weight:500;min-width:80px">{{ sno }}</span>
                      <template v-if="cp.samplePhotos[sno]?.previewUrl">
                        <img :src="cp.samplePhotos[sno].previewUrl" style="height:40px;width:auto;border-radius:3px;border:1px solid #CBD5E1" />
                        <el-tag size="small" type="success">✓</el-tag>
                        <el-button v-if="activeCameraCp !== cp || activeCameraSample !== sno" size="small" @click="openCamera(cp, sno)" :disabled="!canEdit || !photoEditAllowed">重拍</el-button>
                        <el-button v-if="(activeCameraCp !== cp || activeCameraSample !== sno) && cp.samplePhotos[sno]?.previewUrl" size="small" type="danger" @click="removePhoto(cp, sno)" :disabled="!canEdit || !photoEditAllowed">删除</el-button>
                      </template>
                      <template v-else>
                        <span v-if="activeCameraCp !== cp || activeCameraSample !== sno" style="font-size:11px;color:#EF4444">未拍摄</span>
                        <el-button v-if="activeCameraCp !== cp || activeCameraSample !== sno" size="small" type="primary" @click="openCamera(cp, sno)" :disabled="!canEdit || !photoEditAllowed"><el-icon style="margin-right:2px"><Camera /></el-icon>拍照</el-button>
                      </template>
                    </div>
                    <!-- Inline camera for per-sample checkpoint -->
                    <CameraCapture v-if="activeCameraCp === cp && activeCameraSample" :checkpoint="cp" :sampleNo="activeCameraSample" :cameraHint="cameraHints[cp.code] || ''" @photo-taken="onPhotoTaken" @close="closeCamera" />
                  </div>
                </div>
              </div>
            </el-card>

            <div class="step-nav">
              <el-button @click="activeTab='3'">上一步</el-button>
              <el-button type="primary" @click="activeTab='5'">下一步：母版过程确认</el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- ═══════════════ ⑤ 母版过程确认 ═══════════════ -->
        <el-tab-pane label="⑤母版过程确认" name="5">
          <div class="tab-inner">
            <el-card shadow="never" class="mb-card">
              <template #header><strong>母版过程确认</strong></template>
              <div style="font-size:13px;color:#64748B;margin-bottom:16px">这里仅显示前四步尚不能自动取得的现场观察和实际填空。按原始记录表分区排列，可对明确的正常项一键确认。</div>
              <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
                <el-descriptions-item label="SOP版本">{{ config.sop_version || 'A/0' }}</el-descriptions-item>
                <el-descriptions-item label="原始记录模板">{{ config.record_template_file || config.record_template_version || '-' }}</el-descriptions-item>
                <el-descriptions-item label="实验配置版本">{{ config.version || '-' }}</el-descriptions-item>
                <el-descriptions-item label="检测标准">{{ task.standard || '-' }}</el-descriptions-item>
              </el-descriptions>

              <!-- Template supplement fields -->
              <div v-if="!templateFields.length" style="padding:16px;background:#F0FDF4;border-radius:8px;border:1px solid #BBF7D0">
                <span style="color:#166534">✅ 受控原始记录模板全部字段已由前序数据、实验记录或系统规则覆盖。</span>
                <div v-if="config.record_template_file" style="font-size:12px;color:#64748B;margin-top:4px">当前模板：{{ config.record_template_file }} v{{ config.record_template_version || 'A/0' }}</div>
                <div v-if="!config.record_template_file" style="font-size:12px;color:#94A3B8;margin-top:4px">未检测到模板文件，请上传受控原始记录模板后刷新。</div>
              </div>
              <div v-else>
                <div style="margin-bottom:12px;padding:8px 12px;background:#EFF6FF;border-radius:6px;border:1px solid #BFDBFE">
                  <span style="color:#1E40AF;font-size:13px">母版过程确认：{{ templateFields.filter(f => f.value).length }}/{{ templateFields.length }} 项已完成。每个分区可一键确认明确的正常项；实际参数、类别和异常内容仍需本人填写。</span>
                </div>
                <!-- Group by section -->
                <div v-for="(sectionFields, sectionName) in templateFieldsGrouped" :key="sectionName" style="margin-bottom:16px">
                  <el-collapse>
                    <el-collapse-item :title="`${sectionName}｜${sectionFields.filter(f=>f.value).length}/${sectionFields.length} 已完成`" :name="sectionName">
                      <!-- Batch confirm button -->
                      <div v-if="sectionFields.some(f => (f.template_text || '').includes('□') || (f.template_text || '').includes('☐'))" style="margin-bottom:8px">
                        <el-button size="small" :disabled="!canEdit" @click="batchConfirmSection(sectionName)">本区正常项一键确认</el-button>
                        <div style="font-size:12px;color:#94A3B8;margin-top:3px">只批量确认含义明确的"正常/符合/无异常"项目；具体参数和类别不会被代填。</div>
                      </div>
                      <el-form label-position="top" size="small">
                        <el-row :gutter="16">
                          <el-col v-for="f in sectionFields" :key="f.key" :span="8" style="margin-bottom:12px">
                            <el-form-item :label="f.label || f.position">
                              <!-- Checkbox-detected fields -->
                              <template v-if="(f.template_text || '').includes('□') || (f.template_text || '').includes('☐')">
                                <div style="font-size:11px;color:#94A3B8;margin-bottom:3px">
                                  选项：{{ _checkboxChoices(f.template_text || '').join('、') }}
                                </div>
                                <!-- Multi-select for independent confirmations -->
                                <el-select
                                  v-if="_checkboxFieldMeta(f.label||'', _checkboxChoices(f.template_text||'')).multi"
                                  v-model="_parseCheckboxValue(f.template_text||'', templateFields.find(tf=>tf.key===f.key)?.value||'').selected"
                                  multiple
                                  :disabled="!canEdit"
                                  placeholder="选择所有实际符合的项目"
                                  style="width:100%"
                                  @change="(vals) => { const tf = templateFields.find(t=>t.key===f.key); if(tf) { const s = _parseCheckboxValue(f.template_text||'', tf.value||''); tf.value = _filledCheckboxText(f.template_text||'', vals||[], s.note) } }"
                                >
                                  <el-option v-for="c in _checkboxChoices(f.template_text||'')" :key="c" :label="c" :value="c" />
                                </el-select>
                                <!-- Single-select for exclusive choices -->
                                <el-select
                                  v-else
                                  :model-value="_parseCheckboxValue(f.template_text||'', templateFields.find(tf=>tf.key===f.key)?.value||'').selected[0] || '请选择'"
                                  :disabled="!canEdit"
                                  placeholder="选择实际记录值"
                                  style="width:100%"
                                  @change="(val) => { const tf = templateFields.find(t=>t.key===f.key); if(tf) { const s = _parseCheckboxValue(f.template_text||'', tf.value||''); tf.value = _filledCheckboxText(f.template_text||'', val && val!=='请选择' ? [val] : [], s.note) } }"
                                >
                                  <el-option value="请选择" label="请选择" />
                                  <el-option v-for="c in _checkboxChoices(f.template_text||'')" :key="c" :label="c" :value="c" />
                                </el-select>
                                <!-- Note for "其他"/"异常" selections -->
                                <el-input
                                  v-if="_choiceNeedsNote(_parseCheckboxValue(f.template_text||'', templateFields.find(tf=>tf.key===f.key)?.value||'').selected) || ((f.template_text||'').match(/(_{2,}|＿{2,}|…{2,})/) && _parseCheckboxValue(f.template_text||'', templateFields.find(tf=>tf.key===f.key)?.value||'').selected.length)"
                                  :model-value="_parseCheckboxValue(f.template_text||'', templateFields.find(tf=>tf.key===f.key)?.value||'').note"
                                  @update:model-value="(note) => { const tf = templateFields.find(t=>t.key===f.key); if(tf) { const s = _parseCheckboxValue(f.template_text||'', tf.value||''); tf.value = _filledCheckboxText(f.template_text||'', s.selected, note||'') } }"
                                  placeholder="补充说明"
                                  :disabled="!canEdit"
                                  size="small"
                                  style="margin-top:4px"
                                />
                              </template>
                              <!-- Blank-fill fields -->
                              <template v-else>
                                <el-input v-model="templateFields.find(tf=>tf.key===f.key).value" :placeholder="'填写实际记录'" :disabled="!canEdit" />
                              </template>
                            </el-form-item>
                          </el-col>
                        </el-row>
                      </el-form>
                    </el-collapse-item>
                  </el-collapse>
                </div>
              </div>
            </el-card>

            <div class="step-nav">
              <el-button @click="activeTab='4'">上一步</el-button>
              <el-button type="primary" @click="activeTab='6'">下一步：异常与设备文件</el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- ═══════════════ ⑥ 异常与设备文件 ═══════════════ -->
        <el-tab-pane label="⑥异常与设备文件" name="6">
          <div class="tab-inner">
            <!-- Exception & Summary -->
            <el-card shadow="never" class="mb-card">
              <template #header><strong>异常与结果</strong></template>
              <div style="margin-bottom:12px">
                <span style="font-size:13px;color:#475569">实验完成状态：</span>
                <el-radio-group v-model="overallStatus" :disabled="!canEdit" size="small">
                  <el-radio value="正常完成">正常完成</el-radio>
                  <el-radio value="存在异常">存在异常</el-radio>
                </el-radio-group>
              </div>
              <div v-if="hasException">
                <el-input v-model="deviation" type="textarea" :rows="3" placeholder="异常、偏离、影响评估及处理措施" :disabled="!canEdit" style="margin-bottom:12px" />
                <div style="margin-bottom:8px">
                  <span style="font-size:13px;color:#475569">是否复测/重制：</span>
                  <el-radio-group v-model="retest" :disabled="!canEdit" size="small">
                    <el-radio value="否">否</el-radio>
                    <el-radio value="是">是</el-radio>
                  </el-radio-group>
                </div>
              </div>
              <div v-else style="color:#22C55E;margin-bottom:12px">实验无异常，无需复测；复测数据和复测平均值字段不显示。</div>

              <el-divider />
              <div style="font-size:12px;color:#64748B;margin-bottom:8px">系统自动生成的结果摘要</div>
              <!-- Auto-generated report -->
              <div style="margin-bottom:16px;padding:12px;background:#F0FDF4;border-radius:8px;border:1px solid #BBF7D0">
                <div style="font-size:13px;font-weight:600;color:#166534;margin-bottom:4px">实际检验结果摘要</div>
                <div style="font-size:14px;color:#0F172A;white-space:pre-wrap;margin-bottom:8px">{{ autoReport.summary }}</div>
                <div style="font-size:13px;font-weight:600;color:#166534;margin-bottom:4px">单项结论</div>
                <el-tag v-if="autoReport.conclusion === '符合'" type="success" size="default">符合</el-tag>
                <el-tag v-else-if="autoReport.conclusion === '不符合'" type="danger" size="default">不符合</el-tag>
                <el-tag v-else-if="autoReport.conclusion" type="warning" size="default">{{ autoReport.conclusion }}</el-tag>
                <span v-else style="color:#94A3B8">尚未形成有效检验结果</span>
              </div>

              <!-- Manual override toggle -->
              <el-collapse>
                <el-collapse-item title="手动修正报告结果（仅在系统自动生成不准确时使用）">
                  <el-input v-model="reportSummary" type="textarea" :rows="3" placeholder="手动输入检验结果摘要（覆盖自动生成）" :disabled="!canEdit" style="margin-bottom:8px" />
                  <el-input v-model="reportConclusion" placeholder="手动输入单项结论（覆盖自动生成）" :disabled="!canEdit" />
                </el-collapse-item>
              </el-collapse>
            </el-card>

            <!-- Photo status -->
            <el-card shadow="never" class="mb-card">
              <template #header><strong>拍照留档状态</strong></template>
              <el-table :data="sortedPhotoCheckpoints" size="small" stripe>
                <el-table-column prop="label" label="拍照节点" min-width="200" />
                <el-table-column prop="checkpointGroup" label="分组" width="100" />
                <el-table-column label="强制" width="60"><template #default="{row}">{{ row.required!==false ? '是' : '否' }}</template></el-table-column>
                <el-table-column label="逐样" width="60"><template #default="{row}">{{ row.isSampleLevel ? '是' : '否' }}</template></el-table-column>
                <el-table-column label="完成" width="70">
                  <template #default="{row}"><el-tag :type="(row.file && row.previewUrl)?'success':'danger'" size="small">{{ (row.file && row.previewUrl)?'✓':'✗' }}</el-tag></template>
                </el-table-column>
                <el-table-column label="照片数" width="70"><template #default="{row}">{{ (row.file && row.previewUrl)?1:0 }}</template></el-table-column>
              </el-table>
              <div v-if="missingPhotos.length" style="margin-top:8px;color:#EA580C">还有 {{ missingPhotos.length }} 张必需照片未完成（共需 {{ totalPhotoRequired }} 张），请回到④原始数据步骤拍摄。</div>
              <div v-else style="margin-top:8px;color:#22C55E">全部必需照片已完成（共 {{ totalPhotoRequired }} 张）。</div>
            </el-card>

            <!-- Device original files -->
            <el-card shadow="never" class="mb-card">
              <template #header><strong>设备原始文件</strong></template>
              <div style="font-size:12px;color:#94A3B8;margin-bottom:12px">这里只允许上传设备导出的原始数据、曲线或校准文件；图片和截图必须通过上面的现场相机取得。</div>
              <div v-if="isSecondaryEdit && !deviceFileEditAllowed" style="font-size:12px;color:#94A3B8;margin-bottom:8px">设备原始文件未被退回，本步骤文件已锁定。</div>
              <div style="display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap" v-else>
                <el-select v-model="deviceFileType" :disabled="!canEdit || !deviceFileEditAllowed" placeholder="原始文件类型" size="small" style="width:200px">
                  <el-option v-for="t in ['设备原始数据文件','仪器曲线文件','X射线原始图像','校准/核查文件','其他原始文件']" :key="t" :label="t" :value="t" />
                </el-select>
                <el-select v-if="sampleIds.length" v-model="deviceFileSampleNo" :disabled="!canEdit || !deviceFileEditAllowed" placeholder="关联样品（可选）" clearable size="small" style="width:160px">
                  <el-option v-for="sno in sampleIds" :key="sno" :label="'样品：'+sno" :value="sno" />
                </el-select>
                <el-upload
                  :disabled="!canEdit || !deviceFileEditAllowed"
                  :auto-upload="false"
                  :show-file-list="true"
                  :on-change="handleDeviceFileChange"
                  accept=".csv,.xlsx,.xls,.pdf,.txt,.dat,.xml,.json,.zip"
                >
                  <el-button size="small" :disabled="!canEdit || !deviceFileEditAllowed">上传设备原始文件</el-button>
                </el-upload>
                <el-button v-if="deviceFiles.length" size="small" type="primary" @click="uploadDeviceFiles" :loading="uploadingFiles" :disabled="!deviceFileType">保存{{ deviceFiles.length }}个设备文件</el-button>
              </div>
            </el-card>

            <!-- Emergency -->
            <el-card shadow="never" style="border-color:#FCA5A5" class="mb-card">
              <template #header><div style="display:flex;align-items:center;gap:6px;color:#DC2626"><span style="font-size:18px">🚨</span><strong>设备故障 / 安全风险——立即中断实验</strong></div></template>
              <div style="color:#DC2626;font-size:13px;margin-bottom:12px">设备发生故障、数据异常漂移或出现高温/高压/气源等安全风险时，立即中断；不得继续检测或删除已采集数据。提交后任务状态将被冻结并启动故障处置流程。</div>
              <el-collapse style="border:none">
                <el-collapse-item title="展开故障报告表单" name="1">
                  <el-form label-width="150px" size="small">
                    <el-form-item label="故障设备">
                      <el-select v-model="emergencyForm.fault_equipment" style="width:100%" filterable allow-create placeholder="管理编号或设备名称">
                        <el-option v-for="eq in equipmentChecks" :key="eq.management_no" :label="`${eq.equipment_name}（${eq.management_no}）`" :value="eq.management_no" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="故障类型">
                      <el-select v-model="emergencyForm.fault_type" style="width:100%">
                        <el-option v-for="t in ['设备停机/无响应','软件报错','数据漂移/异常','异响/机械异常','温度/压力/气源异常','其他']" :key="t" :label="t" :value="t" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="报错代码"><el-input v-model="emergencyForm.error_code" placeholder="无则填'无'" /></el-form-item>
                    <el-form-item label="试验阶段"><el-input v-model="emergencyForm.current_stage" placeholder="故障发生时的实验阶段" /></el-form-item>
                    <el-form-item label="故障现象"><el-input v-model="emergencyForm.fault_description" type="textarea" :rows="2" placeholder="详细描述设备表现和异常现象" /></el-form-item>
                    <el-form-item label="已完成步骤"><el-input v-model="emergencyForm.completed_steps" type="textarea" :rows="1" placeholder="已成功完成的实验步骤" /></el-form-item>
                    <el-form-item label="已采集数据"><el-input v-model="emergencyForm.collected_data" type="textarea" :rows="1" placeholder="已采集且可保留的数据说明" /></el-form-item>
                    <el-form-item label="样品状态"><el-input v-model="emergencyForm.sample_condition" type="textarea" :rows="1" placeholder="中断时样品的状态和摆放位置" /></el-form-item>
                    <el-form-item label="现场风险">
                      <el-select v-model="emergencyForm.site_risks" multiple placeholder="选择所有存在的现场风险" style="width:100%">
                        <el-option v-for="r in ['无持续危险','高温','高压','辐射','气源','水路','化学品','机械运动','电气风险']" :key="r" :label="r" :value="r" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="已实施处置">
                      <el-select v-model="emergencyForm.immediate_actions" multiple placeholder="选择已完成的紧急处置措施" style="width:100%">
                        <el-option v-for="a in ['终止试验动作','按下设备急停','切断危险介质','保护故障现场','样品保持原位并等待隔离','已口头上报质量负责人和管理员']" :key="a" :label="a" :value="a" />
                      </el-select>
                    </el-form-item>
                    <el-form-item>
                      <el-checkbox v-model="emergencyConfirm">我确认以上故障信息属实，确认中断实验并冻结当前记录</el-checkbox>
                    </el-form-item>
                    <el-form-item>
                      <el-button type="danger" @click="submitEmergency" :loading="submittingEmergency" :disabled="!emergencyConfirm">确认中断、冻结当前记录并启动故障处置</el-button>
                    </el-form-item>
                  </el-form>
                </el-collapse-item>
              </el-collapse>
            </el-card>

            <div class="step-nav">
              <el-button @click="activeTab='5'">上一步</el-button>
              <el-button type="primary" @click="activeTab='7'">下一步：保存提交</el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- ═══════════════ ⑦ 保存提交 ═══════════════ -->
        <el-tab-pane label="⑦保存提交" name="7">
          <div class="tab-inner">
            <el-alert v-if="!task?.experiment_ended_at" title="实验尚未点击「记录实验结束时间」。结束前暂不显示未填写区域；可先保存草稿。" type="info" :closable="false" show-icon style="margin-bottom:16px" />

            <el-card shadow="never" class="mb-card">
              <template #header><strong>提交前检查</strong></template>
              <div style="display:flex;flex-direction:column;gap:8px;font-size:14px">
                <div v-for="(passed, label) in business_completion_summary().sections" :key="label" :style="{color:passed?'#166534':'#94A3B8'}">
                  {{ passed?'✅':'⚠️' }} {{ label }}
                </div>
              </div>
              <div v-if="business_completion_summary().issues.length" style="margin-top:12px">
                <el-alert title="仍有需要处理的项目：" type="warning" :closable="false" show-icon>
                  <ul style="margin:4px 0;padding-left:20px;font-size:13px">
                    <li v-for="item in business_completion_summary().issues.slice(0, 30)" :key="item">{{ item }}</li>
                  </ul>
                </el-alert>
              </div>
              <div v-else style="margin-top:12px;color:#22C55E">实验记录已完整，可提交复核。</div>
            </el-card>

            <!-- Result preview -->
            <el-card v-if="autoReport.summary !== '尚未形成有效检验结果'" shadow="never" class="mb-card">
              <template #header><strong>计算结果摘要（将随记录提交）</strong></template>
              <div style="margin-bottom:8px;padding:8px 12px;background:#F8FAFC;border-radius:6px">
                <div style="font-size:12px;color:#64748B;margin-bottom:3px">检验结果</div>
                <div style="font-size:14px;color:#0F172A;white-space:pre-wrap">{{ autoReport.summary }}</div>
              </div>
              <div style="padding:8px 12px;background:#F8FAFC;border-radius:6px">
                <div style="font-size:12px;color:#64748B;margin-bottom:3px">单项结论</div>
                <el-tag v-if="autoReport.conclusion === '符合'" type="success">符合</el-tag>
                <el-tag v-else-if="autoReport.conclusion === '不符合'" type="danger">不符合</el-tag>
                <el-tag v-else type="warning">{{ autoReport.conclusion }}</el-tag>
              </div>
            </el-card>

            <el-card shadow="never" class="mb-card">
              <template #header><strong>同步记录与发布前检查</strong></template>
              <div style="font-size:12px;color:#94A3B8;margin-bottom:12px">提交前必须点击「同步当前记录并检查」，系统将把当前所有步骤中的数据同步至服务器并运行校验。</div>
              <el-button type="warning" @click="syncAndCheck" :loading="syncing" :disabled="!canEdit" size="large">同步当前记录并检查</el-button>
              <el-alert v-if="validationReady" type="success" :closable="false" show-icon style="margin-top:12px" title="记录已同步至服务器，请确认以下自查后提交复核。" />
            </el-card>

            <el-card shadow="never" class="mb-card">
              <template #header><strong>实验员自查与提交</strong></template>
              <div style="font-size:12px;color:#94A3B8;margin-bottom:12px">提交后，系统会把七个步骤中的业务数据回填至受控Word母版原位置。</div>
              <el-form label-position="top" size="small">
                <el-form-item>
                  <el-checkbox v-model="testerSelfCheck" :disabled="!canEdit">我已完成实验员自查：样品、设备、环境、原始数据、计算结果、照片和异常记录均已核对</el-checkbox>
                </el-form-item>
                <el-form-item label="修改原因（首次记录可不填）">
                  <el-input v-model="changeReason" placeholder="首次记录可不填" :disabled="!canEdit" />
                </el-form-item>
              </el-form>
            </el-card>

            <div class="step-nav" style="justify-content:space-between">
              <el-button @click="activeTab='6'">上一步</el-button>
              <div style="display:flex;gap:8px">
                <el-button v-if="canEdit" @click="handleSave(false)" :loading="saving" size="large">保存草稿</el-button>
                <el-button v-if="canEdit" type="primary" @click="handleSave(true)" :loading="saving" :disabled="!testerSelfCheck || !validationReady" size="large">提交复核</el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>

      </el-tabs>
    </div>
  </div>
</template>

<style scoped>
.experiment-run { max-width: 1400px; }

.page-header { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:12px; }
.header-left h1 { font-size:22px; font-weight:600; color:#0F172A; margin:0; }
.task-no { font-size:14px; color:#94A3B8; font-weight:400; margin-left:8px; }
.task-meta { color:#64748B; font-size:13px; margin-top:4px; }
.header-actions { display:flex; gap:8px; flex-shrink:0; }

.status-bar { display:flex; gap:16px; align-items:center; margin-bottom:16px; padding:8px 12px; background:#F8FAFC; border-radius:8px; border:1px solid #E2E8F0; font-size:13px; flex-wrap:wrap; }
.config-source { color:#64748B; }
.time-info { color:#64748B; }

.workflow-area { margin-top:16px; }
.tab-inner { padding:20px 0; }
.step-nav { display:flex; gap:12px; margin-top:20px; padding-top:16px; border-top:1px solid #F1F5F9; }
.mb-card { margin-bottom:16px; }
.mb-card-sm { margin-bottom:12px; }
.mb-table { margin-bottom:8px; }

.equip-grid { display:flex; flex-direction:column; gap:12px; }
.equip-err { border-color:#FCA5A5 !important; background:#FFF5F5; }

/* Photo checklist */
.photo-checklist { margin-bottom:16px; }
.photo-cl-progress { padding:6px 12px; background:#F0F9FF; border-radius:6px; border:1px solid #BAE6FD; font-size:12px; color:#0369A1; margin-bottom:10px; }
.photo-cl-item { padding:10px; border:1px solid #E2E8F0; border-radius:6px; margin-bottom:8px; background:#FAFAFA; }
.photo-cl-item.missing { border-left:3px solid #EF4444; }
.photo-cl-label { font-size:13px; font-weight:500; display:flex; align-items:center; gap:6px; margin-bottom:6px; }
</style>
