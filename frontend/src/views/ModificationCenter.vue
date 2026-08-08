<script setup>
import { ref, onMounted } from 'vue'
import request from '../utils/request'
import { Search } from '@element-plus/icons-vue'

const modifications = ref([])
const loading = ref(false)
const filters = ref({ entity_type: '', actor: '' })
const pagination = ref({ limit: 50, offset: 0 })

// 实体类型选项
const entityTypes = [
  { label: '全部', value: '' },
  { label: '委托单', value: 'commission' },
  { label: '任务', value: 'task' },
  { label: '记录', value: 'record' },
  { label: '报告', value: 'report' },
  { label: '样品', value: 'sample' },
]

onMounted(loadModifications)

async function loadModifications() {
  loading.value = true
  try {
    const params = { ...pagination.value }
    if (filters.value.entity_type) params.entity_type = filters.value.entity_type
    if (filters.value.actor) params.actor = filters.value.actor
    const { data } = await request.get('/traceability/modifications', { params })
    modifications.value = data
  } catch { /* ignore */ }
  finally { loading.value = false }
}

function handleSearch() {
  pagination.value.offset = 0
  loadModifications()
}

function getActionTag(action) {
  const map = {
    'create': 'success', 'update': 'warning', 'delete': 'danger',
    'confirm': 'primary', 'approve': 'success', 'reject': 'danger',
    'submit': 'primary', 'review': 'info',
  }
  return map[action] || 'info'
}

function getActionLabel(action) {
  const map = {
    'create': '创建', 'update': '修改', 'delete': '删除',
    'confirm': '确认', 'approve': '批准', 'reject': '退回',
    'submit': '提交', 'review': '复核', 'revoke': '作废',
    'correct': '更正', 'replace': '替代',
  }
  return map[action] || action
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>修改中心</h1>
    </div>

    <!-- 筛选栏 -->
    <el-card style="margin-bottom:16px">
      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center">
        <span style="color:#64748B;font-size:13px">实体类型：</span>
        <el-select v-model="filters.entity_type" placeholder="全部" clearable style="width:140px" @change="handleSearch">
          <el-option v-for="et in entityTypes" :key="et.value" :label="et.label" :value="et.value" />
        </el-select>
        <span style="color:#64748B;font-size:13px;margin-left:16px">操作人：</span>
        <el-input v-model="filters.actor" placeholder="用户名" clearable style="width:160px" @keyup.enter="handleSearch" @clear="handleSearch" />
        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
      </div>
    </el-card>

    <el-card>
      <el-table :data="modifications" v-loading="loading" stripe empty-text="暂无修改记录" max-height="600">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="entity_type" label="实体类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.entity_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="entity_id" label="实体编号" width="200" />
        <el-table-column prop="action" label="操作" width="80">
          <template #default="{ row }">
            <el-tag :type="getActionTag(row.action)" size="small">{{ getActionLabel(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="field_name" label="字段" width="140" />
        <el-table-column label="旧值" min-width="150">
          <template #default="{ row }">
            <span style="color:#94A3B8;font-size:12px;word-break:break-all">{{ row.old_value || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="新值" min-width="150">
          <template #default="{ row }">
            <span style="word-break:break-all">{{ row.new_value || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="actor" label="操作人" width="100" />
        <el-table-column prop="reason" label="原因" width="120">
          <template #default="{ row }">
            <span style="color:#64748B;font-size:12px">{{ row.reason || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="160" />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.page { max-width: 1400px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
