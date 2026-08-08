<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Plus, Search } from '@element-plus/icons-vue'
import request from '../utils/request'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const loading = ref(false)
const list = ref([])
const showCreate = ref(false)
const submitting = ref(false)

const form = reactive({
  task_nos: [], waste_type: '实验废液', waste_name: '', quantity: 0,
  unit: 'mL', hazard_category: '', disposal_method: '', container_no: '', note: '',
})
const formError = ref('')
const taskNoInput = ref('')

function addTaskNo() {
  const v = taskNoInput.value.trim()
  if (v && !form.task_nos.includes(v)) { form.task_nos.push(v); taskNoInput.value = '' }
}
function removeTaskNo(idx) { form.task_nos.splice(idx, 1) }

onMounted(() => { loadList() })

async function loadList() {
  loading.value = true
  try {
    const { data } = await request.get('/hazardous-waste')
    list.value = data
  } catch { ElMessage.warning('加载危废记录失败') } finally { loading.value = false }
}

async function submitCreate() {
  if (form.task_nos.length === 0) { formError.value = '至少关联一个实验任务'; return }
  if (!form.waste_name.trim() || !form.disposal_method.trim() || form.quantity <= 0) {
    formError.value = '危废名称、正数数量和处置方式为必填项'; return
  }
  formError.value = ''
  submitting.value = true
  try {
    const res = await request.post('/hazardous-waste', form)
    ElMessage.success(`危废记录已登记: ${res.data.disposal_no}`)
    showCreate.value = false
    Object.assign(form, { task_nos: [], waste_type: '实验废液', waste_name: '', quantity: 0, unit: 'mL', hazard_category: '', disposal_method: '', container_no: '', note: '' })
    taskNoInput.value = ''
    loadList()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '登记失败') } finally { submitting.value = false }
}

function formatDate(d) { return d ? new Date(d).toLocaleString('zh-CN') : '—' }
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2><el-icon><Delete /></el-icon> 危废处理登记</h2>
      <el-button v-if="user.role==='实验员'" type="primary" @click="showCreate = true"><el-icon><Plus /></el-icon> 登记危废</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="disposal_no" label="处置编号" width="180" />
      <el-table-column prop="waste_name" label="危废名称" width="150" />
      <el-table-column prop="waste_type" label="类型" width="100" />
      <el-table-column label="数量" width="120">
        <template #default="{ row }">{{ row.quantity }} {{ row.unit }}</template>
      </el-table-column>
      <el-table-column prop="hazard_category" label="危险类别" width="120" />
      <el-table-column prop="disposal_method" label="处置方式" min-width="150" show-overflow-tooltip />
      <el-table-column prop="handler" label="处置人" width="100" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }"><el-tag type="info">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column label="发生时间" width="170">
        <template #default="{ row }">{{ formatDate(row.occurred_at) }}</template>
      </el-table-column>
    </el-table>

    <!-- 登记对话框 -->
    <el-dialog v-model="showCreate" title="危废处置登记" width="550px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="关联任务" required>
          <div style="display:flex;gap:8px;width:100%">
            <el-input v-model="taskNoInput" placeholder="输入任务编号后点击添加" @keyup.enter="addTaskNo" />
            <el-button @click="addTaskNo">添加</el-button>
          </div>
          <el-tag v-for="(t, i) in form.task_nos" :key="t" closable @close="removeTaskNo(i)" style="margin:4px 4px 0 0">{{ t }}</el-tag>
        </el-form-item>
        <el-form-item label="危废名称" required><el-input v-model="form.waste_name" placeholder="如：含铬废液" /></el-form-item>
        <el-form-item label="危废类型"><el-select v-model="form.waste_type" style="width:100%">
          <el-option label="实验废液" value="实验废液" /><el-option label="废弃化学品" value="废弃化学品" />
          <el-option label="实验固废" value="实验固废" /><el-option label="废弃样品" value="废弃样品" />
          <el-option label="其他危废" value="其他危废" />
        </el-select></el-form-item>
        <el-form-item label="危险类别"><el-select v-model="form.hazard_category" clearable style="width:100%">
          <el-option label="毒性" value="毒性" /><el-option label="腐蚀性" value="腐蚀性" />
          <el-option label="易燃性" value="易燃性" /><el-option label="反应性" value="反应性" />
          <el-option label="感染性" value="感染性" />
        </el-select></el-form-item>
        <el-form-item label="数量" required>
          <el-input-number v-model="form.quantity" :min="0" :precision="2" style="width:200px" />
          <el-select v-model="form.unit" style="width:100px;margin-left:8px">
            <el-option label="mL" value="mL" /><el-option label="L" value="L" /><el-option label="g" value="g" />
            <el-option label="kg" value="kg" /><el-option label="件" value="件" />
          </el-select>
        </el-form-item>
        <el-form-item label="处置方式" required><el-select v-model="form.disposal_method" style="width:100%">
          <el-option label="委托有资质单位处置" value="委托有资质单位处置" />
          <el-option label="中和处理后排放" value="中和处理后排放" />
          <el-option label="高温焚烧" value="高温焚烧" />
          <el-option label="化学固化填埋" value="化学固化填埋" />
          <el-option label="特殊回收" value="特殊回收" />
        </el-select></el-form-item>
        <el-form-item label="容器编号"><el-input v-model="form.container_no" placeholder="危废暂存容器编号" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.note" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <p v-if="formError" style="color:#f56c6c">{{ formError }}</p>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>
