<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, View, Upload, Delete, Edit } from '@element-plus/icons-vue'
import request from '../utils/request'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const isAdmin = computed(() => user.role === '管理员')

const templates = ref([])
const loading = ref(false)
const activeCategory = ref('')
const previewVisible = ref(false)
const previewHtml = ref('')
const previewTitle = ref('')

// 上传
const uploadVisible = ref(false)
const uploadLoading = ref(false)
const uploadForm = ref({ file: null, display_name: '' })
const uploadRef = ref(null)

// 重命名
const renameVisible = ref(false)
const renameLoading = ref(false)
const renameForm = ref({ old_filename: '', new_filename: '' })

const categories = [
  { key: '', label: '全部' },
  { key: 'RECORD', label: '实验原始记录模板' },
  { key: 'SOP', label: '标准操作规程 (SOP)' },
  { key: 'FORM', label: '管理表单模板' },
]

onMounted(loadTemplates)

async function loadTemplates() {
  loading.value = true
  try {
    const params = activeCategory.value ? { category: activeCategory.value } : {}
    const { data } = await request.get('/templates', { params })
    templates.value = data
  } catch {
    ElMessage.error('模板列表加载失败')
  } finally {
    loading.value = false
  }
}

function switchCategory(cat) {
  activeCategory.value = cat
  loadTemplates()
}

function downloadFile(filename) {
  const token = localStorage.getItem('token')
  const url = `/api/v1/templates/${filename}`
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then(res => res.blob())
    .then(blob => {
      const blobUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = filename
      link.click()
      URL.revokeObjectURL(blobUrl)
    })
    .catch(() => ElMessage.error('下载失败'))
}

async function previewFile(filename) {
  try {
    previewTitle.value = filename
    previewVisible.value = true
    previewHtml.value = '<div style="text-align:center;padding:40px;color:#94A3B8;">加载中...</div>'
    const { data } = await request.get(`/templates/${filename}/preview`)
    previewHtml.value = data
  } catch (e) {
    previewHtml.value = `<div style="text-align:center;padding:40px;color:#EF4444;">
      预览失败：${e.response?.data?.detail || '预览功能需要 LibreOffice'}</div>`
  }
}

// ── 上传 ──
function showUpload() {
  uploadForm.value = { file: null, display_name: '' }
  uploadVisible.value = true
}

function handleFileChange(file) {
  uploadForm.value.file = file.raw
}

async function handleUpload() {
  if (!uploadForm.value.file) { ElMessage.warning('请选择文件'); return }
  uploadLoading.value = true
  try {
    const fd = new FormData()
    fd.append('file', uploadForm.value.file)
    if (uploadForm.value.display_name) fd.append('display_name', uploadForm.value.display_name)
    await request.post('/templates/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    ElMessage.success('模板上传成功')
    uploadVisible.value = false
    loadTemplates()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '上传失败')
  } finally {
    uploadLoading.value = false
  }
}

// ── 删除 ──
async function deleteTemplate(filename) {
  try {
    await ElMessageBox.confirm(`确定要删除模板「${filename}」吗？此操作不可撤销。`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await request.delete(`/templates/${filename}`)
    ElMessage.success('已删除')
    loadTemplates()
  } catch { /* 取消 */ }
}

// ── 重命名 ──
function showRename(filename) {
  renameForm.value = { old_filename: filename, new_filename: filename }
  renameVisible.value = true
}

async function handleRename() {
  if (!renameForm.value.new_filename || renameForm.value.new_filename === renameForm.value.old_filename) {
    ElMessage.warning('请输入新的文件名')
    return
  }
  renameLoading.value = true
  try {
    await request.put(`/templates/${renameForm.value.old_filename}/rename`, {
      new_filename: renameForm.value.new_filename,
    })
    ElMessage.success('重命名成功')
    renameVisible.value = false
    loadTemplates()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '重命名失败')
  } finally {
    renameLoading.value = false
  }
}

function getCategoryTag(category) {
  const map = { RECORD: 'primary', SOP: 'success', FORM: 'warning' }
  return map[category] || 'info'
}

function getCategoryLabel(category) {
  const map = { RECORD: '记录模板', SOP: 'SOP', FORM: '管理表单' }
  return map[category] || category
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>模板与文档管理</h1>
      <el-button v-if="isAdmin" type="primary" :icon="Upload" @click="showUpload">上传模板</el-button>
    </div>

    <el-tabs v-model="activeCategory" @tab-change="switchCategory" style="margin-bottom:16px">
      <el-tab-pane v-for="cat in categories" :key="cat.key" :label="cat.label" :name="cat.key" />
    </el-tabs>

    <el-card v-loading="loading">
      <el-table :data="templates" stripe empty-text="暂无模板文件">
        <el-table-column prop="display_name" label="模板名称" min-width="300" />
        <el-table-column label="类别" width="120">
          <template #default="{ row }">
            <el-tag :type="getCategoryTag(row.category)" size="small">
              {{ getCategoryLabel(row.category) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="experiment_code" label="实验编号" width="100" />
        <el-table-column label="文件大小" width="100">
          <template #default="{ row }">{{ row.size_kb }} KB</template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button text type="primary" :icon="View" @click="previewFile(row.filename)">预览</el-button>
            <el-button text type="primary" :icon="Download" @click="downloadFile(row.filename)">下载</el-button>
            <template v-if="isAdmin">
              <el-button text type="warning" :icon="Edit" @click="showRename(row.filename)">重命名</el-button>
              <el-button text type="danger" :icon="Delete" @click="deleteTemplate(row.filename)">删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 预览对话框 -->
    <el-dialog v-model="previewVisible" :title="previewTitle" width="80%" top="2vh">
      <div class="preview-container" v-html="previewHtml" />
    </el-dialog>

    <!-- 上传对话框 -->
    <el-dialog v-model="uploadVisible" title="上传模板" width="480px">
      <el-form :model="uploadForm" label-width="80px">
        <el-form-item label="模板文件" required>
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".docx"
            :on-change="handleFileChange"
            drag
          >
            <el-icon style="font-size:32px;color:#CBD5E1"><Upload /></el-icon>
            <div style="margin-top:8px;color:#94A3B8">拖拽或点击上传 .docx 文件</div>
          </el-upload>
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="uploadForm.display_name" placeholder="可选，留空则自动从文件名解析" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpload" :loading="uploadLoading">上传</el-button>
      </template>
    </el-dialog>

    <!-- 重命名对话框 -->
    <el-dialog v-model="renameVisible" title="重命名模板" width="420px">
      <el-form :model="renameForm" label-width="80px">
        <el-form-item label="当前文件">
          <span style="color:#64748B">{{ renameForm.old_filename }}</span>
        </el-form-item>
        <el-form-item label="新文件名" required>
          <el-input v-model="renameForm.new_filename" placeholder="必须以 .docx 结尾" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renameVisible = false">取消</el-button>
        <el-button type="primary" @click="handleRename" :loading="renameLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; }
.page-header { margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }

.preview-container {
  max-height: 80vh;
  overflow-y: auto;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 24px;
  background: #fff;
}
</style>
