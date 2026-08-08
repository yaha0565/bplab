<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'
import { User, Lock, Loading } from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref(null)
const loading = ref(false)
const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    router.push('/dashboard')
  } catch (e) {
    const msg = e?.response?.data?.detail || '登录失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <!-- 左侧品牌面板 -->
    <div class="login-left">
      <div class="brand-content">
        <div class="brand-logo">
          <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="48" height="48" rx="12" fill="url(#lg)"/>
            <path d="M14 30V18l10 6-10 6z" fill="#fff" opacity=".9"/>
            <path d="M24 30V18l10 6-10 6z" fill="#fff" opacity=".7"/>
            <defs><linearGradient id="lg" x1="0" y1="0" x2="48" y2="48"><stop stop-color="#2563EB"/><stop offset="1" stop-color="#60A5FA"/></linearGradient></defs>
          </svg>
          <span class="brand-name">BPLab Trace</span>
        </div>
        <h1>实验室信息管理系统</h1>
        <p>专业的检测流程管理 · 全链路数据追溯 · 合规审计支持</p>
        <!-- 实验室 SVG 插画 -->
        <div class="lab-illustration">
          <svg viewBox="0 0 400 200" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- 显微镜 -->
            <g transform="translate(60,40)">
              <rect x="0" y="80" width="80" height="10" rx="3" fill="#94A3B8"/>
              <rect x="30" y="30" width="20" height="50" rx="2" fill="#CBD5E1"/>
              <circle cx="40" cy="25" r="12" fill="#E2E8F0" stroke="#94A3B8" stroke-width="2"/>
              <rect x="25" y="90" width="30" height="40" rx="4" fill="#F1F5F9" stroke="#CBD5E1" stroke-width="1.5"/>
              <circle cx="40" cy="115" r="10" fill="#DBEAFE" stroke="#60A5FA" stroke-width="1.5"/>
            </g>
            <!-- 分子结构 -->
            <g transform="translate(220,30)">
              <circle cx="40" cy="20" r="8" fill="#DBEAFE" stroke="#2563EB" stroke-width="2"/>
              <circle cx="20" cy="60" r="8" fill="#DBEAFE" stroke="#2563EB" stroke-width="2"/>
              <circle cx="60" cy="60" r="8" fill="#DBEAFE" stroke="#2563EB" stroke-width="2"/>
              <circle cx="40" cy="100" r="8" fill="#DBEAFE" stroke="#2563EB" stroke-width="2"/>
              <line x1="36" y1="26" x2="24" y2="54" stroke="#93C5FD" stroke-width="2"/>
              <line x1="44" y1="26" x2="56" y2="54" stroke="#93C5FD" stroke-width="2"/>
              <line x1="24" y1="66" x2="36" y2="94" stroke="#93C5FD" stroke-width="2"/>
              <line x1="56" y1="66" x2="44" y2="94" stroke="#93C5FD" stroke-width="2"/>
              <line x1="28" y1="60" x2="52" y2="60" stroke="#93C5FD" stroke-width="2"/>
            </g>
            <!-- 试管 -->
            <g transform="translate(330,50)">
              <rect x="5" y="0" width="8" height="60" rx="4" fill="#DBEAFE" stroke="#60A5FA" stroke-width="1.5"/>
              <rect x="20" y="10" width="8" height="50" rx="4" fill="#EDE9FE" stroke="#A78BFA" stroke-width="1.5"/>
              <rect x="35" y="5" width="8" height="55" rx="4" fill="#D1FAE5" stroke="#34D399" stroke-width="1.5"/>
            </g>
            <!-- 数据图表 -->
            <g transform="translate(20,140)">
              <rect x="0" y="0" width="360" height="50" rx="6" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1"/>
              <rect x="10" y="25" width="40" height="15" rx="2" fill="#BFDBFE"/>
              <rect x="60" y="10" width="40" height="30" rx="2" fill="#2563EB"/>
              <rect x="110" y="20" width="40" height="20" rx="2" fill="#BFDBFE"/>
              <rect x="160" y="5" width="40" height="35" rx="2" fill="#60A5FA"/>
              <rect x="210" y="15" width="40" height="25" rx="2" fill="#BFDBFE"/>
              <rect x="260" y="22" width="40" height="18" rx="2" fill="#93C5FD"/>
              <rect x="310" y="8" width="40" height="32" rx="2" fill="#2563EB"/>
            </g>
          </svg>
        </div>
      </div>
    </div>

    <!-- 右侧登录卡片 -->
    <div class="login-right">
      <div class="login-card">
        <h2>欢迎登录</h2>
        <p class="subtitle">BPLab Trace LIMS V11</p>
        <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="handleLogin">
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              :prefix-icon="User"
              size="large"
            />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              size="large"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              :icon="loading ? Loading : undefined"
              @click="handleLogin"
              class="login-btn"
            >
              {{ loading ? '登录中...' : '登 录' }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  height: 100vh;
  width: 100%;
}

/* 左侧品牌面板 60% */
.login-left {
  flex: 6;
  background: linear-gradient(135deg, #EFF6FF 0%, #BFDBFE 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.login-left::before {
  content: '';
  position: absolute;
  top: -20%;
  right: -10%;
  width: 400px;
  height: 400px;
  border-radius: 50%;
  background: rgba(37, 99, 235, .04);
}

.brand-content {
  text-align: center;
  z-index: 1;
  padding: 40px;
}

.brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 24px;
}

.brand-logo svg {
  width: 48px;
  height: 48px;
}

.brand-name {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #1E3A5F, #2563EB);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.login-left h1 {
  font-size: 26px;
  font-weight: 600;
  color: #1E3A5F;
  margin-bottom: 12px;
}

.login-left p {
  font-size: 15px;
  color: #64748B;
  margin-bottom: 40px;
}

.lab-illustration {
  max-width: 400px;
  margin: 0 auto;
}

.lab-illustration svg {
  width: 100%;
  height: auto;
}

/* 右侧登录卡片 40% */
.login-right {
  flex: 4;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #F8FAFC, #FFF);
}

.login-card {
  width: 360px;
  padding: 40px 36px;
  background: rgba(255,255,255,.8);
  backdrop-filter: blur(16px);
  border-radius: 16px;
  border: 1px solid rgba(226,232,240,.8);
  box-shadow: 0 8px 32px rgba(0,0,0,.06);
}

.login-card h2 {
  font-size: 24px;
  font-weight: 700;
  color: #0F172A;
  text-align: center;
  margin-bottom: 6px;
}

.subtitle {
  text-align: center;
  color: #94A3B8;
  font-size: 13px;
  margin-bottom: 32px;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  letter-spacing: 4px;
  border-radius: 10px;
  background: linear-gradient(135deg, #2563EB, #60A5FA);
  border: none;
  transition: all .2s ease;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(37,99,235,.35);
}

.login-btn:active {
  transform: scale(.97);
}
</style>
