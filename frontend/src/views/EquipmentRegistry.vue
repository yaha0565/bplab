<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'
import { Search, Plus, Delete } from '@element-plus/icons-vue'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const canManage = computed(() => user.role === '管理员' || user.role === '样品管理员')

const equipment = ref([])
const loading = ref(true)
const searchText = ref('')

// 新增对话框
const dialogVisible = ref(false)
const saving = ref(false)
const form = ref({
  management_no: '', equipment_name: '', model: '',
  measuring_range: '', manufacturer: '', serial_no: '',
  purchase_time: '', calibration_time: '', responsible: '',
  equipment_class: '', lifecycle_status: '正常', notes: '',
})

async function loadEquipment() {
  loading.value = true
  try {
    const { data } = await request.get('/equipment', { params: { search: searchText.value || undefined, limit: 200 } })
    equipment.value = data
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  form.value = {
    management_no: '', equipment_name: '', model: '',
    measuring_range: '', manufacturer: '', serial_no: '',
    purchase_time: '', calibration_time: '', responsible: '',
    equipment_class: '', lifecycle_status: '正常', notes: '',
  }
  dialogVisible.value = true
}

async function handleAdd() {
  const f = form.value
  if (!f.management_no) { ElMessage.warning('请输入管理编号'); return }
  if (!f.equipment_name) { ElMessage.warning('请输入设备名称'); return }

  saving.value = true
  try {
    await request.post('/equipment', {
      management_no: f.management_no,
      equipment_name: f.equipment_name,
      model: f.model || null,
      measuring_range: f.measuring_range || null,
      manufacturer: f.manufacturer || null,
      serial_no: f.serial_no || null,
      purchase_time: f.purchase_time || null,
      calibration_time: f.calibration_time || null,
      responsible: f.responsible || null,
      equipment_class: f.equipment_class || null,
      lifecycle_status: f.lifecycle_status || '正常',
      notes: f.notes || null,
    })
    ElMessage.success('设备添加成功')
    dialogVisible.value = false
    loadEquipment()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(item) {
  try {
    await ElMessageBox.confirm(
      `确定要删除设备「${item.management_no} ${item.equipment_name}」吗？`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await request.delete(`/equipment/${item.management_no}`)
    ElMessage.success('设备已删除')
    loadEquipment()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(loadEquipment)

function getLifecycleType(status) {
  const map = { '正常': 'success', '启用': 'success', '停用': 'warning', '维修': 'danger', '报废': 'info' }
  return map[status] || 'info'
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>设备库</h1>
      <div style="display:flex;gap:12px">
        <el-button v-if="canManage" type="primary" :icon="Plus" @click="showAddDialog">新增设备</el-button>
        <el-input
          v-model="searchText"
          placeholder="搜索设备名称/编号/型号..."
          style="width:300px"
          clearable
          @input="loadEquipment"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
    </div>

    <el-card>
      <el-table :data="equipment" v-loading="loading" stripe empty-text="暂无数据" max-height="600">
        <el-table-column prop="management_no" label="管理编号" width="130" />
        <el-table-column prop="equipment_name" label="设备名称" min-width="180" />
        <el-table-column prop="model" label="型号" width="150" />
        <el-table-column prop="measuring_range" label="测量范围" width="150" />
        <el-table-column prop="manufacturer" label="制造商" width="150" />
        <el-table-column prop="serial_no" label="序列号" width="130" />
        <el-table-column prop="equipment_class" label="分类" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.equipment_class }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="calibration_time" label="校准日期" width="120" />
        <el-table-column prop="responsible" label="负责人" width="100" />
        <el-table-column prop="lifecycle_status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getLifecycleType(row.lifecycle_status)" size="small">{{ row.lifecycle_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="canManage" label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button text type="danger" :icon="Delete" @click.stop="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增设备对话框 -->
    <el-dialog v-model="dialogVisible" title="新增设备" width="600px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="管理编号" required>
              <el-input v-model="form.management_no" placeholder="如 EQ-2026-001" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设备名称" required>
              <el-input v-model="form.equipment_name" placeholder="如 万能试验机" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="型号">
              <el-input v-model="form.model" placeholder="如 Instron 5982" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="序列号">
              <el-input v-model="form.serial_no" placeholder="序列号" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="测量范围">
              <el-input v-model="form.measuring_range" placeholder="如 0-100kN" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="制造商">
              <el-input v-model="form.manufacturer" placeholder="如 Instron" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="分类">
              <el-input v-model="form.equipment_class" placeholder="如 力学、金相" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.lifecycle_status" style="width:100%">
                <el-option label="正常" value="正常" />
                <el-option label="停用" value="停用" />
                <el-option label="维修" value="维修" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="采购日期">
              <el-input v-model="form.purchase_time" type="date" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="校准日期">
              <el-input v-model="form.calibration_time" type="date" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="负责人">
          <el-input v-model="form.responsible" placeholder="负责人用户名" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAdd" :loading="saving">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { max-width: 1600px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
