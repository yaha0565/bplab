<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import request from '../utils/request'

const loading = ref(false)
const logs = ref([])
const verifyResult = ref(null)
const entityType = ref('commission')
const entityId = ref('')
const verifying = ref(false)

onMounted(() => { loadLogs() })

async function loadLogs() {
  loading.value = true
  try {
    const { data } = await request.get('/traceability/audit-logs', { params: { limit: 100 } })
    logs.value = data
  } catch { ElMessage.warning('加载审计日志失败') } finally { loading.value = false }
}

async function verifyChain() {
  if (!entityId.value.trim()) { ElMessage.warning('请输入实体编号'); return }
  verifying.value = true
  try {
    // 从后台拉取该实体的审计日志并按哈希链表验算
    const { data } = await request.get('/traceability/audit-logs', {
      params: { entity_type: entityType.value, entity_id: entityId.value.trim(), limit: 500 },
    })
    const entries = Array.isArray(data) ? data : []
    if (entries.length === 0) {
      verifyResult.value = { ok: true, detail: '该实体暂无审计记录', broken: null }
      return
    }
    // 从头链到尾验算哈希
    let prevHash = '0'.repeat(64)
    let broken = null
    for (const e of entries) {
      if (e.previous_hash && e.previous_hash !== prevHash) {
        broken = { ...e, expected: prevHash, found: e.previous_hash }
        break
      }
      prevHash = e.entry_hash || '0'.repeat(64)
    }
    verifyResult.value = broken
      ? { ok: false, detail: `在记录 #${broken.id} 处链断裂`, broken }
      : { ok: true, detail: `审计链完整，共 ${entries.length} 条记录`, broken: null }
  } catch { ElMessage.error('验证失败') } finally { verifying.value = false }
}

function formatDate(d) { return d ? new Date(d).toLocaleString('zh-CN') : '—' }
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2><el-icon><Lock /></el-icon> 审计追踪链</h2>
    </div>

    <!-- 链验证 -->
    <el-card style="margin-bottom:16px">
      <template #header><strong>审计链完整性验证</strong></template>
      <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
        <el-select v-model="entityType" style="width:140px">
          <el-option label="委托" value="commission" /><el-option label="任务" value="task" />
          <el-option label="报告" value="report" /><el-option label="样品" value="sample" />
          <el-option label="异议" value="objection" /><el-option label="设备故障" value="equipment_incident" />
          <el-option label="样品组" value="sample_group" />
        </el-select>
        <el-input v-model="entityId" placeholder="输入实体编号" clearable @keyup.enter="verifyChain" style="width:280px" />
        <el-button type="primary" :loading="verifying" @click="verifyChain">验证链完整性</el-button>
      </div>
      <div v-if="verifyResult" style="margin-top:12px">
        <el-alert v-if="verifyResult.ok" :title="verifyResult.detail" type="success" :closable="false" show-icon>
          <template #icon><el-icon><CircleCheck /></el-icon></template>
        </el-alert>
        <el-alert v-else :title="verifyResult.detail" type="error" :closable="false" show-icon>
          <template #icon><el-icon><CircleClose /></el-icon></template>
        </el-alert>
      </div>
    </el-card>

    <!-- 审计日志列表 -->
    <el-table :data="logs" v-loading="loading" stripe max-height="500">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="entity_type" label="实体类型" width="120" />
      <el-table-column prop="entity_id" label="实体编号" width="200" />
      <el-table-column prop="actor" label="操作人" width="100" />
      <el-table-column prop="action" label="操作" width="160" />
      <el-table-column label="时间" width="170"><template #default="{row}">{{ formatDate(row.created_at) }}</template></el-table-column>
      <el-table-column prop="previous_hash" label="前序哈希" min-width="200" show-overflow-tooltip>
        <template #default="{row}"><code style="font-size:11px">{{ row.previous_hash || '—' }}</code></template>
      </el-table-column>
      <el-table-column prop="entry_hash" label="条目哈希" min-width="200" show-overflow-tooltip>
        <template #default="{row}"><code style="font-size:11px">{{ row.entry_hash || '—' }}</code></template>
      </el-table-column>
    </el-table>
  </div>
</template>
