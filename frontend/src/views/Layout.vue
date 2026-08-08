<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import request from '../utils/request'
import {
  DataBoard, Document, UserFilled, Files, Folder,
  ArrowLeft, ArrowRight, SwitchButton, HomeFilled,
  Collection, Notebook, Checked, Clock, Van, Box,
  Cpu, Monitor, Bell, Warning, ChatLineSquare, Delete, Lock,
  EditPen, Tools
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isCollapsed = ref(false)
const unreadCount = ref(0)

// ── 菜单名 → 路由路径 + 图标（含所有页面） ──
const allMenus = {
  '首页看板':            { icon: DataBoard, path: '/dashboard' },
  '委托与样品管理':        { icon: Files,     path: '/commissions' },
  '新建委托与入库':        { icon: Van,       path: '/commissions/create' },
  '我的任务包':           { icon: Box,       path: '/task-packages' },
  '任务包分配':           { icon: Box,       path: '/task-packages' },
  '实验记录':             { icon: Notebook,  path: '/my-tasks' },
  '我的任务':             { icon: Notebook,  path: '/my-tasks' },
  '原始记录复核':          { icon: Checked,   path: '/pending-reviews' },
  '报告中心':             { icon: Collection, path: '/reports' },
  '报告发放管理':          { icon: Document,  path: '/report-delivery' },
  '单位信息库':            { icon: Folder,    path: '/organizations' },
  '检测项目与方法库':       { icon: Monitor,   path: '/methods' },
  '样品资料库':            { icon: Box,       path: '/catalog' },
  '设备库':               { icon: Cpu,       path: '/equipment' },
  '用户与权限':            { icon: UserFilled, path: '/users' },
  '附件与内部追溯':         { icon: Files,     path: '/traceability' },
  '一键下载':             { icon: Document,  path: '/batch-download' },
  '单据中心':             { icon: Collection, path: '/documents' },
  '客户异议':             { icon: ChatLineSquare, path: '/objections' },
  '设备故障处置':          { icon: Warning,   path: '/incidents' },
  'SOP与模板版本':         { icon: Document,  path: '/templates' },
  '实验配置版本':          { icon: Monitor,   path: '/methods' },
  '审计追踪':             { icon: Lock,      path: '/audit-trail' },
  '样品借出与归还':         { icon: Van,       path: '/sample-return' },
  '危废处理登记':          { icon: Delete,    path: '/hazardous-waste' },
  '回库确认':             { icon: Checked,   path: '/return-confirm' },
  '通知中心':             { icon: Bell,      path: '/notifications' },
  '电子签名':             { icon: EditPen,   path: '/signatures' },
  '修改中心':             { icon: Clock,     path: '/modifications' },
  '系统初始化':           { icon: Tools,     path: '/system' },
}

// ── 菜单分组结构 ──
const menuGroups = computed(() => {
  const role = auth.user?.role || ''
  const menus = auth.menus || []

  const groups = []

  // 工作台
  const ws = ['首页看板']
  if (menus.includes('报告中心')) ws.push('报告中心')
  if (menus.includes('报告发放管理')) ws.push('报告发放管理')
  if (menus.includes('客户异议')) ws.push('客户异议')
  if (menus.includes('设备故障处置')) ws.push('设备故障处置')
  if (menus.includes('通知中心')) ws.push('通知中心')
  if (ws.length > 1 || (ws.length === 1 && menus.includes(ws[0]))) groups.push({ label: '工作台', items: ws.filter(m => menus.includes(m)) })

  // 业务与追溯
  const biz = ['委托与样品管理', '新建委托与入库', '任务包分配', '我的任务包', '实验记录', '我的任务',
               '原始记录复核', '样品借出与归还', '回库确认', '危废处理登记',
               '单据中心', '一键下载', '附件与内部追溯', '修改中心']
  const bizFiltered = biz.filter(m => menus.includes(m))
  if (bizFiltered.length) groups.push({ label: '业务与追溯', items: bizFiltered })

  // 基础配置
  const cfg = ['单位信息库', '检测项目与方法库', '样品资料库', '设备库',
               'SOP与模板版本', '实验配置版本', '电子签名']
  const cfgFiltered = cfg.filter(m => menus.includes(m))
  if (cfgFiltered.length) groups.push({ label: '基础配置', items: cfgFiltered })

  // 系统管理
  const sys = ['用户与权限', '审计追踪', '系统初始化']
  const sysFiltered = sys.filter(m => menus.includes(m))
  if (sysFiltered.length) groups.push({ label: '系统管理', items: sysFiltered })

  // 构建带分组的菜单项列表
  const result = []
  for (const g of groups) {
    result.push({ __isGroup: true, label: g.label })
    for (const title of g.items) {
      if (allMenus[title]) {
        result.push({
          title,
          icon: allMenus[title].icon,
          path: allMenus[title].path,
        })
      }
    }
  }
  return result
})

// 扁平化菜单列表（用于 activeMenuIndex 计算）
const visibleMenus = computed(() => {
  return menuGroups.value.filter(m => !m.__isGroup)
})

// 根据当前路由反查应高亮的菜单项（用标题作唯一标识，避免同路径菜单项一起高亮）
const activeMenuIndex = computed(() => {
  const currentPath = route.path
  // 精确匹配优先
  const exact = visibleMenus.value.find(m => m.path === currentPath)
  if (exact) return exact.title
  // 前缀匹配（处理带参数的路由）
  const prefix = visibleMenus.value.find(m => currentPath.startsWith(m.path + '/'))
  if (prefix) return prefix.title
  // 动态路由匹配（如 /commissions/WT20260807001）
  const fuzzy = visibleMenus.value.find(m => {
    const base = m.path.replace(/\/[^/]+$/, '')  // 去掉最后一段
    return base && currentPath.startsWith(base)
  })
  return fuzzy ? fuzzy.title : (visibleMenus.value[0]?.title || '')
})

function handleMenuSelect(index) {
  const menu = visibleMenus.value.find(m => m.title === index)
  if (menu && menu.path !== route.path) {
    router.push(menu.path)
  }
}

function handleCommand(cmd) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  } else if (cmd === 'notifications') {
    router.push('/notifications')
  }
}

// 定时拉取未读通知数
async function fetchUnread() {
  try {
    const { data } = await request.get('/notifications')
    unreadCount.value = Array.isArray(data) ? data.length : 0
  } catch { /* ignore */ }
}
onMounted(() => { fetchUnread(); setInterval(fetchUnread, 60000) })
</script>

<template>
  <el-container class="layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="sidebar">
      <div class="sidebar-header">
        <div class="logo-area" :class="{ collapsed: isCollapsed }">
          <svg viewBox="0 0 40 40" width="36" height="36">
            <rect width="40" height="40" rx="10" fill="url(#lg2)"/>
            <path d="M10 25V15l9 5-9 5z" fill="#fff" opacity=".9"/>
            <path d="M19 25V15l9 5-9 5z" fill="#fff" opacity=".7"/>
            <defs><linearGradient id="lg2" x1="0" y1="0" x2="40" y2="40"><stop stop-color="#2563EB"/><stop offset="1" stop-color="#60A5FA"/></linearGradient></defs>
          </svg>
          <span v-if="!isCollapsed" class="logo-text">BPLab Trace</span>
        </div>
      </div>

      <el-menu
        :default-active="activeMenuIndex"
        :collapse="isCollapsed"
        :collapse-transition="false"
        background-color="#1E3A5F"
        text-color="rgba(255,255,255,.65)"
        active-text-color="#fff"
        @select="handleMenuSelect"
      >
        <template v-for="m in menuGroups" :key="m.__isGroup ? `g-${m.label}` : m.title">
          <!-- 分组标题 -->
          <div v-if="m.__isGroup && !isCollapsed" class="menu-group-label">{{ m.label }}</div>
          <el-menu-item
            v-else-if="!m.__isGroup"
            :index="m.title"
          >
            <el-icon><component :is="m.icon" /></el-icon>
            <template #title>
              {{ m.title }}
              <el-badge v-if="m.title === '通知中心' && unreadCount" :value="unreadCount" style="margin-left:8px" />
            </template>
          </el-menu-item>
        </template>
      </el-menu>

      <div class="sidebar-footer">
        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-info">
            <el-avatar :size="32" :icon="UserFilled" />
            <span v-if="!isCollapsed" class="user-name">{{ auth.user?.display_name }}</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>
                {{ auth.user?.role }} · {{ auth.user?.username }}
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon> 退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-aside>

    <!-- 主区域 -->
    <el-container>
      <el-header class="topbar">
        <div class="topbar-left">
          <el-button
            :icon="isCollapsed ? ArrowRight : ArrowLeft"
            text
            @click="isCollapsed = !isCollapsed"
          />
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">
              <el-icon><HomeFilled /></el-icon> 首页
            </el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.title">{{ route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="topbar-right">
          <el-badge :value="unreadCount" :hidden="!unreadCount" style="margin-right:16px;cursor:pointer" @click="router.push('/notifications')">
            <el-icon :size="20"><Bell /></el-icon>
          </el-badge>
          <span class="version-tag">BPLab Trace V11</span>
        </div>
      </el-header>

      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100vh;
}

.sidebar {
  background: #1E3A5F;
  display: flex;
  flex-direction: column;
  transition: width .2s;
  overflow: hidden;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid rgba(255,255,255,.08);
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-area.collapsed {
  justify-content: center;
}

.logo-text {
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  white-space: nowrap;
}

.el-menu {
  flex: 1;
  border-right: none;
  overflow-y: auto;
  overflow-x: hidden;
}

.menu-group-label {
  padding: 12px 20px 4px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: rgba(255,255,255,.35);
  font-weight: 600;
  white-space: nowrap;
  user-select: none;
}

.el-menu-item {
  margin: 2px 8px;
  border-radius: 8px;
}

.el-menu-item.is-active {
  background: rgba(37,99,235,.5) !important;
}

.el-menu-item:hover {
  background: rgba(255,255,255,.08) !important;
}

/* 侧边栏滚动条样式 */
.el-menu::-webkit-scrollbar {
  width: 4px;
}

.el-menu::-webkit-scrollbar-track {
  background: transparent;
}

.el-menu::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,.15);
  border-radius: 2px;
}

.el-menu::-webkit-scrollbar-thumb:hover {
  background: rgba(255,255,255,.3);
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid rgba(255,255,255,.08);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 8px;
  transition: background .2s;
}

.user-info:hover {
  background: rgba(255,255,255,.08);
}

.user-name {
  color: rgba(255,255,255,.8);
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 顶栏 */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #E2E8F0;
  padding: 0 20px;
  height: 56px;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.topbar-right {
  display: flex;
  align-items: center;
}

.version-tag {
  font-size: 12px;
  color: #94A3B8;
  background: #F1F5F9;
  padding: 2px 10px;
  border-radius: 10px;
}

.el-main {
  background: #F8FAFC;
  padding: 24px;
}
</style>
