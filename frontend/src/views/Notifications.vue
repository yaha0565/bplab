<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Bell } from '@element-plus/icons-vue'
import request from '../utils/request'

const loading = ref(false)
const list = ref([])

onMounted(() => { loadList() })

async function loadList() {
  loading.value = true
  try {
    const { data } = await request.get('/notifications')
    list.value = data
  } catch { ElMessage.warning('加载通知失败') } finally { loading.value = false }
}

async function markRead(id) {
  try {
    await request.put('/notifications/read', { ids: [id] })
    ElMessage.success('已标记为已读')
    loadList()
  } catch { ElMessage.error('操作失败') }
}

async function markAllRead() {
  try {
    await request.put('/notifications/read', { ids: null })
    ElMessage.success('全部已读')
    loadList()
  } catch { ElMessage.error('操作失败') }
}

function formatDate(d) { return d ? new Date(d).toLocaleString('zh-CN') : '—' }
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2><el-icon><Bell /></el-icon> 通知中心</h2>
      <el-button v-if="list.length" @click="markAllRead">全部已读</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="title" label="标题" width="250" />
      <el-table-column prop="message" label="内容" min-width="300" show-overflow-tooltip />
      <el-table-column label="类型" width="100">
        <template #default="{row}">
          <el-tag size="small">{{ row.entity_type || '系统' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="170">
        <template #default="{row}">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{row}">
          <el-button size="small" type="primary" link @click="markRead(row.id)">已读</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !list.length" description="暂无通知" />
  </div>
</template>
