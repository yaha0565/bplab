<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'

const healthData = ref(null)
const loading = ref(false)
const initText = ref('')
const initLoading = ref(false)
const initResult = ref(null)

async function loadHealth() {
  loading.value = true
  try {
    const { data } = await request.get('/system/health')
    healthData.value = data
  } catch (e) {
    ElMessage.error('无法获取系统健康信息')
  } finally {
    loading.value = false
  }
}

async function handleInit() {
  if (initText.value !== '确认初始化系统') {
    ElMessage.warning('请输入正确的确认文字')
    return
  }
  try {
    await ElMessageBox.confirm(
      '⚠️ 此操作将清空所有业务数据（委托、样品、任务、记录、报告、审计日志等），仅保留基础配置。此操作不可撤销！',
      '最终确认：系统初始化',
      {
        type: 'error',
        confirmButtonText: '我已知晓风险，确认初始化',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
      }
    )
  } catch {
    return // 用户取消
  }

  initLoading.value = true
  try {
    const { data } = await request.post('/system/initialize', { confirm_text: initText.value })
    initResult.value = data
    ElMessage.success('系统初始化完成')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '初始化失败')
  } finally {
    initLoading.value = false
  }
}

// 加载健康信息
loadHealth()
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>系统初始化</h1>
    </div>

    <!-- 健康状态 -->
    <el-card style="margin-bottom:20px" header="系统健康状态">
      <div v-if="healthData" class="health-grid">
        <el-tag :type="healthData.database_ok ? 'success' : 'danger'" size="large">
          数据库: {{ healthData.database_ok ? '正常' : '异常' }}
        </el-tag>
        <span style="color:#64748B">总数据表: {{ healthData.total_tables_with_data }} 个有数据</span>
      </div>
      <div v-if="healthData" style="margin-top:16px">
        <el-table :data="Object.entries(healthData.table_counts).map(([k,v]) => ({ table: k, rows: v }))" size="small" max-height="400">
          <el-table-column prop="table" label="数据表" />
          <el-table-column prop="rows" label="行数" width="120">
            <template #default="{ row }">
              <el-tag :type="row.rows > 0 ? 'warning' : 'info'" size="small">{{ row.rows }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-skeleton v-else :rows="4" animated />
    </el-card>

    <!-- 初始化操作 -->
    <el-card header="⚠️ 系统初始化">
      <el-alert
        title="危险操作"
        type="error"
        description="系统初始化将清空所有业务数据：委托单、样品组、样品、任务包、任务、原始记录、报告、审计日志、修改日志、通知、异议、设备故障、危废记录、附件记录（数据库中的记录）。将保留：用户、单位、检测方法、样品目录、设备库、实验配置。"
        show-icon
        :closable="false"
        style="margin-bottom:16px"
      />

      <div style="margin-top:12px">
        <span style="color:#64748B">请输入</span>
        <code style="background:#FEF2F2;color:#DC2626;padding:2px 8px;border-radius:4px;margin:0 8px">确认初始化系统</code>
        <span style="color:#64748B">以确认操作：</span>
      </div>

      <div style="display:flex;gap:12px;margin-top:12px">
        <el-input v-model="initText" placeholder="确认初始化系统" style="width:300px" />
        <el-button type="danger" @click="handleInit" :loading="initLoading" :disabled="initText !== '确认初始化系统'">
          执行初始化
        </el-button>
      </div>

      <!-- 初始化结果 -->
      <div v-if="initResult" style="margin-top:16px">
        <el-alert type="success" :title="initResult.message" :closable="false" />
        <div style="margin-top:8px;max-height:300px;overflow-y:auto">
          <div v-for="t in initResult.cleared_tables" :key="t" style="font-size:12px;color:#64748B;padding:2px 0">
            {{ t }}
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.page { max-width: 1000px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
.health-grid { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
</style>
