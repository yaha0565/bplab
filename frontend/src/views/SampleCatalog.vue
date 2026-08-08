<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'
import { Search, Plus, Delete } from '@element-plus/icons-vue'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const canManage = computed(() => user.role === '管理员' || user.role === '样品管理员')

const catalog = ref([])
const loading = ref(true)
const searchText = ref('')

// 新增对话框
const dialogVisible = ref(false)
const saving = ref(false)
const form = ref({
  sample_name: '', model: '', material_name: '',
  sample_code: '', process: '', material_suffix: '',
  source_sequence: '', category: '', unit: '',
  experiment_codes: [], notes: '',
})

async function loadCatalog() {
  loading.value = true
  try {
    const { data } = await request.get('/catalog', { params: { search: searchText.value || undefined, limit: 200 } })
    catalog.value = data
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  form.value = {
    sample_name: '', model: '', material_name: '',
    sample_code: '', process: '', material_suffix: '',
    source_sequence: '', category: '', unit: '',
    experiment_codes: [], notes: '',
  }
  dialogVisible.value = true
}

async function handleAdd() {
  const f = form.value
  if (!f.sample_name) { ElMessage.warning('请输入样品名称'); return }
  if (!f.model) { ElMessage.warning('请输入型号'); return }
  if (!f.material_name) { ElMessage.warning('请输入材料名称'); return }

  saving.value = true
  try {
    await request.post('/catalog', {
      sample_name: f.sample_name,
      model: f.model,
      material_name: f.material_name,
      sample_code: f.sample_code || null,
      process: f.process || null,
      material_suffix: f.material_suffix || null,
      source_sequence: f.source_sequence || null,
      category: f.category || null,
      unit: f.unit || null,
      experiment_codes: f.experiment_codes.length ? f.experiment_codes : null,
      notes: f.notes || null,
    })
    ElMessage.success('样品资料添加成功')
    dialogVisible.value = false
    loadCatalog()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(item) {
  try {
    await ElMessageBox.confirm(
      `确定要删除样品资料「${item.sample_name}」吗？`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await request.delete(`/catalog/${item.id}`)
    ElMessage.success('样品资料已删除')
    loadCatalog()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(loadCatalog)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>样品资料库</h1>
      <div style="display:flex;gap:12px">
        <el-button v-if="canManage" type="primary" :icon="Plus" @click="showAddDialog">新增样品资料</el-button>
        <el-input
          v-model="searchText"
          placeholder="搜索样品名称/编号/材料..."
          style="width:300px"
          clearable
          @input="loadCatalog"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
    </div>

    <el-card>
      <el-table :data="catalog" v-loading="loading" stripe empty-text="暂无数据" max-height="600">
        <el-table-column prop="sample_code" label="样品代码" width="120" />
        <el-table-column prop="sample_name" label="样品名称" min-width="200" />
        <el-table-column prop="model" label="型号" width="150" />
        <el-table-column prop="material_name" label="材料名称" width="150" />
        <el-table-column prop="process" label="工艺" width="120" />
        <el-table-column prop="category" label="类别" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'danger'" size="small">{{ row.enabled ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="canManage" label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button text type="danger" :icon="Delete" @click.stop="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增样品资料对话框 -->
    <el-dialog v-model="dialogVisible" title="新增样品资料" width="560px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="样品名称" required>
              <el-input v-model="form.sample_name" placeholder="如 TC4钛合金试样" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="样品代码">
              <el-input v-model="form.sample_code" placeholder="如 TC4-001" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="型号" required>
              <el-input v-model="form.model" placeholder="如 φ10×50mm" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="材料名称" required>
              <el-input v-model="form.material_name" placeholder="如 Ti-6Al-4V" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="工艺">
              <el-input v-model="form.process" placeholder="如 退火态" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="类别">
              <el-input v-model="form.category" placeholder="如 金属、陶瓷" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="单位">
              <el-input v-model="form.unit" placeholder="如 件、kg" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="后缀">
              <el-input v-model="form.material_suffix" placeholder="材料后缀" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="来源序号">
          <el-input v-model="form.source_sequence" placeholder="来源序号" />
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
.page { max-width: 1400px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
