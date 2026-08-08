<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import request from '../utils/request'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const isAdmin = computed(() => user.role === '管理员')

const signatures = ref([])
const loading = ref(false)

// 上传
const uploadVisible = ref(false)
const uploadLoading = ref(false)
const uploadForm = ref({ file: null, target_username: '' })
const userList = ref([])

onMounted(loadSignatures)

async function loadSignatures() {
  loading.value = true
  try {
    const { data } = await request.get('/signatures')
    signatures.value = data
  } catch { /* ignore */ }
  finally { loading.value = false }
}

async function openUpload() {
  try {
    const { data } = await request.get('/users')
    userList.value = data
  } catch { /* ignore */ }
  uploadForm.value = { file: null, target_username: '' }
  uploadVisible.value = true
}

function handleFileChange(file) {
  uploadForm.value.file = file.raw
}

async function handleUpload() {
  if (!uploadForm.value.file) { ElMessage.warning('请选择签名图片'); return }
  if (!uploadForm.value.target_username) { ElMessage.warning('请选择用户'); return }
  uploadLoading.value = true
  try {
    const fd = new FormData()
    fd.append('file', uploadForm.value.file)
    fd.append('target_username', uploadForm.value.target_username)
    await request.post('/signatures/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    ElMessage.success('签名上传成功')
    uploadVisible.value = false
    loadSignatures()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '上传失败')
  } finally {
    uploadLoading.value = false
  }
}

async function deleteSignature(username) {
  try {
    const { ElMessageBox } = await import('element-plus')
    await ElMessageBox.confirm(`确定删除 ${username} 的签名吗？`, '确认', { type: 'warning' })
    await request.delete(`/signatures/${username}`)
    ElMessage.success('签名已删除')
    loadSignatures()
  } catch { /* cancelled */ }
}

function previewUrl(username) {
  const token = localStorage.getItem('token')
  return `/api/v1/signatures/${username}.png?token=${token}`
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>电子签名管理</h1>
      <el-button v-if="isAdmin" type="primary" :icon="Upload" @click="openUpload">上传签名</el-button>
    </div>

    <el-card>
      <el-table :data="signatures" v-loading="loading" stripe empty-text="暂无数据">
        <el-table-column prop="display_name" label="用户" width="160" />
        <el-table-column prop="username" label="账号" width="140" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="签名状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.has_signature ? 'success' : 'warning'" size="small">
              {{ row.has_signature ? '已上传' : '未上传' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="签名预览" width="200">
          <template #default="{ row }">
            <img v-if="row.has_signature" :src="previewUrl(row.username)" style="max-height:60px;background:#fff;border:1px solid #E2E8F0;border-radius:4px;padding:4px" />
            <span v-else style="color:#94A3B8">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="file_size_kb" label="大小(KB)" width="100" />
        <el-table-column prop="uploaded_at" label="上传时间" width="160" />
        <el-table-column label="操作" width="100" v-if="isAdmin">
          <template #default="{ row }">
            <el-button v-if="row.has_signature" text type="danger" @click="deleteSignature(row.username)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 上传对话框 -->
    <el-dialog v-model="uploadVisible" title="上传电子签名" width="460px">
      <el-form :model="uploadForm" label-width="80px">
        <el-form-item label="用户" required>
          <el-select v-model="uploadForm.target_username" placeholder="选择用户" filterable style="width:100%">
            <el-option v-for="u in userList" :key="u.username" :label="`${u.display_name} (${u.username})`" :value="u.username" />
          </el-select>
        </el-form-item>
        <el-form-item label="签名图片" required>
          <el-upload :auto-upload="false" :limit="1" accept=".png,.jpg,.jpeg" :on-change="handleFileChange" drag>
            <el-icon style="font-size:32px;color:#CBD5E1"><Upload /></el-icon>
            <div style="margin-top:8px;color:#94A3B8">拖拽或点击上传 PNG/JPG</div>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpload" :loading="uploadLoading">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
