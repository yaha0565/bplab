<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'
import { Plus, Delete } from '@element-plus/icons-vue'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const canManage = computed(() => user.role === '管理员' || user.role === '样品管理员')

const organizations = ref([])
const loading = ref(true)
const dialogVisible = ref(false)
const formRef = ref(null)

const form = reactive({
  org_name: '',
  short_name: '',
  is_client: true,
  is_manufacturer: false,
  contact: '',
  phone: '',
  address: '',
})

onMounted(async () => {
  try {
    const { data } = await request.get('/organizations', { params: { limit: 500 } })
    organizations.value = data
  } finally {
    loading.value = false
  }
})

async function handleCreate() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    await request.post('/organizations', form)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    Object.assign(form, { org_name: '', short_name: '', is_client: true, is_manufacturer: false, contact: '', phone: '', address: '' })
    const { data } = await request.get('/organizations', { params: { limit: 500 } })
    organizations.value = data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
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
    const { data } = await request.get('/organizations', { params: { limit: 500 } })
    organizations.value = data
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>单位信息库</h1>
      <el-button type="primary" :icon="Plus" @click="dialogVisible = true">新建单位</el-button>
    </div>

    <el-card>
      <el-table :data="organizations" v-loading="loading" stripe empty-text="暂无数据">
        <el-table-column prop="org_code" label="单位代码" width="120" />
        <el-table-column prop="org_name" label="单位名称" min-width="200" />
        <el-table-column prop="short_name" label="简称" width="120" />
        <el-table-column label="类型" width="160">
          <template #default="{ row }">
            <el-tag v-if="row.is_client" size="small" type="primary" style="margin-right:4px">客户</el-tag>
            <el-tag v-if="row.is_manufacturer" size="small" type="success" style="margin-right:4px">生产商</el-tag>
            <el-tag v-if="row.is_contract_manufacturer" size="small" type="warning">合同制造</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="contact" label="联系人" width="100" />
        <el-table-column prop="phone" label="电话" width="140" />
        <el-table-column prop="address" label="地址" min-width="200" />
        <el-table-column v-if="canManage" label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button text type="danger" :icon="Delete" @click.stop="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新建单位" width="500px">
      <el-form ref="formRef" :model="form" label-width="80px">
        <el-form-item label="单位名称" prop="org_name" :rules="[{required:true,message:'请输入单位名称'}]">
          <el-input v-model="form.org_name" />
        </el-form-item>
        <el-form-item label="简称" prop="short_name">
          <el-input v-model="form.short_name" />
        </el-form-item>
        <el-form-item label="单位类型">
          <el-checkbox v-model="form.is_client">客户</el-checkbox>
          <el-checkbox v-model="form.is_manufacturer">生产商</el-checkbox>
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="form.contact" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.address" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { max-width: 1300px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
