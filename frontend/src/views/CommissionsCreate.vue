<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import request from '../utils/request'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const organizations = ref([])
const methods = ref([])

const form = reactive({
  client_org_id: null,
  production_org_id: null,
  production_relation: '客户提供',
  commission_date: new Date().toISOString().slice(0, 10),
  due_date: '',
  notes: '',
})

// 样品组列表
const sampleGroups = ref([{
  material_name: '',
  sample_count: 1,
  experiment_codes: [],
  batch_no: '',
  heat_no: '',
}])

const relations = ['客户提供', '自产', '外协', '合同制造']

onMounted(async () => {
  const [orgs, mtds] = await Promise.all([
    request.get('/organizations', { params: { limit: 500 } }),
    request.get('/methods'),
  ])
  organizations.value = orgs.data
  methods.value = mtds.data
})

function addSampleGroup() {
  sampleGroups.value.push({
    material_name: '',
    sample_count: 1,
    experiment_codes: [],
    batch_no: '',
    heat_no: '',
  })
}

function removeSampleGroup(index) {
  if (sampleGroups.value.length <= 1) {
    ElMessage.warning('至少保留一个样品组')
    return
  }
  sampleGroups.value.splice(index, 1)
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  // 验证至少一个样品组填写了材料
  const validGroups = sampleGroups.value.filter(g => g.material_name.trim())
  if (!validGroups.length) {
    ElMessage.warning('请至少填写一个样品组的材料名称')
    return
  }

  loading.value = true
  try {
    // 1. 创建委托
    const commRes = await request.post('/commissions', form)
    const commissionNo = commRes.data.commission_no
    ElMessage.success(`委托 ${commissionNo} 创建成功`)

    // 2. 逐个创建样品组
    let groupCount = 0
    for (const g of validGroups) {
      try {
        const expNames = g.experiment_codes
          .map(code => methods.value.find(m => m.experiment_code === code)?.experiment_name || code)

        await request.post(`/commissions/${commissionNo}/sample-groups`, {
          material_name: g.material_name,
          sample_count: g.sample_count,
          experiment_codes: g.experiment_codes,
          experiments: expNames,
          batch_no: g.batch_no || null,
          heat_no: g.heat_no || null,
        })
        groupCount++
      } catch (e) {
        ElMessage.error(`样品组「${g.material_name}」创建失败: ${e.response?.data?.detail || e}`)
      }
    }

    if (groupCount > 0) {
      ElMessage.success(`已创建 ${groupCount} 个样品组`)
    }

    router.push(`/commission/${commissionNo}`)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>新建委托与样品入库</h1>
    </div>

    <el-card>
      <el-form ref="formRef" :model="form" label-width="120px" style="max-width:900px">
        <!-- ===== 委托基本信息 ===== -->
        <el-divider content-position="left">
          <span style="font-weight:600">委托基本信息</span>
        </el-divider>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="委托日期" prop="commission_date" :rules="[{required:true,message:'请选择日期'}]">
              <el-date-picker v-model="form.commission_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="要求完成日期" prop="due_date">
              <el-date-picker v-model="form.due_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">客户与生产信息</el-divider>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="委托方（客户）" prop="client_org_id" :rules="[{required:true,message:'请选择客户'}]">
              <el-select v-model="form.client_org_id" filterable placeholder="选择客户单位" style="width:100%">
                <el-option v-for="o in organizations.filter(o=>o.is_client)" :key="o.id" :label="o.org_name" :value="o.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="生产单位" prop="production_org_id" :rules="[{required:true,message:'请选择生产单位'}]">
              <el-select v-model="form.production_org_id" filterable placeholder="选择生产单位" style="width:100%">
                <el-option v-for="o in organizations" :key="o.id" :label="o.org_name" :value="o.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="生产关系">
          <el-select v-model="form.production_relation" style="width:100%">
            <el-option v-for="r in relations" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>

        <!-- ===== 样品组 ===== -->
        <el-divider content-position="left">
          <span style="font-weight:600">样品组</span>
          <span style="font-size:12px;color:#94A3B8;margin-left:8px">
            一个委托可包含多种样品，每种样品可做多项检测
          </span>
        </el-divider>

        <div
          v-for="(sg, idx) in sampleGroups"
          :key="idx"
          style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:16px;margin-bottom:12px"
        >
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <span style="font-weight:600;color:#0F172A">样品组 {{ idx + 1 }}</span>
            <el-button
              v-if="sampleGroups.length > 1"
              text type="danger"
              :icon="Delete"
              @click="removeSampleGroup(idx)"
            >移除</el-button>
          </div>

          <el-row :gutter="16">
            <el-col :span="14">
              <el-form-item label="材料名称">
                <el-input v-model="sg.material_name" placeholder="如 TC4钛合金、316L不锈钢" />
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <el-form-item label="数量">
                <el-input-number v-model="sg.sample_count" :min="1" :max="200" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="批号">
                <el-input v-model="sg.batch_no" placeholder="选填" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="检测项目">
            <el-select
              v-model="sg.experiment_codes"
              placeholder="选择检测项目（可多选）"
              multiple
              filterable
              style="width:100%"
            >
              <el-option
                v-for="m in methods"
                :key="m.experiment_code"
                :label="`${m.experiment_code} ${m.experiment_name} (${m.method_code})`"
                :value="m.experiment_code"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="炉号">
            <el-input v-model="sg.heat_no" placeholder="选填" style="max-width:300px" />
          </el-form-item>
        </div>

        <el-button text type="primary" :icon="Plus" @click="addSampleGroup" style="margin-bottom:16px">
          添加样品组
        </el-button>

        <!-- ===== 备注 ===== -->
        <el-divider content-position="left">备注</el-divider>

        <el-form-item label="备注" prop="notes">
          <el-input v-model="form.notes" type="textarea" :rows="3" placeholder="委托备注信息" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSubmit" :icon="Plus" size="large">
            创建委托并入库样品
          </el-button>
          <el-button @click="router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.page { max-width: 960px; }
.page-header { margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; }
</style>
