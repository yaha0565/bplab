<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ChatLineSquare, Search } from '@element-plus/icons-vue'
import request from '../utils/request'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const loading = ref(false)
const list = ref([])
const dialogVisible = ref(false)
const current = ref(null)
const actions = ref([])
const submitting = ref(false)

// ── 登记表单 ──
const showRegister = ref(false)
const registerForm = reactive({
  report_no: '', client_name: '', contact: '', description: '',
  evidence_note: '', disputed_items: '', involved_samples: '', application_channel: '',
})
const registerError = ref('')

onMounted(() => { loadList() })

async function loadList() {
  loading.value = true
  try {
    const { data } = await request.get('/objections')
    list.value = data
  } catch { ElMessage.warning('加载异议列表失败') } finally { loading.value = false }
}

async function openDetail(row) {
  try {
    const { data } = await request.get(`/objections/${row.objection_no}`)
    current.value = data.objection
    actions.value = data.actions || []
    dialogVisible.value = true
  } catch { ElMessage.error('加载详情失败') }
}

async function submitRegister() {
  if (!registerForm.report_no || !registerForm.description.trim() || !registerForm.disputed_items.trim()) {
    registerError.value = '请填写报告编号、异议内容和争议检测项目'
    return
  }
  registerError.value = ''
  submitting.value = true
  try {
    const res = await request.post('/objections', registerForm)
    ElMessage.success(`异议已登记: ${res.data.objection_no}`)
    showRegister.value = false
    Object.assign(registerForm, { report_no: '', client_name: '', contact: '', description: '', evidence_note: '', disputed_items: '', involved_samples: '', application_channel: '' })
    loadList()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '登记失败') } finally { submitting.value = false }
}

// ── 调查 ──
async function doInvestigate(ono) {
  try {
    const { value: pathway } = await ElMessageBox.confirm('请选择调查结论方向', '质量调查', {
      confirmButtonText: '是我方问题', cancelButtonText: '样品问题',
      distinguishCancelAndClose: true, type: 'warning',
    }).catch(e => e)  // 'confirm'/'cancel'/'close'
    if (pathway === 'close') return
    const isOurFault = pathway === 'confirm' ? '是我方问题' : '样品问题'

    const { value: investigation } = await ElMessageBox.prompt('调查过程描述', '质量调查', { inputType: 'textarea' })
    if (!investigation) return
    const { value: traceConclusion } = await ElMessageBox.prompt('追溯结论', '质量调查', { inputType: 'textarea' })
    if (!traceConclusion) return

    await request.put(`/objections/${ono}/investigate`, {
      pathway: isOurFault, investigation, trace_conclusion: traceConclusion,
    })
    ElMessage.success('调查结论已提交')
    loadList()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(typeof e === 'string' ? e : (e.response?.data?.detail || '操作失败'))
  }
}

// ── 重测决定 ──
async function doRetestDecision(ono) {
  try {
    const need = await ElMessageBox.confirm('客户是否需要重测？', '重测决定', {
      confirmButtonText: '需要重测', cancelButtonText: '不需要重测', type: 'warning',
    })
    await request.put(`/objections/${ono}/retest-decision`, { decision: '需要重测', note: '' })
    ElMessage.success('客户重测决定已记录')
    loadList()
  } catch (e) {
    if (e === 'cancel') {
      await request.put(`/objections/${ono}/retest-decision`, { decision: '不需要重测', note: '' })
      ElMessage.success('已记录：客户不需要重测')
      loadList()
    } else if (e !== 'close') {
      ElMessage.error(e.response?.data?.detail || '操作失败')
    }
  }
}

// ── 下发重测 ──
async function doDispatchRetest(ono) {
  try {
    const { value: assignee } = await ElMessageBox.prompt('指定实验员用户名', '下发留样重测', { inputPlaceholder: '实验员用户名' })
    if (!assignee) return
    await request.post(`/objections/${ono}/dispatch-retest`, { assignee, selected_sample_nos: [] })
    ElMessage.success('重测任务已下发')
    loadList()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(e.response?.data?.detail || '下发失败')
  }
}

// ── 生成回复 ──
async function doPrepareResponse(ono) {
  try {
    const { value: text } = await ElMessageBox.prompt('异议回复正文', '生成回复单', { inputType: 'textarea', inputPlaceholder: '尊敬的客户：...' })
    if (!text) return
    await request.put(`/objections/${ono}/prepare-response`, { response_text: text, response_method: '' })
    ElMessage.success('回复单已生成')
    loadList()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(e.response?.data?.detail || '生成失败')
  }
}

// ── 发送归档 ──
async function doSend(ono) {
  try {
    await ElMessageBox.confirm('确认发送异议回复并归档？', '发送归档', { confirmButtonText: '确认发送', type: 'warning' })
    await request.put(`/objections/${ono}/send`, { note: '' })
    ElMessage.success('异议已发送并归档')
    loadList()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(e.response?.data?.detail || '发送失败')
  }
}

function statusTag(s) {
  const map = { '调查中': 'danger', '待客户确认重测': 'warning', '待安排重测': '', '重测任务已下发': '', '待异议回复': 'warning', '待发送': '', '已归档': 'success' }
  return map[s] || 'info'
}
function formatDate(d) { return d ? new Date(d).toLocaleString('zh-CN') : '—' }
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2><el-icon><ChatLineSquare /></el-icon> 客户异议管理</h2>
      <el-button v-if="user.role==='样品管理员'" type="primary" @click="showRegister = true">登记客户异议</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe @row-click="openDetail" style="cursor:pointer">
      <el-table-column prop="objection_no" label="异议编号" width="180" />
      <el-table-column prop="report_no" label="关联报告" width="180" />
      <el-table-column prop="client_name" label="客户名称" width="150" />
      <el-table-column prop="description" label="异议描述" min-width="200" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="130">
        <template #default="{ row }"><el-tag :type="statusTag(row.status)">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="created_at" label="登记时间" width="170">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="快捷操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status==='调查中' && (user.role==='质量负责人'||user.role==='管理员')" size="small" type="warning" @click.stop="doInvestigate(row.objection_no)">调查</el-button>
          <el-button v-if="row.status==='待客户确认重测' && (user.role==='样品管理员'||user.role==='管理员')" size="small" @click.stop="doRetestDecision(row.objection_no)">重测决定</el-button>
          <el-button v-if="row.status==='待安排重测' && (user.role==='样品管理员'||user.role==='管理员')" size="small" type="primary" @click.stop="doDispatchRetest(row.objection_no)">下发重测</el-button>
          <el-button v-if="row.status==='待异议回复' && (user.role==='样品管理员'||user.role==='管理员')" size="small" type="success" @click.stop="doPrepareResponse(row.objection_no)">生成回复</el-button>
          <el-button v-if="row.status==='待发送' && (user.role==='样品管理员'||user.role==='管理员')" size="small" type="success" @click.stop="doSend(row.objection_no)">发送归档</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 详情对话框 -->
    <el-dialog v-model="dialogVisible" title="异议详情" width="700px">
      <template v-if="current">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="异议编号">{{ current.objection_no }}</el-descriptions-item>
          <el-descriptions-item label="状态"><el-tag :type="statusTag(current.status)">{{ current.status }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="关联报告">{{ current.report_no }}</el-descriptions-item>
          <el-descriptions-item label="客户名称">{{ current.client_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="争议项目" :span="2">{{ current.disputed_items || '—' }}</el-descriptions-item>
          <el-descriptions-item label="异议描述" :span="2">{{ current.description }}</el-descriptions-item>
          <el-descriptions-item label="调查路径">{{ current.pathway || '—' }}</el-descriptions-item>
          <el-descriptions-item label="追溯结论">{{ current.trace_conclusion || '—' }}</el-descriptions-item>
          <el-descriptions-item label="重测决定">{{ current.customer_retest_decision || '—' }}</el-descriptions-item>
          <el-descriptions-item label="重测任务">{{ current.retest_task_no || '—' }}</el-descriptions-item>
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

    <!-- 登记异议对话框 -->
    <el-dialog v-model="showRegister" title="登记客户异议" width="600px">
      <el-form :model="registerForm" label-width="110px">
        <el-form-item label="报告编号" required><el-input v-model="registerForm.report_no" placeholder="已签发的报告编号" /></el-form-item>
        <el-form-item label="客户名称"><el-input v-model="registerForm.client_name" /></el-form-item>
        <el-form-item label="联系方式"><el-input v-model="registerForm.contact" /></el-form-item>
        <el-form-item label="异议内容" required><el-input v-model="registerForm.description" type="textarea" :rows="3" placeholder="客户对哪些检验结论提出异议" /></el-form-item>
        <el-form-item label="争议检测项目" required><el-input v-model="registerForm.disputed_items" placeholder="多个项目用顿号（、）分隔" /></el-form-item>
        <el-form-item label="涉及样品"><el-input v-model="registerForm.involved_samples" placeholder="样品编号" /></el-form-item>
        <el-form-item label="证明材料"><el-input v-model="registerForm.evidence_note" type="textarea" :rows="2" placeholder="客户提供的证明材料描述" /></el-form-item>
        <el-form-item label="申请途径"><el-select v-model="registerForm.application_channel" clearable style="width:100%">
          <el-option label="电话" value="电话" /><el-option label="邮件" value="邮件" /><el-option label="上门" value="上门" /><el-option label="其他" value="其他" />
        </el-select></el-form-item>
      </el-form>
      <p v-if="registerError" style="color:#f56c6c">{{ registerError }}</p>
      <template #footer>
        <el-button @click="showRegister = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitRegister">提交登记</el-button>
      </template>
    </el-dialog>
  </div>
</template>
