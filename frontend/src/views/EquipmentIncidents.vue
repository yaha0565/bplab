<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Warning, Search, CircleCheck, Timer } from '@element-plus/icons-vue'
import request from '../utils/request'

const loading = ref(false)
const list = ref([])
const dialogVisible = ref(false)
const current = ref(null)
const actions = ref([])
const searchText = ref('')

// ── 报告故障表单 ──
const reportForm = reactive({
  task_no: '', equipment_no: '', fault_type: '', fault_description: '',
  error_code: '', current_stage: '', collected_data: '', sample_condition: '',
  risk_types: [], immediate_actions: [], involved_samples: '',
})
const riskOptions = ['数据丢失风险', '样品损坏风险', '人员安全风险', '环境污染风险', '进度延误风险']
const actionOptions = ['立即停止实验', '切断电源', '撤离人员', '隔离区域', '通知主管', '保存已采集数据']

// ── 隔离/评估表单 ──
const actionForm = reactive({
  comment: '', isolation_location: '', storage_requirements: '',
  sample_validity: '', quality_note: '', backup_equipment_no: '',
  performance_check_result: '', admin_note: '', recovery_route: '',
})

const submitting = ref(false)
const user = JSON.parse(localStorage.getItem('user') || '{}')

onMounted(() => { loadList() })

async function loadList() {
  loading.value = true
  try {
    const { data } = await request.get('/incidents', { params: { search: searchText.value || undefined } })
    list.value = data
  } catch { ElMessage.warning('加载故障记录失败') } finally { loading.value = false }
}

async function openDetail(row) {
  try {
    const { data } = await request.get(`/incidents/${row.incident_no}`)
    current.value = data.incident
    actions.value = data.actions || []
    dialogVisible.value = true
  } catch { ElMessage.error('加载详情失败') }
}

// ── 报告故障 ──
const showReport = ref(false)
const reportError = ref('')
async function submitReport() {
  if (!reportForm.task_no || !reportForm.equipment_no || !reportForm.fault_description) {
    reportError.value = '请填写任务编号、设备编号和故障描述'
    return
  }
  reportError.value = ''
  submitting.value = true
  try {
    const res = await request.post('/incidents', {
      ...reportForm,
      risk_types: reportForm.risk_types,
      immediate_actions: reportForm.immediate_actions,
    })
    ElMessage.success(`故障已报告: ${res.data.incident_no}`)
    showReport.value = false
    resetReportForm()
    loadList()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '报告失败') } finally { submitting.value = false }
}

function resetReportForm() {
  Object.assign(reportForm, { task_no: '', equipment_no: '', fault_type: '', fault_description: '', error_code: '', current_stage: '', collected_data: '', sample_condition: '', risk_types: [], immediate_actions: [], involved_samples: '' })
}

// ── 隔离/评估/批准操作 ──
async function doAction(incidentNo, action) {
  const titleMap = { isolate: '确认样品隔离', assess: '质量评估', approve: '技术批准' }
  const title = titleMap[action] || action

  try {
    if (action === 'isolate') {
      await ElMessageBox.prompt('隔离位置', title, { confirmButtonText: '确认', inputPlaceholder: '样品隔离存放位置' })
        .then(async ({ value }) => {
          if (!value) throw new Error('请输入隔离位置')
          await request.put(`/incidents/${incidentNo}/isolate`, { isolation_location: value, storage_requirements: '', note: '' })
        })
    } else if (action === 'assess') {
      await ElMessageBox.prompt('样品有效性评估结论', title, {
        confirmButtonText: '提交',
        inputType: 'textarea',
        inputPlaceholder: '描述样品有效性、影响范围和恢复建议',
      }).then(async ({ value }) => {
        if (!value) throw new Error('请输入评估结论')
        await request.put(`/incidents/${incidentNo}/assess`, { sample_validity: '样品有效-可继续使用原设备重做', quality_note: value })
      })
    } else if (action === 'approve') {
      await ElMessageBox.confirm('确认批准故障处置恢复方案？', title, {
        confirmButtonText: '批准',
        cancelButtonText: '取消',
        type: 'warning',
      }).then(async () => {
        await request.put(`/incidents/${incidentNo}/approve`, {
          recovery_route: '使用原设备重做', admin_note: '', backup_equipment_no: '', performance_check_result: '',
        })
      })
    }
    ElMessage.success(`${title}操作成功`)
    loadList()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(typeof e === 'string' ? e : (e.response?.data?.detail || '操作失败'))
  }
}

function statusTag(s) {
  const map = { '报告': 'danger', '已隔离': 'warning', '已评估': '', '已批准恢复': 'success', '已关闭': 'info' }
  return map[s] || 'info'
}
function formatDate(d) { return d ? new Date(d).toLocaleString('zh-CN') : '—' }
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2><el-icon><Warning /></el-icon> 设备故障处置</h2>
      <el-button type="primary" @click="showReport = true">报告设备故障</el-button>
    </div>

    <!-- 搜索 -->
    <el-input v-model="searchText" placeholder="搜索故障编号或任务编号" clearable @clear="loadList" @keyup.enter="loadList" style="width:320px;margin-bottom:16px">
      <template #prefix><el-icon><Search /></el-icon></template>
    </el-input>

    <!-- 列表 -->
    <el-table :data="list" v-loading="loading" stripe @row-click="openDetail" style="cursor:pointer">
      <el-table-column prop="incident_no" label="故障编号" width="180" />
      <el-table-column prop="task_no" label="关联任务" width="150" />
      <el-table-column prop="equipment_no" label="设备编号" width="150" />
      <el-table-column prop="fault_type" label="故障类型" width="120" />
      <el-table-column prop="fault_description" label="故障描述" min-width="200" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }"><el-tag :type="statusTag(row.status)">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="created_at" label="报告时间" width="170">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="快捷操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status==='报告' && (user.role==='样品管理员' || user.role==='管理员')" size="small" type="warning" @click.stop="doAction(row.incident_no,'isolate')">隔离</el-button>
          <el-button v-if="row.status==='已隔离' && (user.role==='质量负责人' || user.role==='管理员')" size="small" @click.stop="doAction(row.incident_no,'assess')">评估</el-button>
          <el-button v-if="row.status==='已评估' && (user.role==='管理员')" size="small" type="success" @click.stop="doAction(row.incident_no,'approve')">批准</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 详情对话框 -->
    <el-dialog v-model="dialogVisible" title="故障详情" width="700px">
      <template v-if="current">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="故障编号">{{ current.incident_no }}</el-descriptions-item>
          <el-descriptions-item label="状态"><el-tag :type="statusTag(current.status)">{{ current.status }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="关联任务">{{ current.task_no }}</el-descriptions-item>
          <el-descriptions-item label="设备编号">{{ current.equipment_no }}</el-descriptions-item>
          <el-descriptions-item label="故障类型">{{ current.fault_type }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ current.created_by }}</el-descriptions-item>
          <el-descriptions-item label="故障描述" :span="2">{{ current.fault_description }}</el-descriptions-item>
        </el-descriptions>
        <h4 style="margin-top:16px">操作历史</h4>
        <el-timeline v-if="actions.length">
          <el-timeline-item v-for="a in actions" :key="a.id" :timestamp="formatDate(a.created_at)" placement="top">
            <strong>{{ a.action }}</strong> — {{ a.actor }}<br/>
            <span v-if="a.comment">{{ a.comment }}</span>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无操作记录" :image-size="60" />
      </template>
    </el-dialog>

    <!-- 报告故障对话框 -->
    <el-dialog v-model="showReport" title="报告设备故障" width="600px">
      <el-form :model="reportForm" label-width="100px">
        <el-form-item label="任务编号" required><el-input v-model="reportForm.task_no" placeholder="如 BP20260809-001-T01" /></el-form-item>
        <el-form-item label="设备编号" required><el-input v-model="reportForm.equipment_no" placeholder="故障设备编号" /></el-form-item>
        <el-form-item label="故障类型"><el-select v-model="reportForm.fault_type" placeholder="选择故障类型" clearable style="width:100%">
          <el-option label="机械故障" value="机械故障" /><el-option label="电气故障" value="电气故障" />
          <el-option label="软件故障" value="软件故障" /><el-option label="传感器故障" value="传感器故障" />
          <el-option label="校准偏差" value="校准偏差" /><el-option label="其他" value="其他" />
        </el-select></el-form-item>
        <el-form-item label="故障描述" required><el-input v-model="reportForm.fault_description" type="textarea" :rows="3" placeholder="详细描述故障现象" /></el-form-item>
        <el-form-item label="当前阶段"><el-input v-model="reportForm.current_stage" placeholder="实验进行到哪一步" /></el-form-item>
        <el-form-item label="风险类型"><el-checkbox-group v-model="reportForm.risk_types">
          <el-checkbox v-for="r in riskOptions" :key="r" :label="r">{{ r }}</el-checkbox>
        </el-checkbox-group></el-form-item>
        <el-form-item label="紧急措施"><el-checkbox-group v-model="reportForm.immediate_actions">
          <el-checkbox v-for="a in actionOptions" :key="a" :label="a">{{ a }}</el-checkbox>
        </el-checkbox-group></el-form-item>
        <el-form-item label="样品状况"><el-input v-model="reportForm.sample_condition" placeholder="样品是否受影响" /></el-form-item>
      </el-form>
      <p v-if="reportError" style="color:#f56c6c">{{ reportError }}</p>
      <template #footer>
        <el-button @click="showReport = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitReport">提交报告</el-button>
      </template>
    </el-dialog>
  </div>
</template>
