<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Check, Download } from '@element-plus/icons-vue'
import request from '../utils/request'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const isAdmin = computed(() => user.role === '管理员')
const canManage = computed(() => user.role === '管理员' || user.role === '样品管理员')

const methods = ref([])
const loading = ref(true)

// 版本列表
const versionDialogVisible = ref(false)
const versions = ref([])
const versionLoading = ref(false)
const selectedExperiment = ref(null)

// 新增检测项目
const addMethodDialogVisible = ref(false)
const addMethodLoading = ref(false)
const addMethodForm = ref({
  experiment_code: '', experiment_name: '', method_code: '',
  standard: '', category: '', kind: 'generic',
})

// 创建版本
const createDialogVisible = ref(false)
const createLoading = ref(false)
const createForm = ref({
  experiment_code: '', version: '', experiment_name: '',
  method_code: '', standard: '', category: '', kind: 'generic',
  effective_date: '', note: '',
})

// ============ 版本编辑器 ============
const editorVisible = ref(false)
const editorSaving = ref(false)
const editorLoading = ref(false)
const editorExperimentCode = ref('')
const editorVersion = ref('')
const editorActiveTab = ref('fields')

// 编辑器数据
const editFields = ref([])          // [{key, label, type, default, options, readonly, section_title, section_order}]
const editColumns = ref([])         // [{column_key, column_label, column_type, column_default}]
const editPhotos = ref([])          // [{code, label, required}]
const editPrechecks = ref([])       // [{label}]

const FIELD_TYPES = ['text', 'number', 'date', 'datetime', 'select', 'multiselect', 'checkbox', 'textarea']
const COLUMN_TYPES = ['number', 'calc', 'text', 'select:选项1|选项2']

onMounted(async () => {
  try {
    const { data } = await request.get('/config/methods')
    methods.value = data
  } finally {
    loading.value = false
  }
})

// ── 新增检测项目 ──
function showAddMethod() {
  addMethodForm.value = { experiment_code: '', experiment_name: '', method_code: '', standard: '', category: '', kind: 'generic' }
  addMethodDialogVisible.value = true
}

async function handleAddMethod() {
  const f = addMethodForm.value
  if (!f.experiment_code) { ElMessage.warning('请输入实验编码'); return }
  if (!f.experiment_name) { ElMessage.warning('请输入实验名称'); return }
  if (!f.method_code) { ElMessage.warning('请输入方法编号'); return }
  addMethodLoading.value = true
  try {
    await request.post('/methods', f)
    ElMessage.success('检测项目添加成功')
    addMethodDialogVisible.value = false
    const { data } = await request.get('/config/methods')
    methods.value = data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  } finally { addMethodLoading.value = false }
}

// ── 删除检测项目 ──
async function handleDeleteMethod(method) {
  try {
    await ElMessageBox.confirm(`确定要删除「${method.experiment_code} ${method.experiment_name}」吗？`, '确认删除', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    await request.delete(`/methods/${method.experiment_code}`)
    ElMessage.success('已删除')
    const { data } = await request.get('/config/methods')
    methods.value = data
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

// ── 版本列表 ──
async function openVersions(method) {
  selectedExperiment.value = method
  versionLoading.value = true
  versionDialogVisible.value = true
  try {
    const { data } = await request.get(`/config/${method.experiment_code}/versions`)
    versions.value = data
  } catch { versions.value = [] }
  finally { versionLoading.value = false }
}

// ── 新建版本 ──
function showCreateVersion() {
  createForm.value = {
    experiment_code: selectedExperiment.value.experiment_code,
    version: '', experiment_name: selectedExperiment.value.experiment_name,
    method_code: selectedExperiment.value.method_code || '',
    standard: selectedExperiment.value.standard || '',
    category: selectedExperiment.value.category || '',
    kind: selectedExperiment.value.kind || 'generic',
    effective_date: '', note: '',
  }
  createDialogVisible.value = true
}

async function handleCreateVersion() {
  const f = createForm.value
  if (!f.version) { ElMessage.warning('请输入版本号'); return }
  if (!f.experiment_name) { ElMessage.warning('请输入实验名称'); return }
  createLoading.value = true
  try {
    await request.post(`/config/${f.experiment_code}/versions`, f)
    ElMessage.success(`版本 ${f.version} 创建成功`)
    createDialogVisible.value = false
    openVersions(selectedExperiment.value)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally { createLoading.value = false }
}

// ── 激活/归档/删除版本 ──
async function activateVersion(ec, v) {
  try {
    await ElMessageBox.confirm(`确定激活版本「${v}」？其他现行版本将被归档。`, '确认激活', { type: 'info', confirmButtonText: '激活', cancelButtonText: '取消' })
    await request.put(`/config/${ec}/versions/${v}/status`, { status: '现行' })
    ElMessage.success(`版本 ${v} 已激活`)
    openVersions(selectedExperiment.value)
    const { data } = await request.get('/config/methods')
    methods.value = data
  } catch { /* cancelled */ }
}
async function archiveVersion(ec, v) {
  try {
    await ElMessageBox.confirm(`确定归档版本「${v}」？`, '确认归档', { type: 'warning', confirmButtonText: '归档', cancelButtonText: '取消' })
    await request.put(`/config/${ec}/versions/${v}/status`, { status: '历史' })
    ElMessage.success(`版本 ${v} 已归档`)
    openVersions(selectedExperiment.value)
    const { data } = await request.get('/config/methods')
    methods.value = data
  } catch { /* cancelled */ }
}
async function deleteVersion(ec, v) {
  try {
    await ElMessageBox.confirm(`确定删除版本「${v}」？仅草稿可删。`, '确认删除', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    await request.delete(`/config/${ec}/versions/${v}`)
    ElMessage.success(`版本 ${v} 已删除`)
    openVersions(selectedExperiment.value)
  } catch { /* cancelled */ }
}

// ============ 版本编辑器 ============

async function openEditor(versionRow) {
  const ec = selectedExperiment.value.experiment_code
  const v = versionRow.version
  editorExperimentCode.value = ec
  editorVersion.value = v
  editorActiveTab.value = 'fields'
  editorVisible.value = true
  editorLoading.value = true
  try {
    const { data } = await request.get(`/config/${ec}/versions/${v}`)
    editFields.value = (data.fields || []).map(f => ({ ...f, _dirty: false }))
    editColumns.value = (data.columns || []).map(c => ({ ...c, _dirty: false }))
    editPhotos.value = (data.photo_checkpoints || []).map(p => ({ code: p.code, label: p.label || p.checkpoint_label, required: p.required !== false, _dirty: false }))
    editPrechecks.value = (data.prechecks || []).map(p => ({ label: p.label || p.precheck_label || p.check_name, _dirty: false }))
  } catch (e) {
    // 加载失败时初始化为空
    editFields.value = []
    editColumns.value = []
    editPhotos.value = []
    editPrechecks.value = []
  } finally { editorLoading.value = false }
}

// ── 从模板导入 ──
async function loadFromTemplate() {
  if (editFields.value.length || editColumns.value.length) {
    try {
      await ElMessageBox.confirm('当前编辑器已有数据，导入模板将覆盖。确认？', '覆盖确认', { type: 'warning' })
    } catch { return }
  }
  editorLoading.value = true
  try {
    // 用 GET config/{code} 获取硬编码回退（无现行版本时自动回退）
    const { data } = await request.get(`/config/${editorExperimentCode.value}`)
    editFields.value = (data.fields || []).map(f => ({ ...f, _dirty: true }))
    editColumns.value = (data.columns || []).map(c => ({ ...c, _dirty: true }))
    editPhotos.value = (data.photo_checkpoints || []).map(p => ({ code: p.code || p.checkpoint_code, label: p.label || p.checkpoint_label, required: p.required !== false, _dirty: true }))
    editPrechecks.value = (data.prechecks || []).map(p => ({ label: p.label || p.checkpoint_label, _dirty: true }))
    ElMessage.success(`已导入模板：${editFields.value.length} 字段, ${editColumns.value.length} 列, ${editPhotos.value.length} 拍照节点`)
  } catch (e) {
    ElMessage.error('导入失败')
  } finally { editorLoading.value = false }
}

// ── 字段操作 ──
function addField() {
  const maxOrder = editFields.value.reduce((m, f) => Math.max(m, f.section_order || 0), 0)
  editFields.value.push({
    key: '', label: '', type: 'text', default: '', options: [], readonly: false,
    section_title: '', section_order: maxOrder, _dirty: true,
  })
}
function removeField(idx) { editFields.value.splice(idx, 1) }

// ── 列操作 ──
function addColumn() {
  editColumns.value.push({
    column_key: '', column_label: '', column_type: 'number', column_default: '', _dirty: true,
  })
}
function removeColumn(idx) { editColumns.value.splice(idx, 1) }

// ── 拍照节点 ──
function addPhoto() {
  editPhotos.value.push({ code: '', label: '', required: true, _dirty: true })
}
function removePhoto(idx) { editPhotos.value.splice(idx, 1) }

// ── 预检 ──
function addPrecheck() {
  editPrechecks.value.push({ label: '', _dirty: true })
}
function removePrecheck(idx) { editPrechecks.value.splice(idx, 1) }

// ── 保存编辑器 ──
async function saveEditor() {
  editorSaving.value = true
  try {
    // 构建提交数据 — 还原 DB 字段名
    const fieldsPayload = editFields.value.map(f => ({
      field_key: f.key, field_label: f.label, field_type: f.type,
      field_default: String(f.default ?? ''), field_options: Array.isArray(f.options) ? JSON.stringify(f.options) : String(f.options || ''),
      is_readonly: f.readonly || false, is_required: f.required || false,
      section_title: f.section_title || '', section_order: f.section_order || 0, sort_order: 0,
    }))
    const columnsPayload = editColumns.value.map(c => ({
      column_key: c.column_key, column_label: c.column_label, column_type: c.column_type,
      column_default: String(c.column_default ?? ''),
    }))
    const photosPayload = editPhotos.value.map(p => ({
      checkpoint_code: p.code, checkpoint_label: p.label, is_required: p.required !== false, sort_order: 0,
    }))
    const prechecksPayload = editPrechecks.value.map(p => ({
      precheck_label: p.label, precheck_code: '', is_required: true, sort_order: 0,
    }))

    await request.put(
      `/config/${editorExperimentCode.value}/versions/${editorVersion.value}`,
      { fields: fieldsPayload, columns: columnsPayload, photo_checkpoints: photosPayload, prechecks: prechecksPayload },
    )
    ElMessage.success('配置已保存')
    editorVisible.value = false
    openVersions(selectedExperiment.value)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally { editorSaving.value = false }
}

function getStatusTag(s) {
  const map = { '现行': 'success', '草稿': 'info', '历史': '' }
  return map[s] || 'info'
}

function optionsStr(opts) {
  if (Array.isArray(opts)) return opts.join(', ')
  if (typeof opts === 'string') {
    try { const p = JSON.parse(opts); if (Array.isArray(p)) return p.join(', ') } catch {}
    return opts
  }
  return ''
}
function parseOptionsInput(val) {
  return val.split(/[,;，；]/).map(s => s.trim()).filter(Boolean)
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>检测项目与方法库</h1>
      <el-button v-if="canManage" type="primary" :icon="Plus" @click="showAddMethod">新增检测项目</el-button>
    </div>

    <el-card>
      <el-table :data="methods" v-loading="loading" stripe empty-text="暂无数据">
        <el-table-column prop="experiment_code" label="项目代码" width="120" />
        <el-table-column prop="experiment_name" label="检测项目" min-width="200" />
        <el-table-column prop="method_code" label="方法编号" width="140" />
        <el-table-column prop="standard" label="标准" min-width="200" />
        <el-table-column prop="category" label="类别" width="120">
          <template #default="{ row }"><el-tag size="small">{{ row.category }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="kind" label="类型" width="100" />
        <el-table-column prop="current_version" label="现行版本" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.current_version" type="success" size="small">{{ row.current_version }}</el-tag>
            <span v-else style="color:#94A3B8">默认</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button text type="primary" @click="openVersions(row)">版本管理</el-button>
            <el-button v-if="canManage" text type="danger" :icon="Delete" @click="handleDeleteMethod(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- ====== 版本列表对话框 ====== -->
    <el-dialog v-model="versionDialogVisible" :title="`${selectedExperiment?.experiment_code} — 配置版本`" width="800px">
      <div v-if="isAdmin" style="margin-bottom:12px">
        <el-button type="primary" :icon="Plus" @click="showCreateVersion">新建版本</el-button>
      </div>
      <el-table :data="versions" v-loading="versionLoading" stripe empty-text="暂无配置版本">
        <el-table-column prop="version" label="版本号" width="100" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }"><el-tag :type="getStatusTag(row.status)" size="small">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="effective_date" label="生效日期" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column prop="approved_by" label="批准人" width="100" />
        <el-table-column label="操作" min-width="250" v-if="isAdmin">
          <template #default="{ row }">
            <el-button text type="primary" :icon="Edit" @click="openEditor(row)">编辑</el-button>
            <el-button v-if="row.status !== '现行'" text type="success" :icon="Check" @click="activateVersion(selectedExperiment.experiment_code, row.version)">激活</el-button>
            <el-button v-if="row.status === '现行'" text type="warning" @click="archiveVersion(selectedExperiment.experiment_code, row.version)">归档</el-button>
            <el-button v-if="row.status === '草稿'" text type="danger" :icon="Delete" @click="deleteVersion(selectedExperiment.experiment_code, row.version)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- ====== 版本编辑器对话框 ====== -->
    <el-dialog v-model="editorVisible" :title="`编辑配置 — ${editorExperimentCode} / ${editorVersion}`" width="1100px" :close-on-click-modal="false" v-loading="editorLoading">
      <div style="margin-bottom:12px;display:flex;gap:8px">
        <el-button :icon="Download" @click="loadFromTemplate">从硬编码模板导入</el-button>
        <span style="color:#94A3B8;font-size:12px;line-height:32px;margin-left:8px">导入后将覆盖当前编辑器数据</span>
      </div>

      <el-tabs v-model="editorActiveTab">
        <!-- 表单字段 -->
        <el-tab-pane label="表单字段" name="fields">
          <div style="margin-bottom:8px">
            <el-button size="small" :icon="Plus" @click="addField">添加字段</el-button>
            <span style="color:#94A3B8;font-size:12px;margin-left:8px">{{ editFields.length }} 个字段</span>
          </div>
          <div style="max-height:400px;overflow-y:auto">
            <el-table :data="editFields" size="small" stripe>
              <el-table-column prop="section_title" label="分区标题" width="140">
                <template #default="{ row }"><el-input v-model="row.section_title" size="small" placeholder="如 环境与设备" /></template>
              </el-table-column>
              <el-table-column prop="section_order" label="分区序" width="70">
                <template #default="{ row }"><el-input-number v-model="row.section_order" size="small" :min="0" controls-position="right" style="width:60px" /></template>
              </el-table-column>
              <el-table-column prop="key" label="字段编码" width="130">
                <template #default="{ row }"><el-input v-model="row.key" size="small" placeholder="如 test_date" /></template>
              </el-table-column>
              <el-table-column prop="label" label="字段标签" min-width="160">
                <template #default="{ row }"><el-input v-model="row.label" size="small" placeholder="如 检测日期" /></template>
              </el-table-column>
              <el-table-column prop="type" label="类型" width="110">
                <template #default="{ row }">
                  <el-select v-model="row.type" size="small" style="width:100px">
                    <el-option v-for="t in FIELD_TYPES" :key="t" :label="t" :value="t" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column prop="default" label="默认值" width="100">
                <template #default="{ row }"><el-input v-model="row.default" size="small" placeholder="可选" /></template>
              </el-table-column>
              <el-table-column prop="options" label="选项" width="140">
                <template #default="{ row }">
                  <el-input :model-value="optionsStr(row.options)" size="small" placeholder="逗号分隔" @change="(v) => row.options = parseOptionsInput(v || '')" />
                </template>
              </el-table-column>
              <el-table-column prop="readonly" label="只读" width="55">
                <template #default="{ row }"><el-checkbox v-model="row.readonly" size="small" /></template>
              </el-table-column>
              <el-table-column label="" width="50">
                <template #default="{ $index }"><el-button text type="danger" size="small" :icon="Delete" @click="removeField($index)" /></template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- 测量列 -->
        <el-tab-pane label="测量列" name="columns">
          <div style="margin-bottom:8px">
            <el-button size="small" :icon="Plus" @click="addColumn">添加列</el-button>
            <span style="color:#94A3B8;font-size:12px;margin-left:8px">{{ editColumns.length }} 列</span>
          </div>
          <el-table :data="editColumns" size="small" stripe>
            <el-table-column prop="column_key" label="列编码" width="140">
              <template #default="{ row }"><el-input v-model="row.column_key" size="small" placeholder="如 ra1" /></template>
            </el-table-column>
            <el-table-column prop="column_label" label="列标签" min-width="180">
              <template #default="{ row }"><el-input v-model="row.column_label" size="small" placeholder="如 Ra1/μm" /></template>
            </el-table-column>
            <el-table-column prop="column_type" label="类型" width="170">
              <template #default="{ row }">
                <el-select v-model="row.column_type" size="small" style="width:160px" filterable allow-create>
                  <el-option v-for="t in COLUMN_TYPES" :key="t" :label="t" :value="t" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column prop="column_default" label="默认值" width="100">
              <template #default="{ row }"><el-input v-model="row.column_default" size="small" placeholder="可选" /></template>
            </el-table-column>
            <el-table-column label="" width="50">
              <template #default="{ $index }"><el-button text type="danger" size="small" :icon="Delete" @click="removeColumn($index)" /></template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 拍照节点 -->
        <el-tab-pane label="拍照节点" name="photos">
          <div style="margin-bottom:8px">
            <el-button size="small" :icon="Plus" @click="addPhoto">添加节点</el-button>
            <span style="color:#94A3B8;font-size:12px;margin-left:8px">{{ editPhotos.length }} 节点</span>
          </div>
          <el-table :data="editPhotos" size="small" stripe>
            <el-table-column prop="code" label="节点编码" width="160">
              <template #default="{ row }"><el-input v-model="row.code" size="small" placeholder="如 SAMPLE_BEFORE" /></template>
            </el-table-column>
            <el-table-column prop="label" label="节点标签" min-width="250">
              <template #default="{ row }"><el-input v-model="row.label" size="small" placeholder="如 实验前样品及标签" /></template>
            </el-table-column>
            <el-table-column prop="required" label="必填" width="60">
              <template #default="{ row }"><el-checkbox v-model="row.required" size="small" /></template>
            </el-table-column>
            <el-table-column label="" width="50">
              <template #default="{ $index }"><el-button text type="danger" size="small" :icon="Delete" @click="removePhoto($index)" /></template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 预检查项 -->
        <el-tab-pane label="预检项" name="prechecks">
          <div style="margin-bottom:8px">
            <el-button size="small" :icon="Plus" @click="addPrecheck">添加预检</el-button>
            <span style="color:#94A3B8;font-size:12px;margin-left:8px">{{ editPrechecks.length }} 项</span>
          </div>
          <el-table :data="editPrechecks" size="small" stripe>
            <el-table-column prop="label" label="检查项标签" min-width="400">
              <template #default="{ row }"><el-input v-model="row.label" size="small" placeholder="如 设备校准证书在有效期内" /></template>
            </el-table-column>
            <el-table-column label="" width="50">
              <template #default="{ $index }"><el-button text type="danger" size="small" :icon="Delete" @click="removePrecheck($index)" /></template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="editorVisible = false">取消</el-button>
        <el-button type="primary" :loading="editorSaving" @click="saveEditor">💾 保存配置</el-button>
      </template>
    </el-dialog>

    <!-- ====== 新建版本对话框 ====== -->
    <el-dialog v-model="createDialogVisible" title="新建配置版本" width="520px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="实验编码"><el-input :model-value="createForm.experiment_code" disabled /></el-form-item>
        <el-form-item label="版本号" required><el-input v-model="createForm.version" placeholder="如 V2.0, A/1" /></el-form-item>
        <el-form-item label="实验名称" required><el-input v-model="createForm.experiment_name" /></el-form-item>
        <el-form-item label="方法编号" required><el-input v-model="createForm.method_code" /></el-form-item>
        <el-form-item label="标准"><el-input v-model="createForm.standard" /></el-form-item>
        <el-form-item label="类别"><el-input v-model="createForm.category" /></el-form-item>
        <el-form-item label="生效日期"><el-input v-model="createForm.effective_date" type="date" style="width:100%" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="createForm.note" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreateVersion" :loading="createLoading">创建</el-button>
      </template>
    </el-dialog>

    <!-- ====== 新增检测项目对话框 ====== -->
    <el-dialog v-model="addMethodDialogVisible" title="新增检测项目" width="500px" :close-on-click-modal="false">
      <el-form :model="addMethodForm" label-width="100px">
        <el-form-item label="实验编码" required><el-input v-model="addMethodForm.experiment_code" placeholder="如 I010" /></el-form-item>
        <el-form-item label="实验名称" required><el-input v-model="addMethodForm.experiment_name" /></el-form-item>
        <el-form-item label="方法编号" required><el-input v-model="addMethodForm.method_code" /></el-form-item>
        <el-form-item label="标准"><el-input v-model="addMethodForm.standard" /></el-form-item>
        <el-form-item label="类别"><el-input v-model="addMethodForm.category" /></el-form-item>
        <el-form-item label="实验类型">
          <el-select v-model="addMethodForm.kind" style="width:100%">
            <el-option label="通用 (generic)" value="generic" />
            <el-option label="表面粗糙度 (rough)" value="rough" />
            <el-option label="金瓷结合裂纹 (mc_crack)" value="mc_crack" />
            <el-option label="X射线灰度 (xray)" value="xray" />
            <el-option label="翘曲变形 (warp)" value="warp" />
            <el-option label="热膨胀系数 (cte)" value="cte" />
            <el-option label="耐急冷急热 (shock)" value="shock" />
            <el-option label="弯曲性能 (bend)" value="bend" />
            <el-option label="维氏硬度 (hv)" value="hv" />
            <el-option label="厚度测量 (thickness)" value="thickness" />
            <el-option label="色稳定性 (color)" value="color" />
            <el-option label="固定义齿综合 (fixed_denture)" value="fixed_denture" />
            <el-option label="活动义齿综合 (removable_denture)" value="removable_denture" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addMethodDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddMethod" :loading="addMethodLoading">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { max-width: 1300px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
