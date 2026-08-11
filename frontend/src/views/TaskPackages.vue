<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../utils/request'
import { ElMessage } from 'element-plus'

const router = useRouter()
const user = JSON.parse(localStorage.getItem('user') || '{}')
const currentUser = user.username || ''
const canManage = computed(() => user.role === '管理员' || user.role === '样品管理员')
const isTester = computed(() => user.role === '实验员')

const packages = ref([])
const loading = ref(true)
const activeTab = ref('all')

// ── 检测位置常量 ──
const DETECTION_LOCATIONS = ['化学室', '无损检测室', '性能检测室', '显微检测室', '制样室', '外观检测室', '样品室']
const SAMPLE_CONDITIONS = ['样品已收到，确认完好', '样品已收到，但存在异常', '尚未收到样品']

// ── 接收任务包对话框 ──
const acceptDialogVisible = ref(false)
const acceptPkg = ref(null)
const acceptTasks = ref([])
const acceptSampleCondition = ref('样品已收到，确认完好')
const acceptLocations = reactive({})
const acceptNote = ref('')
const acceptLoading = ref(false)

const statusFilters = {
  all: '',
  pending: '待接收',
  testing: '检测中',
  reviewing: '待复核',
  done: '已完成',
}

async function loadPackages(status) {
  loading.value = true
  try {
    const params = status ? { status } : {}
    const { data } = await request.get('/tasks/packages', { params: { ...params, limit: 50 } })
    packages.value = data
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function handleTabChange(tab) {
  loadPackages(statusFilters[tab])
}

function viewPackage(pkg) {
  router.push(`/task-package/${pkg.package_no}`)
}

// ── 接收任务包（实验员）──
async function openAcceptDialog(pkg) {
  try {
    const { data } = await request.get(`/tasks/packages/${pkg.package_no}`)
    acceptPkg.value = pkg
    acceptTasks.value = data.tasks || []
    acceptSampleCondition.value = '样品已收到，确认完好'
    acceptNote.value = ''
    // 初始化检测位置（已有值保留，否则默认性能检测室）
    const locs = {}
    for (const t of acceptTasks.value) {
      locs[t.task_no] = t.detection_location || '性能检测室'
    }
    // 清除旧 key 再赋值
    Object.keys(acceptLocations).forEach(k => delete acceptLocations[k])
    Object.assign(acceptLocations, locs)
    acceptDialogVisible.value = true
  } catch (e) {
    ElMessage.error('加载任务包详情失败')
  }
}

async function handleConfirmAccept() {
  const pkg = acceptPkg.value
  if (!pkg) return

  acceptLoading.value = true
  try {
    await request.post(`/tasks/packages/${pkg.package_no}/accept`, {
      acceptance_note: acceptNote.value,
      detection_locations: { ...acceptLocations },
      sample_condition: acceptSampleCondition.value,
    })
    ElMessage.success('任务包已接收，可以开始实验')
    acceptDialogVisible.value = false
    loadPackages(activeTab.value === 'all' ? '' : statusFilters[activeTab.value])
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '接收失败')
  } finally {
    acceptLoading.value = false
  }
}

onMounted(() => loadPackages(''))

// ============ 新建任务包 ============
const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = ref({
  commission_no: '',
  group_id: null,
  experiment_codes: [],
  assignee: '',
  reviewer: '',
  detection_locations: {},
})

// 可选数据
const commissions = ref([])       // 委托列表（含客户名）
const selectedCommission = ref(null)
const sampleGroups = ref([])      // 当前委托下的样品组
const experimentMethods = ref([])
const testers = ref([])
const reviewers = ref([])
const qualityInspectors = ref([])

async function openCreateDialog() {
  try {
    const [commRes, emRes, userRes] = await Promise.all([
      request.get('/commissions', { params: { limit: 100 } }),
      request.get('/config/methods'),
      request.get('/users'),
    ])
    commissions.value = commRes.data || []
    experimentMethods.value = emRes.data || []
    const users = userRes.data || []
    testers.value = users.filter(u => u.role === '实验员')
    reviewers.value = users.filter(u => u.role === '复核员')
    qualityInspectors.value = users.filter(u => u.role === '质量负责人')

    createForm.value = {
      commission_no: '', group_id: null, experiment_codes: [],
      assignee: '', reviewer: '', quality_inspector: '', detection_locations: {},
    }
    selectedCommission.value = null
    sampleGroups.value = []
    showCreateDialog.value = true
  } catch (e) {
    ElMessage.error('加载表单数据失败')
  }
}

// 当选择委托后，加载其样品组
async function onCommissionChange(cno) {
  createForm.value.group_id = null
  createForm.value.experiment_codes = []
  sampleGroups.value = []

  if (!cno) {
    selectedCommission.value = null
    return
  }

  const comm = commissions.value.find(c => c.commission_no === cno)
  selectedCommission.value = comm

  try {
    const { data: detail } = await request.get(`/commissions/${cno}`)
    sampleGroups.value = (detail.sample_groups || []).map(g => {
      // 解析样品组预设的检测项目
      const presetCodes = g.experiment_codes
        ? g.experiment_codes.split(',').map(s => s.trim()).filter(Boolean)
        : []
      return {
        ...g,
        preset_codes: presetCodes,
        label: `${g.group_no} — ${g.material_name} (${g.quantity || g.sample_count || '?'}件)`,
        value: g.id,
      }
    })
  } catch {
    sampleGroups.value = []
  }
}

// 选择样品组后自动勾选检测项目
function onGroupChange(gid) {
  if (!gid) {
    createForm.value.experiment_codes = []
    return
  }
  const group = sampleGroups.value.find(g => g.id === gid)
  if (group && group.preset_codes.length > 0) {
    createForm.value.experiment_codes = [...group.preset_codes]
  }
}

async function handleCreate() {
  const f = createForm.value
  if (!f.commission_no) { ElMessage.warning('请选择委托单'); return }
  if (!f.group_id) { ElMessage.warning('请选择样品组'); return }
  if (!f.experiment_codes.length) { ElMessage.warning('请选择检测项目'); return }
  if (!f.assignee) { ElMessage.warning('请选择实验员'); return }

  creating.value = true
  try {
    const resp = await request.post('/tasks/packages', {
      group_id: f.group_id,
      experiment_codes: f.experiment_codes,
      assignee: f.assignee,
      reviewer: f.reviewer || '',
      quality_inspector: f.quality_inspector || '',
      detection_locations: f.detection_locations,
    })
    const data = resp.data || resp
    ElMessage.success(`任务包创建成功 — 复核员: ${data.reviewer || '自动匹配'}, 质量负责人: ${data.quality_inspector || '待指定'}`)
    showCreateDialog.value = false
    createForm.value = { commission_no: '', group_id: null, experiment_codes: [], assignee: '', reviewer: '', quality_inspector: '', detection_locations: {} }
    loadPackages('')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>任务包管理</h1>
      <el-button v-if="canManage" type="primary" @click="openCreateDialog">+ 新建任务包</el-button>
    </div>

    <el-card>
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="待接收" name="pending" />
        <el-tab-pane label="检测中" name="testing" />
        <el-tab-pane label="待复核" name="reviewing" />
        <el-tab-pane label="已完成" name="done" />
      </el-tabs>

      <el-table :data="packages" v-loading="loading" stripe @row-click="viewPackage" style="cursor:pointer">
        <el-table-column prop="package_no" label="任务包编号" width="220" />
        <el-table-column prop="commission_no" label="委托编号" width="180" />
        <el-table-column prop="material_name" label="材料" width="150" />
        <el-table-column prop="experiments" label="检测项目" min-width="180" />
        <el-table-column prop="assignee" label="实验员" width="100" />
        <el-table-column prop="reviewer" label="复核员" width="100" />
        <el-table-column prop="assigned_by" label="分配人" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag
              :type="row.status === '已完成' ? 'success' : row.status === '检测中' ? 'warning' : 'info'"
              size="small"
            >{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="assigned_at" label="分配时间" width="160" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="isTester && row.assignee === currentUser && row.status === '待接收'"
              type="primary"
              size="small"
              @click.stop="openAcceptDialog(row)"
            >接收</el-button>
            <el-button
              v-else-if="isTester && row.assignee === currentUser && row.status === '检测中'"
              size="small"
              type="warning"
              @click.stop="router.push('/my-tasks')"
            >去实验</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建任务包对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建任务包" width="620px" :close-on-click-modal="false">
      <el-form :model="createForm" label-width="100px">
        <!-- 第一步：选择委托 -->
        <el-form-item label="委托单" required>
          <el-select
            v-model="createForm.commission_no"
            placeholder="请先选择委托单"
            filterable
            style="width:100%"
            @change="onCommissionChange"
          >
            <el-option
              v-for="c in commissions"
              :key="c.commission_no"
              :label="`${c.commission_no} — ${c.client_name}`"
              :value="c.commission_no"
            />
          </el-select>
        </el-form-item>

        <!-- 委托信息摘要 -->
        <div v-if="selectedCommission" class="commission-summary">
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="委托编号">{{ selectedCommission.commission_no }}</el-descriptions-item>
            <el-descriptions-item label="委托方">{{ selectedCommission.client_name }}</el-descriptions-item>
            <el-descriptions-item label="生产单位">{{ selectedCommission.production_org_name }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ selectedCommission.status }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 第二步：选择样品组 -->
        <el-form-item label="样品组" required>
          <el-select
            v-model="createForm.group_id"
            placeholder="请先选择委托单"
            filterable
            style="width:100%"
            :disabled="!createForm.commission_no"
            @change="onGroupChange"
          >
            <el-option
              v-for="g in sampleGroups"
              :key="g.id"
              :label="g.label"
              :value="g.id"
            />
          </el-select>
        </el-form-item>

        <!-- 第三步：检测项目（自动从委托样品组带入）-->
        <el-form-item label="检测项目" required>
          <el-select
            v-model="createForm.experiment_codes"
            placeholder="选择样品组后自动填充"
            multiple
            filterable
            style="width:100%"
            disabled
          >
            <el-option
              v-for="m in experimentMethods"
              :key="m.experiment_code"
              :label="`${m.experiment_code} ${m.experiment_name} (${m.method_code})`"
              :value="m.experiment_code"
            />
          </el-select>
        </el-form-item>

        <!-- 第四步：分配人员 -->
        <el-form-item label="实验员" required>
          <el-select v-model="createForm.assignee" placeholder="选择实验员" filterable style="width:100%">
            <el-option
              v-for="u in testers"
              :key="u.username"
              :label="`${u.display_name || u.username} (${u.username})`"
              :value="u.username"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="复核员">
          <el-select v-model="createForm.reviewer" placeholder="留空自动匹配" clearable filterable style="width:100%">
            <el-option
              v-for="u in reviewers"
              :key="u.username"
              :label="`${u.display_name || u.username} (${u.username})`"
              :value="u.username"
            />
          </el-select>
          <div style="font-size:11px;color:#94A3B8;margin-top:2px">留空则由系统自动匹配工作量最低的复核员（排除实验员本人）</div>
        </el-form-item>

        <el-form-item label="质量负责人">
          <el-select v-model="createForm.quality_inspector" placeholder="留空自动匹配" clearable filterable style="width:100%">
            <el-option
              v-for="u in qualityInspectors"
              :key="u.username"
              :label="`${u.display_name || u.username} (${u.username})`"
              :value="u.username"
            />
          </el-select>
          <div style="font-size:11px;color:#94A3B8;margin-top:2px">留空则由系统自动匹配工作量最低的质量负责人（排除实验员+复核员）</div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">创建任务包</el-button>
      </template>
    </el-dialog>

    <!-- 接收任务包对话框 — 逐实验选择检测位置 + 样品确认 -->
    <el-dialog v-model="acceptDialogVisible" title="接收任务包 — 逐实验确认" width="640px" :close-on-click-modal="false">
      <div v-if="acceptTasks.length" style="margin-bottom:20px">
        <!-- 样品实物接收确认 -->
        <div style="margin-bottom:18px">
          <div style="font-weight:600;margin-bottom:8px;font-size:14px">样品实物接收确认</div>
          <el-radio-group v-model="acceptSampleCondition">
            <el-radio v-for="cond in SAMPLE_CONDITIONS" :key="cond" :value="cond" style="display:block;margin-bottom:6px">{{ cond }}</el-radio>
          </el-radio-group>
        </div>

        <!-- 逐实验选择检测位置 -->
        <div style="margin-bottom:18px">
          <div style="font-weight:600;margin-bottom:8px;font-size:14px">逐实验选择检测位置</div>
          <div style="font-size:12px;color:#94A3B8;margin-bottom:10px">每个实验独立选择，允许同一任务包内的实验使用不同检测位置。</div>
          <el-row :gutter="16">
            <el-col :span="12" v-for="t in acceptTasks" :key="t.task_no" style="margin-bottom:12px">
              <div style="font-size:13px;color:#475569;margin-bottom:3px">{{ t.experiment }}｜{{ t.method_code }}</div>
              <el-select v-model="acceptLocations[t.task_no]" style="width:100%" size="small">
                <el-option v-for="loc in DETECTION_LOCATIONS" :key="loc" :label="loc" :value="loc" />
              </el-select>
            </el-col>
          </el-row>
        </div>

        <!-- 备注 -->
        <div>
          <div style="font-weight:600;margin-bottom:6px;font-size:14px">领用/异常备注</div>
          <el-input v-model="acceptNote" type="textarea" :rows="2" placeholder="可选备注" />
        </div>
      </div>

      <template #footer>
        <el-button @click="acceptDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmAccept" :loading="acceptLoading">确认整组样品领用</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { max-width: 1300px; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }

.commission-summary {
  margin-bottom: 18px;
  padding: 12px;
  background: #F0F9FF;
  border-radius: 8px;
  border: 1px solid #BAE6FD;
}
</style>
