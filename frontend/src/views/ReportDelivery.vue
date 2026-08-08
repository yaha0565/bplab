<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Search } from '@element-plus/icons-vue'
import request from '../utils/request'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const loading = ref(false)
const list = ref([])
const searchNo = ref('')

// 发放表单
const showDeliver = ref(false)
const currentReport = ref('')
const deliverForm = reactive({ delivery_method: '', recipient: '', recipient_contact: '', tracking_no: '', note: '' })
const deliverError = ref('')
const delivering = ref(false)

onMounted(() => { loadList() })

async function loadList() {
  loading.value = true
  try {
    const { data } = await request.get('/reports', { params: { status: '已发布', limit: 100 } })
    list.value = data
  } catch { ElMessage.warning('加载报告列表失败') } finally { loading.value = false }
}

function openDeliver(row) {
  currentReport.value = row.report_no
  Object.assign(deliverForm, { delivery_method: '', recipient: '', recipient_contact: '', tracking_no: '', note: '' })
  deliverError.value = ''
  showDeliver.value = true
}

async function submitDeliver() {
  if (!deliverForm.delivery_method || !deliverForm.recipient.trim()) {
    deliverError.value = '请选择发放方式并填写接收人'; return
  }
  deliverError.value = ''
  delivering.value = true
  try {
    await request.post(`/reports/${currentReport.value}/delivery`, deliverForm)
    ElMessage.success('报告发放已登记')
    showDeliver.value = false
    loadList()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '发放失败') } finally { delivering.value = false }
}

async function doRevoke(row) {
  try {
    await request.post(`/reports/${row.report_no}/revoke`)
    ElMessage.success(`报告 ${row.report_no} 已撤回`)
    loadList()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '撤回失败') }
}

async function searchReport() {
  if (!searchNo.value.trim()) { loadList(); return }
  loading.value = true
  try {
    const { data } = await request.get(`/reports/${searchNo.value.trim()}`)
    list.value = [data]
  } catch { ElMessage.warning('报告未找到') } finally { loading.value = false }
}

function formatDate(d) { return d ? new Date(d).toLocaleString('zh-CN') : '—' }
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2><el-icon><Document /></el-icon> 报告发放管理</h2>
      <el-input v-model="searchNo" placeholder="输入报告编号精确搜索" clearable @keyup.enter="searchReport" style="width:280px">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
    </div>

    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="report_no" label="报告编号" width="200" />
      <el-table-column prop="commission_no" label="委托编号" width="180" />
      <el-table-column prop="tester" label="实验员" width="120" />
      <el-table-column prop="quality_inspector" label="签发人" width="120" />
      <el-table-column label="签发日期" width="120"><template #default="{row}">{{ formatDate(row.publish_date) }}</template></el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{row}"><el-tag type="success">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{row}">
          <el-button v-if="user.role==='样品管理员'||user.role==='管理员'" size="small" type="primary" @click="openDeliver(row)">发放登记</el-button>
          <el-button v-if="user.role==='质量负责人'||user.role==='管理员'" size="small" type="warning" @click="doRevoke(row)">撤回</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 发放登记对话框 -->
    <el-dialog v-model="showDeliver" :title="`报告发放 — ${currentReport}`" width="500px">
      <el-form :model="deliverForm" label-width="90px">
        <el-form-item label="发放方式" required>
          <el-select v-model="deliverForm.delivery_method" style="width:100%">
            <el-option label="自取" value="自取" /><el-option label="邮寄" value="邮寄" />
            <el-option label="电子邮件" value="电子邮件" /><el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="接收人" required><el-input v-model="deliverForm.recipient" placeholder="接收人姓名或单位" /></el-form-item>
        <el-form-item label="联系方式"><el-input v-model="deliverForm.recipient_contact" placeholder="电话/邮箱" /></el-form-item>
        <el-form-item label="快递单号"><el-input v-model="deliverForm.tracking_no" placeholder="邮寄时填写" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="deliverForm.note" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <p v-if="deliverError" style="color:#f56c6c">{{ deliverError }}</p>
      <template #footer>
        <el-button @click="showDeliver = false">取消</el-button>
        <el-button type="primary" :loading="delivering" @click="submitDeliver">确认发放</el-button>
      </template>
    </el-dialog>
  </div>
</template>
