import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      // 首页
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '首页看板' } },

      // 委托管理
      { path: 'commissions', name: 'Commissions', component: () => import('../views/Commissions.vue'), meta: { title: '委托与样品管理' } },
      { path: 'commissions/create', name: 'CommissionsCreate', component: () => import('../views/CommissionsCreate.vue'), meta: { title: '新建委托' } },
      { path: 'commission/:id', name: 'CommissionDetail', component: () => import('../views/CommissionDetail.vue'), meta: { title: '委托详情' } },

      // 任务包 & 实验任务
      { path: 'task-packages', name: 'TaskPackages', component: () => import('../views/TaskPackages.vue'), meta: { title: '任务包管理' } },
      { path: 'task-package/:id', name: 'TaskPackageDetail', component: () => import('../views/TaskPackageDetail.vue'), meta: { title: '任务包详情' } },
      { path: 'my-tasks', name: 'MyTasks', component: () => import('../views/MyTasks.vue'), meta: { title: '我的实验任务' } },
      { path: 'task/:id', name: 'TaskDetail', component: () => import('../views/TaskDetail.vue'), meta: { title: '任务详情' } },
      { path: 'experiment/:taskNo', name: 'ExperimentRun', component: () => import('../views/ExperimentRun.vue'), meta: { title: '实验执行' } },

      // 记录 & 复核
      { path: 'pending-reviews', name: 'PendingReviews', component: () => import('../views/PendingReviews.vue'), meta: { title: '原始记录复核' } },

      // 报告
      { path: 'reports', name: 'ReportsCenter', component: () => import('../views/ReportsCenter.vue'), meta: { title: '报告中心' } },

      // 资料库
      { path: 'organizations', name: 'Organizations', component: () => import('../views/Organizations.vue'), meta: { title: '单位信息库' } },
      { path: 'methods', name: 'ExperimentMethods', component: () => import('../views/ExperimentMethods.vue'), meta: { title: '检测项目与方法库' } },
      { path: 'catalog', name: 'SampleCatalog', component: () => import('../views/SampleCatalog.vue'), meta: { title: '样品资料库' } },
      { path: 'equipment', name: 'EquipmentRegistry', component: () => import('../views/EquipmentRegistry.vue'), meta: { title: '设备库' } },

      // 模板管理
      { path: 'templates', name: 'Templates', component: () => import('../views/Templates.vue'), meta: { title: '模板与文档管理' } },

      // 用户管理
      { path: 'users', name: 'Users', component: () => import('../views/Users.vue'), meta: { title: '用户与权限', role: '管理员' } },

      // 回库确认
      { path: 'return-confirm', name: 'ReturnConfirm', component: () => import('../views/ReturnConfirm.vue'), meta: { title: '回库确认' } },

      // 附件与内部追溯
      { path: 'traceability', name: 'Traceability', component: () => import('../views/Traceability.vue'), meta: { title: '附件与内部追溯' } },

      // 一键下载
      { path: 'batch-download', name: 'BatchDownload', component: () => import('../views/BatchDownload.vue'), meta: { title: '一键下载' } },

      // 设备故障处置
      { path: 'incidents', name: 'EquipmentIncidents', component: () => import('../views/EquipmentIncidents.vue'), meta: { title: '设备故障处置' } },

      // 客户异议
      { path: 'objections', name: 'Objections', component: () => import('../views/Objections.vue'), meta: { title: '客户异议' } },

      // 危废处理
      { path: 'hazardous-waste', name: 'HazardousWaste', component: () => import('../views/HazardousWaste.vue'), meta: { title: '危废处理登记' } },

      // 报告发放
      { path: 'report-delivery', name: 'ReportDelivery', component: () => import('../views/ReportDelivery.vue'), meta: { title: '报告发放管理' } },

      // 样品借出与归还
      { path: 'sample-return', name: 'SampleReturn', component: () => import('../views/SampleReturn.vue'), meta: { title: '样品借出与归还' } },

      // 单据中心
      { path: 'documents', name: 'DocumentCenter', component: () => import('../views/DocumentCenter.vue'), meta: { title: '单据中心' } },

      // 审计追踪
      { path: 'audit-trail', name: 'AuditTrail', component: () => import('../views/AuditTrail.vue'), meta: { title: '审计追踪' } },

      // 通知中心（本地组件）
      { path: 'notifications', name: 'Notifications', component: () => import('../views/Notifications.vue'), meta: { title: '通知中心' } },

      // 电子签名
      { path: 'signatures', name: 'Signatures', component: () => import('../views/Signatures.vue'), meta: { title: '电子签名管理' } },

      // 修改中心
      { path: 'modifications', name: 'ModificationCenter', component: () => import('../views/ModificationCenter.vue'), meta: { title: '修改中心' } },

      // 系统初始化
      { path: 'system', name: 'SystemInit', component: () => import('../views/SystemInit.vue'), meta: { title: '系统初始化' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.public) {
    next()
  } else if (!token) {
    next('/login')
  } else {
    next()
  }
})

export default router
