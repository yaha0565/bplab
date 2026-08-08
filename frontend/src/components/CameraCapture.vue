<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { Camera, Switch, VideoPause, Upload } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: File, default: null },
  previewUrl: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'update:previewUrl', 'capture'])

// ── 摄像头状态 ──
const stream = ref(null)
const videoRef = ref(null)
const canvasRef = ref(null)
const fileInputRef = ref(null)

const isCameraActive = ref(false)
const cameraError = ref('')
const availableCameras = ref([])       // [{deviceId, label, facing}]
const currentFacing = ref('environment') // 'user'=前置, 'environment'=后置
const capturing = ref(false)

// ── 检测设备类型 ──
function isMobile() {
  return /Android|iPhone|iPad|iPod|webOS/i.test(navigator.userAgent) ||
    ('ontouchstart' in window && window.innerWidth < 1024)
}

// ── 枚举摄像头 ──
async function enumCameras() {
  try {
    // 需要先请求一次权限才能拿到 label
    const devices = await navigator.mediaDevices.enumerateDevices()
    availableCameras.value = devices
      .filter(d => d.kind === 'videoinput')
      .map(d => {
        // 推断方向：label 中包含 front/user/前置 → 前置，rear/back/environment/后置 → 后置
        const label = (d.label || '').toLowerCase()
        let facing = 'unknown'
        if (/front|user|前置|正面/.test(label)) facing = 'user'
        else if (/rear|back|environment|后置|背面|顶部/.test(label)) facing = 'environment'
        else if (/integrated|built-in|内建|内置/.test(label)) facing = 'user'
        return { deviceId: d.deviceId, label: d.label || `摄像头 ${availableCameras.value.length + 1}`, facing }
      })

    // 默认方向：PC 用前置，手机用后置
    if (availableCameras.value.length > 1) {
      currentFacing.value = isMobile() ? 'environment' : 'user'
    } else if (availableCameras.value.length === 1) {
      currentFacing.value = availableCameras.value[0].facing !== 'environment' ? 'user' : 'environment'
    }
  } catch {
    availableCameras.value = []
  }
}

// ── 选择当前方向的设备 ID ──
function currentDeviceId() {
  const match = availableCameras.value.find(c => c.facing === currentFacing.value)
  if (match) return match.deviceId
  // fallback：没有匹配 facing 时取第一个
  if (availableCameras.value.length > 0) return availableCameras.value[0].deviceId
  return undefined
}

// ── 启动摄像头 ──
async function startCamera() {
  cameraError.value = ''
  const deviceId = currentDeviceId()
  const constraints = {
    video: {
      ...(deviceId ? { deviceId: { exact: deviceId } } : {}),
      facingMode: currentFacing.value === 'user' ? 'user' : 'environment',
      width: { ideal: 1920 },
      height: { ideal: 1080 },
    },
    audio: false,
  }
  try {
    const s = await navigator.mediaDevices.getUserMedia(constraints)
    stream.value = s
    if (videoRef.value) {
      videoRef.value.srcObject = s
      await videoRef.value.play()
    }
    isCameraActive.value = true
  } catch (err) {
    // 如果 exact deviceId 失败，用 facingMode 重试
    if (deviceId && err.name === 'OverconstrainedError') {
      try {
        const s2 = await navigator.mediaDevices.getUserMedia({ video: { facingMode: currentFacing.value }, audio: false })
        stream.value = s2
        if (videoRef.value) {
          videoRef.value.srcObject = s2
          await videoRef.value.play()
        }
        isCameraActive.value = true
        return
      } catch {}
    }
    cameraError.value = '无法访问摄像头: ' + (err.message || err.name)
  }
}

// ── 停止摄像头 ──
function stopCamera() {
  if (stream.value) {
    stream.value.getTracks().forEach(t => t.stop())
    stream.value = null
  }
  isCameraActive.value = false
}

// ── 切换前后摄像头 ──
function switchCamera() {
  currentFacing.value = currentFacing.value === 'user' ? 'environment' : 'user'
  stopCamera()
  startCamera()
}

// ── 拍照 ──
function takePhoto() {
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas) return

  capturing.value = true
  const ctx = canvas.getContext('2d')
  canvas.width = video.videoWidth || 1280
  canvas.height = video.videoHeight || 720
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

  canvas.toBlob((blob) => {
    if (!blob) { capturing.value = false; return }
    const file = new File([blob], `camera_${Date.now()}.jpg`, { type: 'image/jpeg' })
    const url = URL.createObjectURL(blob)
    emit('update:modelValue', file)
    emit('update:previewUrl', url)
    emit('capture', { file, previewUrl: url })
    capturing.value = false
    stopCamera()
  }, 'image/jpeg', 0.9)
}

// ── 文件上传回退 ──
function handleFileInput(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const url = URL.createObjectURL(file)
  emit('update:modelValue', file)
  emit('update:previewUrl', url)
  emit('capture', { file, previewUrl: url })
}

// ── 触发文件选择 ──
function triggerFileInput() {
  fileInputRef.value?.click()
}

// ── 初始化 ──
onMounted(async () => {
  await enumCameras()
})

onBeforeUnmount(() => {
  stopCamera()
})
</script>

<template>
  <div class="camera-capture">
    <!-- 已有照片预览 -->
    <div v-if="previewUrl" class="preview-wrap">
      <img :src="previewUrl" class="preview-img" />
      <div class="preview-actions">
        <el-button size="small" @click="startCamera">重拍</el-button>
        <el-button size="small" type="danger" @click="emit('update:previewUrl', ''); emit('update:modelValue', null)">删除</el-button>
      </div>
    </div>

    <!-- 摄像头预览 -->
    <div v-else-if="isCameraActive" class="camera-preview">
      <video ref="videoRef" class="video-feed" autoplay playsinline muted />
      <canvas ref="canvasRef" style="display:none" />
      <div class="camera-controls">
        <el-button
          v-if="availableCameras.length > 1"
          circle :icon="Switch"
          @click="switchCamera"
          title="切换前后摄像头"
        />
        <el-button type="primary" circle class="capture-btn" :loading="capturing" @click="takePhoto" title="拍照">
          <span class="capture-dot" v-if="!capturing" />
        </el-button>
        <el-button circle :icon="VideoPause" @click="stopCamera" title="关闭摄像头" />
      </div>
      <div class="facing-hint">{{ currentFacing === 'user' ? '前置' : '后置' }}摄像头</div>
    </div>

    <!-- 启动/上传选择 -->
    <div v-else class="capture-actions">
      <div v-if="cameraError" class="error-msg">{{ cameraError }}</div>
      <el-button type="primary" :icon="Camera" @click="startCamera" :disabled="!('mediaDevices' in navigator)">
        拍照
      </el-button>
      <el-button :icon="Upload" @click="triggerFileInput">上传照片</el-button>
      <input ref="fileInputRef" type="file" accept="image/*" style="display:none" @change="handleFileInput" />
    </div>
  </div>
</template>

<style scoped>
.camera-capture { width: 100%; }

.preview-wrap { position: relative; }
.preview-img {
  width: 100%;
  max-height: 200px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #E2E8F0;
}
.preview-actions {
  display: flex; gap: 6px; margin-top: 6px; justify-content: center;
}

.camera-preview {
  position: relative;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}
.video-feed {
  width: 100%;
  display: block;
  max-height: 300px;
  object-fit: contain;
  background: #0F172A;
}
.camera-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 10px 0;
  background: rgba(0,0,0,0.85);
}
.capture-btn {
  width: 56px !important;
  height: 56px !important;
  border: 3px solid #fff !important;
  background: transparent !important;
}
.capture-dot {
  display: inline-block;
  width: 38px; height: 38px;
  border-radius: 50%;
  background: #fff;
}
.facing-hint {
  position: absolute; top: 8px; right: 12px;
  background: rgba(0,0,0,0.6); color: #fff;
  padding: 2px 8px; border-radius: 4px;
  font-size: 12px;
}

.capture-actions {
  display: flex; gap: 8px; flex-wrap: wrap;
  justify-content: center; padding: 10px 0;
}
.error-msg {
  width: 100%; text-align: center;
  color: #EF4444; font-size: 12px; margin-bottom: 4px;
}
</style>
