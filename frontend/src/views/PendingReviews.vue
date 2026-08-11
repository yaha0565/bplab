<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../utils/request'
import { ElMessage } from 'element-plus'

const router = useRouter()
const records = ref([])
const loading = ref(true)
const reviewDialogVisible = ref(false)
const reviewing = ref(false)

// Current record being reviewed
const currentRecord = ref(null)
const reviewDecision = ref('通过')
const reviewComment = ref('')
const reviewCorrectionFields = ref([])

// Field categories for correction_fields (对应实验7步骤)
const CORRECTION_FIELD_OPTIONS = [
  { value: '①任务与样品确认', label: '① 任务与样品确认｜样品接收、编号或状态确认' },
  { value: '②设备与实验前检查', label: '② 设备与实验前检查｜设备状态、校准信息或异常说明' },
  { value: '③环境与参数', label: '③ 环境与参数｜温湿度、实验参数' },
  { value: '④原始数据', label: '④ 原始数据｜测量数据、计算结果' },
  { value: '⑤母版过程确认', label: '⑤ 母版过程确认｜受控模板补充字段' },
  { value: '⑥照片留档', label: '⑥ 照片留档｜实验照片和证据' },
  { value: '⑦实验员自查', label: '⑦ 实验员自查｜提交前自查确认' },
]

// Status → tag type
function getStatusType(status) {
  const map = { '待复核': 'warning', '更正待复核': 'danger', '已锁定': 'success', '复核退回': 'info' }
  return map[status] || 'info'
}

// Load pending reviews
async function loadRecords() {
  loading.value = true
  try {
    const { data } = await request.get('/records/pending-review', { params: { limit: 50 } })
    records.value = data
  } finally {
    loading.value = false
  }
}

// Open review dialog
function openReview(record) {
  currentRecord.value = record
  reviewDecision.value = '通过'
  reviewComment.value = ''
  reviewCorrectionFields.value = []
  reviewDialogVisible.value = true
}

// View record detail
function viewRecord(record) {
  router.push(`/records/${record.record_no}/v${record.version}`)
}

// Open Word preview in new tab
function openWordPreview(record) {
  const route = router.resolve(`/records/${record.record_no}/v${record.version}`)
  window.open(route.href, '_blank')
}

// Submit review
async function submitReview() {
  if (reviewDecision.value === '退回') {
    if (!reviewComment.value.trim()) {
      ElMessage.warning('退回时必须填写复核意见')
      return
    }
    if (reviewCorrectionFields.value.length === 0) {
      ElMessage.warning('退回时必须至少指定一个需要修改的字段')
      return
    }
  }

  reviewing.value = true
  try {
    const resp = await request.post(`/records/${currentRecord.value.record_no}/review`, {
      decision: reviewDecision.value,
      comment: reviewComment.value,
      correction_fields: reviewCorrectionFields.value,
    })
    ElMessage.success(resp.data?.message || `复核${reviewDecision.value}`)
    reviewDialogVisible.value = false
    loadRecords()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '复核失败')
  } finally {
    reviewing.value = false
  }
}

onMounted(loadRecords)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>原始记录复核</h1>
      <el-button @click="loadRecords" :loading="loading">刷新</el-button>
    </div>

    <el-card>
      <el-table :data="records" v-loading="loading" stripe empty-text="暂无待复核记录">
        <el-table-column prop="record_no" label="记录编号" width="200" />
        <el-table-column prop="task_no" label="任务编号" width="200" />
        <el-table-column prop="version" label="版本" width="80">
          <template #default="{ row }">V{{ row.version }}</template>
        </el-table-column>
        <el-table-column prop="experiment" label="检测项目" min-width="200" />
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="owner" label="实验员" width="100" />
        <el-table-column prop="created_at" label="提交时间" width="160" />
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewRecord(row)">查看数据</el-button>
            <el-button size="small" type="primary" @click="openReview(row)">复核</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 复核对话框 -->
    <el-dialog v-model="reviewDialogVisible" title="复核原始记录" width="580px" :close-on-click-modal="false">
      <template v-if="currentRecord">
        <el-descriptions :column="2" border size="small" style="margin-bottom:20px">
          <el-descriptions-item label="记录编号">{{ currentRecord.record_no }}</el-descriptions-item>
          <el-descriptions-item label="版本">V{{ currentRecord.version }}</el-descriptions-item>
          <el-descriptions-item label="检测项目" :span="2">{{ currentRecord.experiment }}</el-descriptions-item>
          <el-descriptions-item label="实验员">{{ currentRecord.owner }}</el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ currentRecord.created_at }}</el-descriptions-item>
        </el-descriptions>

        <el-alert type="info" :closable="false" show-icon style="margin-bottom:16px">
          <template #title>审核前请先点击下方按钮查看实验原始数据和Word预览</template>
        </el-alert>
        <div style="display:flex;gap:10px;margin-bottom:20px">
          <el-button type="primary" plain @click="viewRecord(currentRecord)">
            📋 查看实验原始数据
          </el-button>
        </div>

        <el-form label-width="100px">
          <el-form-item label="复核决定" required>
            <el-radio-group v-model="reviewDecision">
              <el-radio value="通过">通过 — 锁定记录并自动生成检验报告</el-radio>
              <el-radio value="退回">退回 — 退回实验员修改</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="复核意见" required>
            <el-input v-model="reviewComment" type="textarea" :rows="3"
              placeholder="填写复核意见（退回时必须填写）" />
          </el-form-item>

          <el-form-item v-if="reviewDecision === '退回'" label="修改字段" required>
            <el-select v-model="reviewCorrectionFields" multiple placeholder="至少选择一个需要修改的字段" style="width:100%">
              <el-option v-for="opt in CORRECTION_FIELD_OPTIONS" :key="opt.value"
                :label="opt.label" :value="opt.value" />
            </el-select>
            <div style="font-size:11px;color:#94A3B8;margin-top:4px">
              只有被选中的字段和步骤才允许实验员修改，其余字段将被锁定只读
            </div>
          </el-form-item>
        </el-form>
      </template>

      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReview" :loading="reviewing">
          {{ reviewDecision === '通过' ? '确认通过' : '确认退回' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { max-width: 1400px; }
.page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
