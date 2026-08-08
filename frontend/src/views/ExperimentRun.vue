<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '../utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, VideoPause, Plus, Delete } from '@element-plus/icons-vue'
import CameraCapture from '../components/CameraCapture.vue'

const route = useRoute()
const router = useRouter()
const user = JSON.parse(localStorage.getItem('user') || '{}')
const isAssignee = computed(() => task.value?.assignee === user.username)
const isTester = computed(() => user.role === '实验员')
const taskNo = route.params.taskNo

const task = ref(null)
const config = ref(null)
const loading = ref(true)
const saving = ref(false)
const acting = ref(false)

// ── 动态表单数据 ──
const formData = reactive({})          // flat key→value for all fields
const measurementRows = ref([])        // array of row objects
const photoCheckpoints = ref([])       // [{code, label, file}]
const reportSummary = ref('')
const reportConclusion = ref('')
const testerSelfCheck = ref(false)

// ── 加载 ──
onMounted(async () => {
  try {
    const { data } = await request.get(`/tasks/${taskNo}`)
    task.value = data.task

    // 加载实验配置
    if (task.value?.experiment_code) {
      const cfgRes = await request.get(`/config/${task.value.experiment_code}`)
      const raw = cfgRes.data || {}
      // 仅在响应包含可用数据时设置 config
      if (!raw.fields && !raw.columns) {
        config.value = null
      } else {
        config.value = raw

      // 初始化表单
      if (config.value.fields) {
        for (const f of config.value.fields) {
          if (f.key && !(f.key in formData)) {
            // 预设值
            if (f.key === 'detection_location') formData[f.key] = task.value.detection_location || ''
            else if (f.key === 'start_time') formData[f.key] = task.value.experiment_started_at || ''
            else if (f.key === 'test_date') formData[f.key] = new Date().toISOString().slice(0, 10)
            else formData[f.key] = f.default ?? ''
          }
        }
      }

      // 初始化测量表格
      if (config.value.columns?.length) {
        const sampleNos = task.value.sample_nos
          ? task.value.sample_nos.split(',')
          : [task.value.group_no || taskNo]
        initMeasurementRows(sampleNos)
      }

        // 初始化拍照节点
        if (raw.photo_checkpoints?.length) {
          photoCheckpoints.value = raw.photo_checkpoints.map(cp => ({
            ...cp,
            file: null,
            previewUrl: '',
          }))
        }
      }  // end else (has config data)
    }    // end if experiment_code

    // 加载已有记录（最新版本）
    try {
      const recRes = await request.get(`/records/${taskNo}/v1`)
      if (recRes.data?.payload) {
        const pl = typeof recRes.data.payload === 'string'
          ? JSON.parse(recRes.data.payload)
          : recRes.data.payload
        // 恢复表单数据
        if (pl._form) Object.assign(formData, pl._form)
        if (pl._rows) measurementRows.value = pl._rows
        if (pl._photos) {
          for (const p of pl._photos) {
            const cp = photoCheckpoints.value.find(c => c.code === p.code)
            if (cp) { cp.file = p.file; cp.previewUrl = p.previewUrl }
          }
        }
        reportSummary.value = pl._report_summary || recRes.data.report_summary || ''
        reportConclusion.value = pl._report_conclusion || recRes.data.report_conclusion || ''
        testerSelfCheck.value = pl._tester_self_check || recRes.data.tester_self_check || false
      }
    } catch { /* no existing record */ }
  } finally {
    loading.value = false
  }
})

// ── 初始化测量行 ──
function initMeasurementRows(sampleNos) {
  const cols = config.value.columns || []
  const faces = config.value.face_labels?.length
    ? config.value.face_labels
    : config.value.row_expansion === 'faces'
      ? ['面1', '面2']
      : [null]

  const rows = []
  for (const sno of sampleNos) {
    for (const face of faces) {
      const row = { sample_no: String(sno).trim(), face: face || '' }
      for (const c of cols) {
        if (c.column_key === 'sample_no') row[c.column_key] = String(sno).trim()
        else if (c.column_key === 'face') row[c.column_key] = face || ''
        else row[c.column_key] = c.column_default ?? ''
      }
      rows.push(row)
    }
  }
  measurementRows.value = rows
}

// ── 添加/删除测量行 ──
function addMeasurementRow() {
  const cols = config.value.columns || []
  const row = {}
  for (const c of cols) row[c.column_key] = ''
  row.sample_no = ''
  row.face = ''
  measurementRows.value.push(row)
}

function removeMeasurementRow(index) {
  if (measurementRows.value.length <= 1) return
  measurementRows.value.splice(index, 1)
}

// ── 开始/结束实验 ──
async function markTime(action) {
  try {
    await ElMessageBox.confirm(`确认「${action === '开始' ? '开始' : '结束'}实验」？`, '', {
      type: 'info', confirmButtonText: '确认', cancelButtonText: '取消',
    })
    acting.value = true
    await request.put(`/tasks/${taskNo}/time`, { action })
    ElMessage.success(`已标记实验${action}`)
    task.value = (await request.get(`/tasks/${taskNo}`)).data.task
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    acting.value = false
  }
}

// ── 拍照节点 ──
function onPhotoCaptured(cp, { file, previewUrl }) {
  cp.file = file
  cp.previewUrl = previewUrl
}

function removePhoto(cp) {
  cp.file = null
  cp.previewUrl = ''
}

// ── 保存 / 提交 ──
async function handleSave(submitForReview) {
  if (!task.value) return

  // 收集表单数据
  const _form = { ...formData }

  // 收集测量数据
  const _rows = measurementRows.value.map(r => ({ ...r }))

  // 收集照片
  const _photos = photoCheckpoints.value
    .filter(cp => cp.file)
    .map(cp => ({ code: cp.code || cp.checkpoint_code, label: cp.label || cp.checkpoint_label }))

  const businessRecord = {
    _form,
    _rows,
    _photos,
    _report_summary: reportSummary.value,
    _report_conclusion: reportConclusion.value,
    _tester_self_check: testerSelfCheck.value,
  }

  saving.value = true
  try {
    await request.post('/records', {
      task_no: taskNo,
      business_record: businessRecord,
      report_summary: reportSummary.value,
      report_conclusion: reportConclusion.value,
      tester_self_check: testerSelfCheck.value,
      submit_for_review: submitForReview,
    })
    ElMessage.success(submitForReview ? '已提交复核' : '草稿已保存')
    if (submitForReview) {
      router.push('/my-tasks')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

// ── 多选处理 ──
function toggleMultiselect(key, option) {
  if (!Array.isArray(formData[key])) formData[key] = []
  const idx = formData[key].indexOf(option)
  if (idx >= 0) formData[key].splice(idx, 1)
  else formData[key].push(option)
}

// ── 分组字段（按 section_order）──
const fieldSections = computed(() => {
  if (!config.value?.fields?.length) return []
  const secMap = {}
  for (const f of config.value.fields) {
    const sec = f.section_order ?? 0
    if (!secMap[sec]) secMap[sec] = { title: f.section_title || `第${sec + 1}部分`, fields: [] }
    secMap[sec].fields.push(f)
  }
  return Object.values(secMap)
})

// 拍照节点分组
const checkpointGroups = computed(() => {
  if (!config.value?.photo_checkpoints?.length) return []
  return config.value.photo_checkpoints
})
</script>

<template>
  <div class="page" v-loading="loading">
    <!-- ===== 头部 ===== -->
    <div class="page-header">
      <div>
        <h1>
          实验执行
          <span style="font-size:14px;color:#94A3B8;font-weight:400;margin-left:8px">{{ task?.task_no }}</span>
        </h1>
        <div style="color:#94A3B8;font-size:13px;margin-top:4px">
          {{ task?.experiment }} · {{ task?.method_code }} · {{ task?.detection_location }}
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <el-tag v-if="task" :type="task.status === '检测中' ? 'warning' : 'info'" size="small">{{ task.status }}</el-tag>
        </div>
      </div>
      <div style="display:flex;gap:8px">
        <el-button
          v-if="isTester && isAssignee && task?.status === '待接收'"
          type="primary" :icon="VideoPlay" :loading="acting"
          @click="markTime('开始')"
        >开始实验</el-button>
        <el-button
          v-if="isTester && isAssignee && task?.status === '检测中'"
          type="danger" :icon="VideoPause" :loading="acting"
          @click="markTime('结束')"
        >结束实验</el-button>
      </div>
    </div>

    <template v-if="task && config">
      <el-row :gutter="20">
        <!-- ===== 左侧：实验表单 + 测量表 ===== -->
        <el-col :span="16">
          <!-- 预检查项 -->
          <el-card v-if="config.prechecks?.length" header="使用前检查" style="margin-bottom:16px">
            <el-checkbox-group>
              <div v-for="pc in config.prechecks" :key="pc.check_name || pc.label" style="margin-bottom:4px">
                <el-checkbox>{{ pc.check_name || pc.label }}</el-checkbox>
              </div>
            </el-checkbox-group>
          </el-card>

          <!-- 动态字段区域 -->
          <el-card
            v-for="(sec, si) in fieldSections"
            :key="si"
            :header="sec.title"
            style="margin-bottom:16px"
          >
            <el-form label-width="160px" label-position="left" size="small">
              <el-row :gutter="16">
                <template v-for="f in sec.fields" :key="f.key">
                  <!-- text -->
                  <el-col v-if="f.type === 'text'" :span="12">
                    <el-form-item :label="f.label">
                      <el-input v-model="formData[f.key]" :disabled="f.readonly" :placeholder="f.label" />
                    </el-form-item>
                  </el-col>
                  <!-- textarea -->
                  <el-col v-else-if="f.type === 'textarea'" :span="24">
                    <el-form-item :label="f.label">
                      <el-input v-model="formData[f.key]" type="textarea" :rows="2" :disabled="f.readonly" />
                    </el-form-item>
                  </el-col>
                  <!-- number -->
                  <el-col v-else-if="f.type === 'number'" :span="8">
                    <el-form-item :label="f.label">
                      <el-input-number
                        v-model="formData[f.key]"
                        :disabled="f.readonly"
                        :precision="3"
                        controls-position="right"
                        style="width:100%"
                      />
                    </el-form-item>
                  </el-col>
                  <!-- date -->
                  <el-col v-else-if="f.type === 'date'" :span="8">
                    <el-form-item :label="f.label">
                      <el-input v-model="formData[f.key]" type="date" :disabled="f.readonly" style="width:100%" />
                    </el-form-item>
                  </el-col>
                  <!-- datetime -->
                  <el-col v-else-if="f.type === 'datetime'" :span="8">
                    <el-form-item :label="f.label">
                      <el-input v-model="formData[f.key]" type="datetime-local" :disabled="f.readonly" style="width:100%" />
                    </el-form-item>
                  </el-col>
                  <!-- select -->
                  <el-col v-else-if="f.type === 'select'" :span="8">
                    <el-form-item :label="f.label">
                      <el-select v-model="formData[f.key]" :disabled="f.readonly" style="width:100%">
                        <el-option
                          v-for="opt in (f.options || [])"
                          :key="opt" :label="opt" :value="opt"
                        />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <!-- multiselect -->
                  <el-col v-else-if="f.type === 'multiselect'" :span="12">
                    <el-form-item :label="f.label">
                      <el-checkbox-group v-model="formData[f.key]" :disabled="f.readonly">
                        <el-checkbox
                          v-for="opt in (f.options || [])"
                          :key="opt" :label="opt" :value="opt"
                        />
                      </el-checkbox-group>
                    </el-form-item>
                  </el-col>
                </template>
              </el-row>
            </el-form>
          </el-card>

          <!-- 测量数据表 -->
          <el-card v-if="config.columns?.length" header="测量数据" style="margin-bottom:16px">
            <template #header>
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span>测量数据</span>
                <el-button size="small" :icon="Plus" @click="addMeasurementRow">添加行</el-button>
              </div>
            </template>
            <div style="overflow-x:auto">
              <table class="measure-table">
                <thead>
                  <tr>
                    <th v-for="c in config.columns" :key="c.column_key" style="min-width:100px;padding:8px;font-size:13px">
                      {{ c.column_label }}
                    </th>
                    <th style="width:60px">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in measurementRows" :key="ri">
                    <td v-for="c in config.columns" :key="c.column_key" style="padding:4px">
                      <template v-if="c.column_key === 'sample_no' || c.column_key === 'face'">
                        <el-input
                          v-model="row[c.column_key]"
                          size="small"
                          :placeholder="c.column_key === 'sample_no' ? '样品号' : '面'"
                          style="width:100px"
                        />
                      </template>
                      <template v-else-if="c.column_type === 'number' || c.column_type === 'calc'">
                        <el-input-number
                          v-model="row[c.column_key]"
                          size="small"
                          :precision="4"
                          controls-position="right"
                          style="width:110px"
                        />
                      </template>
                      <template v-else-if="c.column_type?.startsWith('select:')">
                        <el-select v-model="row[c.column_key]" size="small" style="width:100px">
                          <el-option
                            v-for="opt in c.column_type.split(':')[1].split('|')"
                            :key="opt" :label="opt" :value="opt"
                          />
                        </el-select>
                      </template>
                      <template v-else>
                        <el-input v-model="row[c.column_key]" size="small" style="width:100px" />
                      </template>
                    </td>
                    <td style="text-align:center">
                      <el-button text type="danger" size="small" :icon="Delete" @click="removeMeasurementRow(ri)" />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </el-card>
        </el-col>

        <!-- ===== 右侧：拍照 + 报告 + 提交 ===== -->
        <el-col :span="8">
          <!-- 拍照节点 -->
          <el-card v-if="photoCheckpoints.length" header="拍照节点" style="margin-bottom:16px">
            <div v-for="(cp, cpi) in photoCheckpoints" :key="cp.code || cp.checkpoint_code || cpi" style="margin-bottom:14px">
              <div style="display:flex;align-items:center;gap:4px;margin-bottom:4px">
                <span style="font-size:13px;font-weight:500">{{ cp.label || cp.checkpoint_label || cp.code }}</span>
                <el-tag v-if="cp.required !== false" type="danger" size="small">必填</el-tag>
              </div>
              <CameraCapture
                :model-value="cp.file"
                :preview-url="cp.previewUrl"
                @update:model-value="(f) => cp.file = f"
                @update:preview-url="(url) => cp.previewUrl = url"
                @capture="(evt) => onPhotoCaptured(cp, evt)"
              />
            </div>
          </el-card>

          <!-- 报告摘要 -->
          <el-card header="报告与结论" style="margin-bottom:16px">
            <el-form label-width="80px" size="small">
              <el-form-item label="结果摘要">
                <el-input v-model="reportSummary" type="textarea" :rows="3" placeholder="自动生成或手动输入..." />
              </el-form-item>
              <el-form-item label="判定结论">
                <el-select v-model="reportConclusion" style="width:100%" placeholder="选择结论">
                  <el-option label="符合" value="符合" />
                  <el-option label="不符合" value="不符合" />
                  <el-option label="仅描述结果" value="仅描述结果" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="testerSelfCheck">实验员自检确认</el-checkbox>
              </el-form-item>
            </el-form>
          </el-card>

          <!-- 操作按钮 -->
          <el-card>
            <el-space direction="vertical" style="width:100%">
              <el-button
                type="default"
                style="width:100%"
                :loading="saving"
                :disabled="!isTester || !isAssignee || task?.status !== '检测中'"
                @click="handleSave(false)"
              >💾 保存草稿</el-button>
              <el-button
                type="primary"
                style="width:100%"
                :loading="saving"
                :disabled="!isTester || !isAssignee || task?.status !== '检测中'"
                @click="handleSave(true)"
              >📤 提交复核</el-button>
            </el-space>
            <div v-if="!isTester || !isAssignee" style="color:#94A3B8;font-size:12px;text-align:center;margin-top:8px">
              仅任务分配的实验员可操作
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <!-- 无配置时 -->
    <el-empty v-else-if="!loading && task" description="该实验暂无现行配置版本，无法加载实验表单" />
  </div>
</template>

<style scoped>
.page { max-width: 1500px; }
.page-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: 20px;
}
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }

.measure-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.measure-table th {
  background: #F1F5F9;
  font-weight: 600;
  color: #475569;
  text-align: center;
  border: 1px solid #E2E8F0;
  white-space: nowrap;
}
.measure-table td {
  border: 1px solid #E2E8F0;
  text-align: center;
}
.measure-table tr:hover td {
  background: #F8FAFC;
}
</style>
