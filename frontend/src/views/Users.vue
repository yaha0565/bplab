<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'

const currentUser = JSON.parse(localStorage.getItem('user') || '{}')
const users = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新建用户')
const formRef = ref(null)

const form = reactive({
  username: '',
  display_name: '',
  password: '',
  role: '实验员',
})

const roles = ['管理员', '样品管理员', '实验员', '复核员', '质量负责人']

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 8, message: '密码至少8位', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

async function loadUsers() {
  loading.value = true
  try {
    const { data } = await request.get('/users')
    users.value = data
  } finally {
    loading.value = false
  }
}

function showCreate() {
  dialogTitle.value = '新建用户'
  Object.assign(form, { username: '', display_name: '', password: '', role: '实验员' })
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    await request.post('/users', { ...form })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    loadUsers()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  }
}

async function resetPassword(username) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新密码', '重置密码', {
      inputType: 'password',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await request.put(`/users/${username}/password`, { new_password: value })
    ElMessage.success('密码已重置')
  } catch { /* cancelled */ }
}

async function changeRole(username, currentRole) {
  try {
    const { value } = await ElMessageBox.prompt(
      `当前角色：${currentRole}\n\n请输入新角色（管理员 / 样品管理员 / 实验员 / 复核员 / 质量负责人）`,
      '修改角色',
      {
        inputValue: currentRole,
        inputValidator: (v) => roles.includes(v) || '无效的角色名称',
        confirmButtonText: '确定',
        cancelButtonText: '取消',
      }
    )
    await request.put(`/users/${username}/role`, { role: value })
    ElMessage.success('角色已更新')
    loadUsers()
  } catch { /* cancelled */ }
}

async function deleteUser(username) {
  if (username === currentUser.username) {
    ElMessage.warning('不能删除自己的账号')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要删除用户「${username}」吗？该用户关联的任务包分配将被解除。此操作不可撤销。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await request.delete(`/users/${username}`)
    ElMessage.success(`用户 ${username} 已删除`)
    loadUsers()
  } catch { /* cancelled */ }
}

onMounted(loadUsers)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>用户与权限</h1>
      <el-button type="primary" :icon="Plus" @click="showCreate">新建用户</el-button>
    </div>

    <el-card>
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="username" label="用户名" width="160" />
        <el-table-column prop="display_name" label="显示名称" width="160" />
        <el-table-column prop="role" label="角色" width="140">
          <template #default="{ row }">
            <el-tag :type="row.role === '管理员' ? 'danger' : row.role === '实验员' ? 'primary' : 'info'" size="small">
              {{ row.role }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'danger'" size="small">
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" />
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button text type="primary" :icon="Edit" @click="resetPassword(row.username)">重置密码</el-button>
            <el-button text type="warning" :icon="Edit" @click="changeRole(row.username, row.role)">改角色</el-button>
            <el-button text type="danger" :icon="Delete" @click="deleteUser(row.username)" :disabled="row.username === currentUser.username">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建用户对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="英文用户名" />
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="form.display_name" placeholder="中文姓名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="至少8位" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" style="width:100%">
            <el-option v-for="r in roles" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; }
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
