<script setup>
import { ref, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  checkpoint: { type: Object, required: true },
  sampleNo: { type: String, default: '' },
  cameraHint: { type: String, default: '' },
})

const emit = defineEmits(['photo-taken', 'close'])

const videoRef = ref(null)
const canvasRef = ref(null)
const stream = ref(null)
const isCapturing = ref(false)
const error = ref('')
const facingMode = ref('environment')
const devices = ref([])
const videoReady = ref(false)

function cameraErrorMsg(err) {
  const map = {
    NotAllowedError: '摄像头权限被拒绝，请在浏览器设置中允许访问摄像头',
    NotFoundError: '未检测到摄像头设备',
    NotReadableError: '摄像头被占用，请关闭其他使用摄像头的程序',
    OverconstrainedError: '摄像头不支持所需参数',
    AbortError: '摄像头操作被中止',
  }
  return map[err.name] || `摄像头错误: ${err.message || err.name}`
}

async function start() {
  error.value = ''
  videoReady.value = false

  try {
    const allDevices = await navigator.mediaDevices.enumerateDevices()
    devices.value = allDevices.filter(d => d.kind === 'videoinput')
  } catch { }

  await nextTick()

  try {
    const s = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: facingMode.value, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    })
    stream.value = s
    if (videoRef.value) {
      videoRef.value.srcObject = s
      await new Promise((resolve, reject) => {
        if (!videoRef.value) return reject(new Error('no video'))
        videoRef.value.onloadedmetadata = () => {
          videoRef.value.play().then(resolve).catch(reject)
        }
        setTimeout(() => reject(new Error('视频加载超时')), 5000)
      })
      videoReady.value = true
    }
  } catch (err) {
    if (err.name === 'OverconstrainedError') {
      try {
        const s = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        stream.value = s
        if (videoRef.value) {
          videoRef.value.srcObject = s
          await new Promise((resolve, reject) => {
            videoRef.value.onloadedmetadata = () => {
              videoRef.value.play().then(resolve).catch(reject)
            }
            setTimeout(() => reject(new Error('视频加载超时')), 5000)
          })
          videoReady.value = true
          return
        }
      } catch (fbErr) {
        error.value = cameraErrorMsg(fbErr)
      }
    } else {
      error.value = cameraErrorMsg(err)
    }
  }
}

async function switchCamera() {
  if (stream.value) stream.value.getTracks().forEach(t => t.stop())
  facingMode.value = facingMode.value === 'environment' ? 'user' : 'environment'
  await start()
}

function capture() {
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas || !videoReady.value) return
  isCapturing.value = true
  canvas.width = video.videoWidth || 1280
  canvas.height = video.videoHeight || 720
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

  // Draw timestamp watermark at bottom-right corner
  const now = new Date()
  const ts = now.getFullYear() + '-'
    + String(now.getMonth() + 1).padStart(2, '0') + '-'
    + String(now.getDate()).padStart(2, '0') + ' '
    + String(now.getHours()).padStart(2, '0') + ':'
    + String(now.getMinutes()).padStart(2, '0') + ':'
    + String(now.getSeconds()).padStart(2, '0')
  const fontSize = Math.max(14, Math.round(canvas.width * 0.025))
  ctx.font = `${fontSize}px "Courier New", monospace`
  const metrics = ctx.measureText(ts)
  const textW = metrics.width
  const textH = fontSize * 1.2
  const padX = fontSize * 0.5
  const padY = fontSize * 0.3
  const x = canvas.width - textW - padX * 2 - 8
  const y = canvas.height - textH - padY - 8
  // Semi-transparent dark background
  ctx.fillStyle = 'rgba(0, 0, 0, 0.55)'
  ctx.fillRect(x, y, textW + padX * 2, textH + padY)
  // White text
  ctx.fillStyle = 'rgba(255, 255, 255, 0.92)'
  ctx.textBaseline = 'bottom'
  ctx.fillText(ts, x + padX, y + textH)

  canvas.toBlob((blob) => {
    isCapturing.value = false
    if (!blob) return
    const file = new File([blob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' })
    const url = URL.createObjectURL(blob)
    emit('photo-taken', { file, previewUrl: url, sampleNo: props.sampleNo })
    close()
  }, 'image/jpeg', 0.9)
}

function handleFileInput(e) {
  const file = e.target.files?.[0]
  if (!file) return
  // Draw uploaded image onto canvas to add timestamp watermark
  const img = new Image()
  img.onload = () => {
    const canvas = document.createElement('canvas')
    canvas.width = img.naturalWidth
    canvas.height = img.naturalHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(img, 0, 0)
    // Timestamp watermark
    const now = new Date()
    const ts = now.getFullYear() + '-'
      + String(now.getMonth() + 1).padStart(2, '0') + '-'
      + String(now.getDate()).padStart(2, '0') + ' '
      + String(now.getHours()).padStart(2, '0') + ':'
      + String(now.getMinutes()).padStart(2, '0') + ':'
      + String(now.getSeconds()).padStart(2, '0')
    const fontSize = Math.max(14, Math.round(canvas.width * 0.025))
    ctx.font = `${fontSize}px "Courier New", monospace`
    const metrics = ctx.measureText(ts)
    const textW = metrics.width
    const textH = fontSize * 1.2
    const padX = fontSize * 0.5
    const padY = fontSize * 0.3
    const x = canvas.width - textW - padX * 2 - 8
    const y = canvas.height - textH - padY - 8
    ctx.fillStyle = 'rgba(0, 0, 0, 0.55)'
    ctx.fillRect(x, y, textW + padX * 2, textH + padY)
    ctx.fillStyle = 'rgba(255, 255, 255, 0.92)'
    ctx.textBaseline = 'bottom'
    ctx.fillText(ts, x + padX, y + textH)
    canvas.toBlob((blob) => {
      if (!blob) {
        // Fallback: use original file if canvas fails
        const url = URL.createObjectURL(file)
        emit('photo-taken', { file, previewUrl: url, sampleNo: props.sampleNo })
        close()
        return
      }
      const stampedFile = new File([blob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' })
      const url = URL.createObjectURL(blob)
      emit('photo-taken', { file: stampedFile, previewUrl: url, sampleNo: props.sampleNo })
      close()
    }, 'image/jpeg', 0.92)
  }
  img.onerror = () => {
    const url = URL.createObjectURL(file)
    emit('photo-taken', { file, previewUrl: url, sampleNo: props.sampleNo })
    close()
  }
  img.src = URL.createObjectURL(file)
}

function close() {
  if (stream.value) { stream.value.getTracks().forEach(t => t.stop()); stream.value = null }
  videoReady.value = false
  error.value = ''
  emit('close')
}

onBeforeUnmount(() => {
  if (stream.value) stream.value.getTracks().forEach(t => t.stop())
})

start()
</script>

<template>
  <div class="camera-inline">
    <div v-if="error" class="cam-error">
      <div class="cam-error-msg">⚠️ {{ error }}</div>
      <div class="cam-error-actions">
        <el-button size="small" @click="start">重试</el-button>
        <label class="file-btn">
          📁 从文件选择
          <input type="file" accept="image/*" @change="handleFileInput" style="display:none" />
        </label>
        <el-button size="small" @click="close">取消</el-button>
      </div>
    </div>

    <div v-show="!error" class="cam-viewfinder" :class="{ ready: videoReady }">
      <video ref="videoRef" autoplay playsinline muted class="cam-video" />
      <div v-if="!videoReady" class="cam-loading">
        <span>正在启动摄像头…</span>
      </div>
      <canvas ref="canvasRef" style="display:none" />
      <div class="cam-controls">
        <el-button v-if="devices.length > 1" circle size="small" @click="switchCamera" :disabled="isCapturing">🔄</el-button>
        <el-button type="primary" circle class="snap-btn" :loading="isCapturing" @click="capture" :disabled="!videoReady || isCapturing">
          <span v-if="!isCapturing" class="snap-dot" />
        </el-button>
        <el-button circle size="small" @click="close" :disabled="isCapturing">✕</el-button>
      </div>
      <div class="cam-hint">
        <span>拍摄：<strong>{{ checkpoint.label }}</strong></span>
        <span v-if="sampleNo" class="sn-tag">样品 {{ sampleNo }}</span>
        <span v-if="cameraHint" class="tip">📷 {{ cameraHint }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.camera-inline { border: 2px solid #3B82F6; border-radius: 10px; overflow: hidden; background: #0F172A; margin-top: 8px; }
.cam-video { width: 100%; max-height: 320px; display: block; background: #000; object-fit: contain; }
.cam-loading { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: #94A3B8; font-size: 14px; background: rgba(15,23,42,0.95); }
.cam-viewfinder { position: relative; }
.cam-viewfinder.ready .cam-loading { display: none; }
.cam-controls { display: flex; justify-content: center; align-items: center; gap: 20px; padding: 10px; background: #1E293B; }
.snap-btn { width: 52px !important; height: 52px !important; }
.snap-dot { width: 36px; height: 36px; border-radius: 50%; background: white; display: block; border: 3px solid #CBD5E1; }
.cam-hint { padding: 6px 12px; font-size: 12px; color: #CBD5E1; background: #0F172A; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.sn-tag { color: #60A5FA; font-weight: 600; }
.tip { color: #FBBF24; font-weight: 500; }
.cam-error { padding: 14px; text-align: center; }
.cam-error-msg { color: #EF4444; font-size: 13px; margin-bottom: 10px; }
.cam-error-actions { display: flex; gap: 8px; justify-content: center; align-items: center; }
.file-btn { display: inline-flex; align-items: center; padding: 5px 12px; font-size: 12px; border-radius: 4px; border: 1px solid #D1D5DB; background: white; cursor: pointer; color: #374151; }
.file-btn:hover { background: #F3F4F6; }
</style>
