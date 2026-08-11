<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const canManage = computed(() => user.role === '管理员' || user.role === '样品管理员')

const organizations = ref([])
const loading = ref(true)
const dialogVisible = ref(false)
const editMode = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const defaultForm = () => ({
  org_code: '',
  org_name: '',
  short_name: '',
  is_client: true,
  is_manufacturer: false,
  is_contract_manufacturer: false,
  address: '',
  contact: '',
  phone: '',
  credit_code: '',
  notes: '',
})

const form = reactive(defaultForm())

const dialogTitle = computed(() => editMode.value ? '编辑单位' : '新建单位')

onMounted(async () => {
  await loadData()
})

async function loadData() {
  loading.value = true
  try {
    const { data } = await request.get('/organizations', { params: { limit: 500 } })
    organizations.value = data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editMode.value = false
  editingId.value = null
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

function openEdit(org) {
  editMode.value = true
  editingId.value = org.id
  Object.assign(form, {
    org_code: org.org_code || '',
    org_name: org.org_name || '',
    short_name: org.short_name || '',
    is_client: org.is_client,
    is_manufacturer: org.is_manufacturer,
    is_contract_manufacturer: org.is_contract_manufacturer,
    address: org.address || '',
    contact: org.contact || '',
    phone: org.phone || '',
    credit_code: org.credit_code || '',
    notes: org.notes || '',
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (editMode.value) {
      await request.put(`/organizations/${editingId.value}`, form)
      ElMessage.success('更新成功')
    } else {
      await request.post('/organizations', form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || (editMode.value ? '更新失败' : '创建失败'))
  }
}

async function handleDelete(org) {
  try {
    await ElMessageBox.confirm(
      `确定要删除单位「${org.org_name}」吗？`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await request.delete(`/organizations/${org.id}`)
    ElMessage.success('单位已删除')
    await loadData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>单位信息库</h1>
      <el-button type="primary" :icon="Plus" @click="openCreate">新建单位</el-button>
    </div>

    <el-card>
      <el-table :data="organizations" v-loading="loading" stripe empty-text="暂无数据">
        <el-table-column prop="org_code" label="单位编号" width="120" />
        <el-table-column prop="org_name" label="单位名称" min-width="180" />
        <el-table-column prop="short_name" label="单位简称" width="100" />
        <el-table-column label="类型" width="180">
          <template #default="{ row }">
            <el-tag v-if="row.is_client" size="small" type="primary" style="margin-right:4px">委托客户</el-tag>
            <el-tag v-if="row.is_manufacturer" size="small" type="success" style="margin-right:4px">生产单位</el-tag>
            <el-tag v-if="row.is_contract_manufacturer" size="small" type="warning">受委托生产企业</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="contact" label="联系人" width="100" />
        <el-table-column prop="phone" label="联系电话" width="130" />
        <el-table-column prop="credit_code" label="统一社会信用代码" width="180" />
        <el-table-column prop="address" label="地址" min-width="180" />
        <el-table-column prop="notes" label="备注" min-width="120" />
        <el-table-column v-if="canManage" label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" :icon="Edit" @click.stop="openEdit(row)">编辑</el-button>
            <el-button text type="danger" :icon="Delete" @click.stop="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form ref="formRef" :model="form" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="单位编号" prop="org_code">
              <el-input v-model="form.org_code" placeholder="自动或手动输入" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="委托客户">
              <el-switch v-model="form.is_client" active-text="是" inactive-text="否" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="地址" prop="address">
              <el-input v-model="form.address" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="统一社会信用代码" prop="credit_code">
              <el-input v-model="form.credit_code" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="单位名称" prop="org_name" :rules="[{required:true,message:'请输入单位名称'}]">
              <el-input v-model="form.org_name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="生产单位">
              <el-switch v-model="form.is_manufacturer" active-text="是" inactive-text="否" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="联系人" prop="contact">
              <el-input v-model="form.contact" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="单位简称" prop="short_name">
              <el-input v-model="form.short_name" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="受委托生产企业">
              <el-switch v-model="form.is_contract_manufacturer" active-text="是" inactive-text="否" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系电话" prop="phone">
              <el-input v-model="form.phone" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="24">
            <el-form-item label="备注" prop="notes">
              <el-input v-model="form.notes" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { max-width: 1500px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
