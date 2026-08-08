<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Box, Check, List } from '@element-plus/icons-vue'
import request from '../utils/request'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const isKeeper = user.role === '样品管理员' || user.role === '管理员'
const isTester = user.role === '实验员'

const loading = ref(false)
const list = ref([])
const pendingList = ref([])
const activeTab = ref(isKeeper ? 'pending' : 'loan')

// ── 借出 ──
const showLoan = ref(false)
const loanForm = reactive({ package_no: '', sample_nos: [], detection_location: '', purpose: '实验检测', issue_note: '' })
const loanSampleInput = ref('')
const loanError = ref('')
const loanSubmitting = ref(false)

function addSample() {
  const v = loanSampleInput.value.trim()
  if (v && !loanForm.sample_nos.includes(v)) { loanForm.sample_nos.push(v); loanSampleInput.value = '' }
}

// ── 归还 ──
const showReturn = ref(false)
const returnForm = reactive({ package_no: '', sample_nos: [], detection_location: '', purpose: '实验检测', issue_note: '' })
const returnSampleInput = ref('')
const returnError = ref('')
const returnSubmitting = ref(false)

function addReturnSample() {
  const v = returnSampleInput.value.trim()
  if (v && !returnForm.sample_nos.includes(v)) { returnForm.sample_nos.push(v); returnSampleInput.value = '' }
}

onMounted(() => {
  loadList()
  if (isKeeper) loadPending()
})

async function loadList() {
  loading.value = true
  try {
    const { data } = await request.get('/returns', { params: { limit: 200 } })
    list.value = data
  } catch { ElMessage.warning('加载记录失败') } finally { loading.value = false }
}

async function loadPending() {
  try {
    const { data } = await request.get('/returns/pending')
    pendingList.value = data
  } catch { /* ignore */ }
}

// ── 借出 ──
async function submitLoan() {
  if (!loanForm.package_no.trim() || loanForm.sample_nos.length === 0) {
    loanError.value = '请填写任务包编号并至少添加一个样品'; return
  }
  loanError.value = ''
  loanSubmitting.value = true
  try {
    await request.post('/returns/loan', loanForm)
    ElMessage.success('借出登记成功')
    showLoan.value = false
    Object.assign(loanForm, { package_no: '', sample_nos: [], detection_location: '', purpose: '实验检测', issue_note: '' })
    loanSampleInput.value = ''
    loadList()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '登记失败') } finally { loanSubmitting.value = false }
}

// ── 归还 ──
async function submitReturn() {
  if (!returnForm.package_no.trim() || returnForm.sample_nos.length === 0) {
    returnError.value = '请填写任务包编号并至少添加一个样品'; return
  }
  returnError.value = ''
  returnSubmitting.value = true
  try {
    await request.post('/returns/submit', returnForm)
    ElMessage.success('归还已提交，待样品管理员确认')
    showReturn.value = false
    Object.assign(returnForm, { package_no: '', sample_nos: [], detection_location: '', purpose: '实验检测', issue_note: '' })
    returnSampleInput.value = ''
    loadList()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '提交失败') } finally { returnSubmitting.value = false }
}

// ── 确认 ──
async function confirmReturn(row) {
  try {
    await request.put(`/returns/${row.id}/confirm`, { return_condition: '完好', confirmed_location: '' })
    ElMessage.success(`样品 ${row.sample_no} 回库已确认`)
    loadList(); loadPending()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '确认失败') }
}

function statusTag(s) {
  const map = { '未归还': 'danger', '已归还': 'warning', '已确认': 'success' }
  return map[s] || 'info'
}
function formatDate(d) { return d ? new Date(d).toLocaleString('zh-CN') : '—' }
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2><el-icon><Box /></el-icon> 样品借出与归还</h2>
      <div style="display:flex;gap:8px">
        <el-button v-if="isTester" type="primary" @click="showLoan = true">样品借出</el-button>
        <el-button v-if="isTester" type="warning" @click="showReturn = true">归还提交</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <!-- 样品管理员确认视图 -->
      <el-tab-pane v-if="isKeeper" label="待确认归还" name="pending">
        <el-table :data="pendingList" stripe>
          <el-table-column prop="sample_no" label="样品编号" width="180" />
          <el-table-column prop="sample_name" label="样品名称" width="150" />
          <el-table-column prop="borrower" label="借出人" width="100" />
          <el-table-column label="借出时间" width="170"><template #default="{row}">{{ formatDate(row.borrowed_at) }}</template></el-table-column>
          <el-table-column label="归还时间" width="170"><template #default="{row}">{{ formatDate(row.returned_at) }}</template></el-table-column>
          <el-table-column label="归还状态" width="100"><template #default="{row}"><el-tag type="warning">待确认</el-tag></template></el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{row}">
              <el-button size="small" type="success" @click="confirmReturn(row)">确认回库</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 全部记录 -->
      <el-tab-pane label="全部记录" name="all">
        <el-table :data="list" v-loading="loading" stripe>
          <el-table-column prop="package_no" label="任务包" width="170" />
          <el-table-column prop="sample_no" label="样品编号" width="180" />
          <el-table-column prop="sample_name" label="样品名称" width="150" />
          <el-table-column prop="borrower" label="借用人" width="100" />
          <el-table-column label="借出时间" width="170"><template #default="{row}">{{ formatDate(row.borrowed_at) }}</template></el-table-column>
          <el-table-column label="归还时间" width="170"><template #default="{row}">{{ formatDate(row.returned_at) }}</template></el-table-column>
          <el-table-column label="归还状态" width="100">
            <template #default="{row}"><el-tag :type="statusTag(row.return_status)">{{ row.return_status }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="detection_location" label="检测地点" width="120" />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 样品借出对话框 -->
    <el-dialog v-model="showLoan" title="样品借出登记" width="500px">
      <el-form :model="loanForm" label-width="90px">
        <el-form-item label="任务包编号" required><el-input v-model="loanForm.package_no" placeholder="如 BP20260809-001" /></el-form-item>
        <el-form-item label="样品编号" required>
          <div style="display:flex;gap:8px;width:100%">
            <el-input v-model="loanSampleInput" placeholder="输入样品编号后添加" @keyup.enter="addSample" />
            <el-button @click="addSample">添加</el-button>
          </div>
          <el-tag v-for="(s, i) in loanForm.sample_nos" :key="s" closable @close="loanForm.sample_nos.splice(i,1)" style="margin:4px 4px 0 0">{{ s }}</el-tag>
        </el-form-item>
        <el-form-item label="检测地点"><el-input v-model="loanForm.detection_location" /></el-form-item>
        <el-form-item label="用途"><el-select v-model="loanForm.purpose" style="width:100%">
          <el-option label="实验检测" value="实验检测" /><el-option label="校准" value="校准" /><el-option label="展示" value="展示" /><el-option label="其他" value="其他" />
        </el-select></el-form-item>
        <el-form-item label="备注"><el-input v-model="loanForm.issue_note" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <p v-if="loanError" style="color:#f56c6c">{{ loanError }}</p>
      <template #footer>
        <el-button @click="showLoan = false">取消</el-button>
        <el-button type="primary" :loading="loanSubmitting" @click="submitLoan">确认借出</el-button>
      </template>
    </el-dialog>

    <!-- 归还提交对话框 -->
    <el-dialog v-model="showReturn" title="样品归还提交" width="500px">
      <el-form :model="returnForm" label-width="90px">
        <el-form-item label="任务包编号" required><el-input v-model="returnForm.package_no" /></el-form-item>
        <el-form-item label="归还样品" required>
          <div style="display:flex;gap:8px;width:100%">
            <el-input v-model="returnSampleInput" placeholder="输入样品编号" @keyup.enter="addReturnSample" />
            <el-button @click="addReturnSample">添加</el-button>
          </div>
          <el-tag v-for="(s, i) in returnForm.sample_nos" :key="s" closable @close="returnForm.sample_nos.splice(i,1)" style="margin:4px 4px 0 0">{{ s }}</el-tag>
        </el-form-item>
        <el-form-item label="检测地点"><el-input v-model="returnForm.detection_location" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="returnForm.issue_note" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <p v-if="returnError" style="color:#f56c6c">{{ returnError }}</p>
      <template #footer>
        <el-button @click="showReturn = false">取消</el-button>
        <el-button type="primary" :loading="returnSubmitting" @click="submitReturn">提交归还</el-button>
      </template>
    </el-dialog>
  </div>
</template>
