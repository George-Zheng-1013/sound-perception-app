<template>
  <div class="audio-recorder"
    :class="[`direction-${direction}`, result && result.risk_level ? `risk-${result.risk_level}` : '']">
    <!-- 主控制面板 -->
    <el-row :gutter="24" justify="center">
      <el-col :lg="16" :md="20" :sm="24">
        <el-card class="control-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon class="header-icon">
                <Microphone />
              </el-icon>
              <span class="header-title">音频录制控制</span>
              <el-tag v-if="isRecording" type="danger" effect="dark" class="status-tag">
                <el-icon class="pulse-icon">
                  <Microphone />
                </el-icon>
                REC
              </el-tag>
            </div>
          </template>

          <div class="control-content">
            <!-- 主要控制按钮 -->
            <div class="main-controls">
              <el-button type="primary" size="large" :icon="Microphone" @click="startRecording"
                :disabled="isRecording || isRealtimeListening" :loading="isStarting" class="record-btn" round>
                {{ isRecording ? '录音中...' : '开始录音' }}
              </el-button>

              <el-button type="danger" size="large" :icon="VideoPause" @click="stopRecording" :disabled="!isRecording"
                class="stop-btn" round>
                停止录音
              </el-button>

              <el-button type="success" size="large" :icon="isRealtimeListening ? VideoPause : Microphone"
                @click="toggleRealtimeListening" :loading="isStartingRealtime" class="realtime-btn" round>
                {{ isRealtimeListening ? '停止实时感知' : '开始实时感知' }}
              </el-button>
            </div>

            <!-- 录音状态显示 -->
            <div v-if="isRecording" class="recording-status">
              <div class="time-display">
                <el-statistic :value="recordingTime" :formatter="formatTime">
                  <template #title>
                    <span class="time-label">录音时长</span>
                  </template>
                </el-statistic>
              </div>
            </div>

            <!-- 操作按钮组 -->
            <div v-if="audioUrl" class="action-buttons">
              <el-button type="warning" :icon="Delete" @click="clearRecording" round>
                清除录音
              </el-button>
              <el-button type="success" :icon="Download" @click="downloadRecording" round>
                下载录音
              </el-button>
            </div>

            <!-- 测试按钮（开发时使用） -->
            <div class="test-buttons">
              <el-button type="danger" size="small" @click="testHighRisk" plain>
                测试高风险
              </el-button>
              <el-button type="warning" size="small" @click="testMediumRisk" plain>
                测试中风险
              </el-button>
              <el-button type="success" size="small" @click="testLowRisk" plain>
                测试低风险
              </el-button>
              <el-button type="info" size="small" @click="clearResult" plain>
                清除结果
              </el-button>
              <el-button type="primary" size="small" @click="testLeftDirection" plain>
                左侧方向
              </el-button>
              <el-button type="primary" size="small" @click="testRightDirection" plain>
                右侧方向
              </el-button>
              <el-button type="info" size="small" @click="clearDirection" plain>
                清除方向
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 音频预览和分析结果 -->

    <!-- 风险警告面板 -->
    <el-row :gutter="24" justify="center" v-if="(isRecording && direction) || result">
      <el-col :lg="20" :md="22" :sm="24">
        <el-card class="warning-panel" :class="[
          result?.risk_level ? `warning-${result.risk_level}` : 'warning-low',
          direction ? `warning-direction-${direction}` : ''
        ]" shadow="always">
          <template #header>
            <div class="warning-header">
              <el-icon class="warning-icon" :class="`warning-icon-${result?.risk_level || 'low'}`">
                <Warning />
              </el-icon>
              <span class="warning-title">声源方向检测与风险提示</span>
              <el-tag class="warning-status" :type="getRiskTagType(result?.risk_level || 'low')" effect="dark"
                size="large">
                {{ getRiskLevelText(result?.risk_level || 'low') }}
              </el-tag>
            </div>
          </template>

          <div class="warning-content">
            <div class="direction-indicator">
              <div class="direction-arrow" :class="direction ? `arrow-${direction}` : 'arrow-detecting'">
                <el-icon size="40">
                  <ArrowLeft v-if="direction === 'left'" />
                  <ArrowRight v-if="direction === 'right'" />
                  <Loading v-if="!direction && isRecording" />
                </el-icon>
              </div>
              <div class="direction-text">
                <h3>声源方向：{{ getDirectionText(direction) }}</h3>
                <p class="risk-description">{{ getRiskDescription(result?.risk_level || 'low') }}</p>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="24" v-if="audioUrl" justify="center">
      <el-col :lg="12" :md="16" :sm="24">
        <el-card class="preview-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon class="header-icon">
                <VideoPlay />
              </el-icon>
              <span class="header-title">录音预览</span>
            </div>
          </template>

          <div class="audio-preview">
            <div class="audio-player-container">
              <audio ref="audioElement" :src="audioUrl" controls class="audio-player" @loadedmetadata="onAudioLoaded"
                @play="onAudioPlay" @pause="onAudioPause"></audio>
            </div>

            <el-descriptions :column="1" size="default" border class="audio-info">
              <el-descriptions-item label="录音时长">
                <el-tag type="info">{{ audioDuration ? formatTime(audioDuration) : '--:--' }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="文件格式">
                <el-tag type="success">WebM/Opus</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="采样率">
                <el-tag>44.1 kHz</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="文件大小">
                <el-tag>{{ formatFileSize(audioFileSize) }}</el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-col>

      <el-col :lg="12" :md="16" :sm="24">
        <!-- 处理状态或识别结果 -->
        <el-card v-if="isProcessing" class="processing-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon class="header-icon loading-icon">
                <Loading />
              </el-icon>
              <span class="header-title">AI 分析中</span>
            </div>
          </template>

          <div class="processing-content">
            <el-progress type="circle" :percentage="processingProgress" :width="120" :stroke-width="8" color="#409EFF">
              <template #default="{ percentage }">
                <span class="progress-text">{{ percentage }}%</span>
              </template>
            </el-progress>
            <p class="processing-message">正在使用AI模型分析您的录音内容...</p>
          </div>
        </el-card>

        <el-card v-else-if="result" class="result-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon class="header-icon">
                <SuccessFilled />
              </el-icon>
              <span class="header-title">识别结果</span>
            </div>
          </template>

          <div class="result-content">
            <el-row :gutter="16">
              <el-col :span="24">
                <div class="result-main">
                  <div class="category-display">
                    <h3 class="category-title">{{ result.category }}</h3>
                    <div class="tags-container">
                      <el-tag :type="result.is_known ? 'success' : 'warning'" size="large" class="category-tag">
                        {{ result.is_known ? '已知类别' : '未知类别' }}
                      </el-tag>
                      <el-tag v-if="result.risk_level" :type="getRiskTagType(result.risk_level)" size="large"
                        class="risk-tag">
                        {{ getRiskLevelText(result.risk_level) }}
                      </el-tag>
                    </div>
                  </div>

                  <div class="confidence-display">
                    <el-progress type="circle" :percentage="result.confidence * 100"
                      :color="getConfidenceColor(result.confidence)" :width="100" :stroke-width="10">
                      <template #default="{ percentage }">
                        <span class="confidence-text">{{ percentage.toFixed(1) }}%</span>
                      </template>
                    </el-progress>
                    <p class="confidence-label">置信度</p>
                  </div>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 错误提示 -->
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="true" @close="error = null"
      class="error-alert" />
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Microphone,
  VideoPause,
  Delete,
  Download,
  VideoPlay,
  SuccessFilled,
  Loading,
  Warning,
  ArrowLeft,
  ArrowRight
} from '@element-plus/icons-vue'

// 类型定义
interface AudioResult {
  category: string
  confidence: number
  is_known: boolean
  class_id?: number
  risk_level?: string
}

// 响应式数据
const mediaRecorder = ref<MediaRecorder | null>(null)
const audioChunks = ref<Blob[]>([])
const isRecording = ref(false)
const isStarting = ref(false)
const isProcessing = ref(false)
const result = ref<AudioResult | null>(null)
const error = ref<string | null>(null)
const audioUrl = ref<string | null>(null)
const audioDuration = ref(0)
const audioFileSize = ref(0)
const recordingTime = ref(0)
const recordingTimer = ref<number | null>(null)
const processingProgress = ref(0)

// 实时感知相关状态
const isRealtimeListening = ref(false)
const isStartingRealtime = ref(false)
const realtimeStream = ref<MediaStream | null>(null)
const soundDetectionTimer = ref<number | null>(null)
const isEnvironmentNoisy = ref(false)
const silenceTimer = ref<number | null>(null)
const noiseTimer = ref<number | null>(null)

// 音频流和元素引用
const stream = ref<MediaStream | null>(null)
const audioElement = ref<HTMLAudioElement | null>(null)

// 计算属性
const isAudioPlaying = ref(false)

// 声源方位，不设置默认值
const direction = ref<'left' | 'right' | null>(null)
let audioCtx: AudioContext | null = null
let leftAnalyser: AnalyserNode | null = null
let rightAnalyser: AnalyserNode | null = null

// 持续分析方向（高灵敏度，只检测左右）
const analyzeDirection = () => {
  if (!leftAnalyser || !rightAnalyser) return
  const size = leftAnalyser.fftSize
  const ldata = new Float32Array(size)
  const rdata = new Float32Array(size)
  leftAnalyser.getFloatTimeDomainData(ldata)
  rightAnalyser.getFloatTimeDomainData(rdata)
  const energy = (arr: Float32Array) => arr.reduce((s, v) => s + v * v, 0)
  const el = energy(ldata), er = energy(rdata)

  // 需要更明显的差异才认为检测到方向（1.2倍差异）
  if (el > er * 1.2) {
    direction.value = 'left'
  } else if (er > el * 1.2) {
    direction.value = 'right'
  }
  // 如果差异不够大，保持当前状态（可能是null）

  requestAnimationFrame(analyzeDirection)
}

// 风险等级分类映射
const riskCategories = {
  low: [0, 1, 5, 6, 7, 8, 9, 10, 11, 18, 19, 20, 21, 23, 29, 41, 42],
  medium: [3, 12, 13, 14, 15, 16, 17, 22, 28, 30, 34, 35, 36, 43, 44, 45, 46, 47],
  high: [2, 4, 24, 25, 31, 32, 33, 37, 38, 39, 40]
}

// 根据类别ID获取风险等级
const getRiskLevelByClassId = (classId: number): string => {
  for (const [riskLevel, classIds] of Object.entries(riskCategories)) {
    if (classIds.includes(classId)) {
      return riskLevel
    }
  }
  return 'medium' // 默认为中等风险
}

// 开始录音
const startRecording = async () => {
  error.value = null
  result.value = null
  audioUrl.value = null
  direction.value = null // 重置方向检测
  isStarting.value = true

  try {
    stream.value = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 44100, channelCount: 2 }
    })

    // 初始化 Web Audio API 分析器
    audioCtx = new AudioContext()
    const srcNode = audioCtx.createMediaStreamSource(stream.value)
    const splitter = audioCtx.createChannelSplitter(2)
    srcNode.connect(splitter)
    leftAnalyser = audioCtx.createAnalyser()
    rightAnalyser = audioCtx.createAnalyser()
    leftAnalyser.fftSize = 2048
    rightAnalyser.fftSize = 2048
    splitter.connect(leftAnalyser, 0)
    splitter.connect(rightAnalyser, 1)
    analyzeDirection()

    // 使用明确的MIME类型
    const mimeType = 'audio/webm;codecs=opus'
    const options = { mimeType }

    mediaRecorder.value = new MediaRecorder(stream.value, options)
    audioChunks.value = []

    mediaRecorder.value.ondataavailable = (e: BlobEvent) => {
      audioChunks.value.push(e.data)
    }

    mediaRecorder.value.onstop = async () => {
      await handleRecordingStop()
    }

    mediaRecorder.value.start()
    isRecording.value = true
    isStarting.value = false
    recordingTime.value = 0

    // 开始录音计时
    startRecordingTimer()

    ElMessage.success('录音开始')
  } catch (err: unknown) {
    const errorMessage = err instanceof Error ? err.message : '未知错误'
    error.value = `无法访问麦克风: ${errorMessage}`
    isStarting.value = false
    ElMessage.error('录音启动失败')
  }
}

// 停止录音
const stopRecording = () => {
  if (!isRecording.value || !mediaRecorder.value) return

  mediaRecorder.value.stop()
  isRecording.value = false
  stopRecordingTimer()

  // 停止音频流
  if (stream.value) {
    stream.value.getTracks().forEach((track: MediaStreamTrack) => track.stop())
  }

  ElMessage.success('录音停止')
}

// 清除录音
const clearRecording = () => {
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value)
  }
  audioUrl.value = null
  result.value = null
  error.value = null
  audioDuration.value = 0
  audioFileSize.value = 0
  ElMessage.info('录音已清除')
}

// 下载录音
const downloadRecording = () => {
  if (!audioUrl.value) return

  const link = document.createElement('a')
  link.href = audioUrl.value
  link.download = `recording_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.webm`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  ElMessage.success('录音下载完成')
}

// 处理录音停止
const handleRecordingStop = async () => {
  // 创建音频预览
  const audioBlob = new Blob(audioChunks.value, { type: 'audio/webm' })
  audioUrl.value = URL.createObjectURL(audioBlob)
  audioFileSize.value = audioBlob.size

  try {
    isProcessing.value = true
    processingProgress.value = 0
    simulateProgress()
    await sendAudioForAnalysis(audioBlob)
    isProcessing.value = false
    processingProgress.value = 100
  } catch (err: unknown) {
    const errorMessage = err instanceof Error ? err.message : '未知错误'
    error.value = `处理失败: ${errorMessage}`
    isProcessing.value = false
    ElMessage.error('音频分析失败')
  }
}

// 开始录音计时
const startRecordingTimer = () => {
  recordingTimer.value = setInterval(() => {
    recordingTime.value++
  }, 1000)
}

// 停止录音计时
const stopRecordingTimer = () => {
  if (recordingTimer.value) {
    clearInterval(recordingTimer.value)
    recordingTimer.value = null
  }
}

// 模拟处理进度
const simulateProgress = () => {
  const interval = setInterval(() => {
    if (processingProgress.value < 90) {
      processingProgress.value += Math.random() * 10
    } else {
      clearInterval(interval)
    }
  }, 200)
}

// 发送音频进行分析
const sendAudioForAnalysis = async (audioBlob: Blob) => {
  const formData = new FormData()
  const file = new File([audioBlob], "recording.webm", { type: 'audio/webm' })
  formData.append('audio', file)

  try {
    const response = await fetch('http://localhost:5000/api/analyze', {
      method: 'POST',
      body: formData
    })

    if (response.ok) {
      const data = await response.json()
      if (data.status === 'success') {
        // 如果有class_id，计算风险等级
        if (data.class_id !== undefined && data.class_id >= 0) {
          data.risk_level = getRiskLevelByClassId(data.class_id)
        }
        result.value = data
        ElMessage.success('音频分析完成')
        return
      }
    }

    // 如果后端响应失败，使用模拟数据
    throw new Error('后端服务响应失败')

  } catch (err: unknown) {
    console.warn('后端服务不可用，使用模拟数据:', err)

    // 模拟不同风险等级的数据
    const mockResults: (AudioResult & { status: string })[] = [
      {
        category: "火灾发生时的警报声",
        confidence: 0.95,
        is_known: true,
        class_id: 2,
        status: "success"
      },
      {
        category: "室内烟雾、煤气警报",
        confidence: 0.92,
        is_known: true,
        class_id: 4,
        status: "success"
      },
      {
        category: "有人敲用户房间门、按门铃的声音",
        confidence: 0.76,
        is_known: true,
        class_id: 3,
        status: "success"
      },
      {
        category: "窗外下大雨的声音",
        confidence: 0.79,
        is_known: true,
        class_id: 12,
        status: "success"
      },
      {
        category: "手机收到短信的提示音",
        confidence: 0.88,
        is_known: true,
        class_id: 0,
        status: "success"
      },
      {
        category: "别人敲键盘、鼠标的声音",
        confidence: 0.85,
        is_known: true,
        class_id: 1,
        status: "success"
      }
    ]

    // 随机选择一个模拟结果并计算风险等级
    const mockResult = mockResults[Math.floor(Math.random() * mockResults.length)]
    if (mockResult.class_id !== undefined) {
      mockResult.risk_level = getRiskLevelByClassId(mockResult.class_id)
    }
    result.value = mockResult
    ElMessage.success('音频分析完成（模拟数据）')
  }
}

// 音频加载完成
const onAudioLoaded = () => {
  if (audioElement.value) {
    audioDuration.value = audioElement.value.duration
  }
}

// 音频播放
const onAudioPlay = () => {
  isAudioPlaying.value = true
}

// 音频暂停
const onAudioPause = () => {
  isAudioPlaying.value = false
}

// 格式化时间
const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// 格式化文件大小
const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 获取置信度颜色
const getConfidenceColor = (confidence: number) => {
  if (confidence >= 0.8) return '#67C23A'
  if (confidence >= 0.6) return '#E6A23C'
  return '#F56C6C'
}

// 获取风险等级标签类型
const getRiskTagType = (riskLevel: string) => {
  switch (riskLevel) {
    case 'high':
      return 'danger'
    case 'medium':
      return 'warning'
    case 'low':
      return 'success'
    default:
      return 'info'
  }
}

// 获取风险等级文本
const getRiskLevelText = (riskLevel: string) => {
  switch (riskLevel) {
    case 'high':
      return '高风险'
    case 'medium':
      return '中风险'
    case 'low':
      return '低风险'
    default:
      return '未知风险'
  }
}

// 获取方向文本
const getDirectionText = (direction: 'left' | 'right' | null) => {
  if (direction === 'left') return '左侧'
  if (direction === 'right') return '右侧'
  if (isRecording.value) return '检测中...'
  return '未检测'
}

// 获取风险描述
const getRiskDescription = (riskLevel: string) => {
  switch (riskLevel) {
    case 'high':
      return '检测到高风险声源，请立即检查！'
    case 'medium':
      return '检测到中等风险声源，请注意！'
    case 'low':
      return '检测到低风险声源，情况正常。'
    default:
      return '正在监听音频...'
  }
}

// 测试方法（开发时使用）
const testHighRisk = () => {
  result.value = {
    category: "火灾发生时的警报声",
    confidence: 0.95,
    is_known: true,
    class_id: 2, // 高风险类别ID
    risk_level: getRiskLevelByClassId(2)
  }
  ElMessage.success('高风险测试数据已加载')
}

const testMediumRisk = () => {
  result.value = {
    category: "有人敲用户房间门、按门铃的声音",
    confidence: 0.76,
    is_known: true,
    class_id: 3, // 中风险类别ID
    risk_level: getRiskLevelByClassId(3)
  }
  ElMessage.success('中风险测试数据已加载')
}

const testLowRisk = () => {
  result.value = {
    category: "手机收到短信的提示音",
    confidence: 0.88,
    is_known: true,
    class_id: 0, // 低风险类别ID
    risk_level: getRiskLevelByClassId(0)
  }
  ElMessage.success('低风险测试数据已加载')
}

const clearResult = () => {
  result.value = null
  ElMessage.info('结果已清除')
}

// 测试方向变化（开发时使用）
const testLeftDirection = () => {
  direction.value = 'left'
  ElMessage.success('方向设置为左侧')
}

const testRightDirection = () => {
  direction.value = 'right'
  ElMessage.success('方向设置为右侧')
}

// 清除方向检测结果
const clearDirection = () => {
  direction.value = null
  ElMessage.info('方向检测已清除')
}

// 实时感知相关函数
let realtimeAnalyser: AnalyserNode | null = null
let realtimeLeftAnalyser: AnalyserNode | null = null
let realtimeRightAnalyser: AnalyserNode | null = null
let realtimeAudioCtx: AudioContext | null = null

// 音量检测参数
const NOISE_THRESHOLD = 0.01 // 声音检测阈值
const SILENCE_DURATION = 2000 // 安静持续时间(ms)
const NOISE_DURATION = 500 // 有声持续时间(ms)

// 开始/停止实时感知
const toggleRealtimeListening = async () => {
  if (isRealtimeListening.value) {
    stopRealtimeListening()
  } else {
    await startRealtimeListening()
  }
}

// 开始实时感知
const startRealtimeListening = async () => {
  if (isRecording.value) {
    ElMessage.warning('请先停止录音再启动实时感知')
    return
  }

  isStartingRealtime.value = true
  error.value = null

  try {
    realtimeStream.value = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 44100, channelCount: 2 }
    })

    // 初始化音频分析器
    realtimeAudioCtx = new AudioContext()
    const srcNode = realtimeAudioCtx.createMediaStreamSource(realtimeStream.value)
    const splitter = realtimeAudioCtx.createChannelSplitter(2)
    srcNode.connect(splitter)

    // 创建音量检测分析器
    realtimeAnalyser = realtimeAudioCtx.createAnalyser()
    realtimeAnalyser.fftSize = 2048
    srcNode.connect(realtimeAnalyser)

    // 创建方向检测分析器
    realtimeLeftAnalyser = realtimeAudioCtx.createAnalyser()
    realtimeRightAnalyser = realtimeAudioCtx.createAnalyser()
    realtimeLeftAnalyser.fftSize = 2048
    realtimeRightAnalyser.fftSize = 2048
    splitter.connect(realtimeLeftAnalyser, 0)
    splitter.connect(realtimeRightAnalyser, 1)

    isRealtimeListening.value = true
    isStartingRealtime.value = false

    // 开始检测
    startSoundDetection()
    startRealtimeDirectionAnalysis()

    ElMessage.success('实时感知已启动')
  } catch (err: unknown) {
    const errorMessage = err instanceof Error ? err.message : '未知错误'
    error.value = `无法启动实时感知: ${errorMessage}`
    isStartingRealtime.value = false
    ElMessage.error('实时感知启动失败')
  }
}

// 停止实时感知
const stopRealtimeListening = () => {
  isRealtimeListening.value = false
  isStartingRealtime.value = false

  // 停止所有定时器
  if (soundDetectionTimer.value) {
    clearInterval(soundDetectionTimer.value)
    soundDetectionTimer.value = null
  }
  if (silenceTimer.value) {
    clearTimeout(silenceTimer.value)
    silenceTimer.value = null
  }
  if (noiseTimer.value) {
    clearTimeout(noiseTimer.value)
    noiseTimer.value = null
  }

  // 停止音频流
  if (realtimeStream.value) {
    realtimeStream.value.getTracks().forEach((track: MediaStreamTrack) => track.stop())
    realtimeStream.value = null
  }

  // 关闭音频上下文
  if (realtimeAudioCtx) {
    realtimeAudioCtx.close()
    realtimeAudioCtx = null
    realtimeAnalyser = null
    realtimeLeftAnalyser = null
    realtimeRightAnalyser = null
  }

  // 如果正在录音，停止录音
  if (isRecording.value) {
    stopRecording()
  }

  isEnvironmentNoisy.value = false
  direction.value = null

  ElMessage.info('实时感知已停止')
}

// 声音检测
const startSoundDetection = () => {
  soundDetectionTimer.value = setInterval(() => {
    if (!realtimeAnalyser) return

    const bufferLength = realtimeAnalyser.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)
    realtimeAnalyser.getByteFrequencyData(dataArray)

    // 计算音量
    const volume = dataArray.reduce((sum, value) => sum + value, 0) / bufferLength / 255

    if (volume > NOISE_THRESHOLD) {
      // 检测到声音
      handleNoiseDetected()
    } else {
      // 环境安静
      handleSilenceDetected()
    }
  }, 100) // 每100ms检测一次
}

// 处理检测到声音
const handleNoiseDetected = () => {
  // 清除安静定时器
  if (silenceTimer.value) {
    clearTimeout(silenceTimer.value)
    silenceTimer.value = null
  }

  // 如果还没有开始录音且环境还不是噪音状态
  if (!isEnvironmentNoisy.value && !isRecording.value) {
    // 设置噪音定时器，确保声音持续一段时间后才开始录音
    if (!noiseTimer.value) {
      noiseTimer.value = setTimeout(() => {
        if (!isRecording.value && isRealtimeListening.value) {
          isEnvironmentNoisy.value = true
          startAutoRecording()
        }
      }, NOISE_DURATION)
    }
  }
}

// 处理检测到安静
const handleSilenceDetected = () => {
  // 清除噪音定时器
  if (noiseTimer.value) {
    clearTimeout(noiseTimer.value)
    noiseTimer.value = null
  }

  // 如果正在录音，设置安静定时器
  if (isRecording.value && !silenceTimer.value) {
    silenceTimer.value = setTimeout(() => {
      if (isRecording.value && isRealtimeListening.value) {
        isEnvironmentNoisy.value = false
        stopRecording()
        ElMessage.info('环境安静，自动停止录音')
      }
    }, SILENCE_DURATION)
  }
}

// 自动开始录音
const startAutoRecording = async () => {
  if (isRecording.value || !isRealtimeListening.value) return

  try {
    // 重用实时感知的音频流进行录音
    const mimeType = 'audio/webm;codecs=opus'
    const options = { mimeType }

    mediaRecorder.value = new MediaRecorder(realtimeStream.value!, options)
    audioChunks.value = []

    mediaRecorder.value.ondataavailable = (e: BlobEvent) => {
      audioChunks.value.push(e.data)
    }

    mediaRecorder.value.onstop = async () => {
      await handleRecordingStop()
    }

    mediaRecorder.value.start()
    isRecording.value = true
    recordingTime.value = 0

    // 开始录音计时
    startRecordingTimer()

    ElMessage.success('检测到声音，自动开始录音')
  } catch (err: unknown) {
    const errorMessage = err instanceof Error ? err.message : '未知错误'
    error.value = `自动录音失败: ${errorMessage}`
    ElMessage.error('自动录音失败')
  }
}

// 实时方向分析
const startRealtimeDirectionAnalysis = () => {
  const analyzeRealtimeDirection = () => {
    if (!realtimeLeftAnalyser || !realtimeRightAnalyser || !isRealtimeListening.value) return

    const size = realtimeLeftAnalyser.fftSize
    const ldata = new Float32Array(size)
    const rdata = new Float32Array(size)
    realtimeLeftAnalyser.getFloatTimeDomainData(ldata)
    realtimeRightAnalyser.getFloatTimeDomainData(rdata)
    const energy = (arr: Float32Array) => arr.reduce((s, v) => s + v * v, 0)
    const el = energy(ldata), er = energy(rdata)

    // 需要更明显的差异才认为检测到方向（1.2倍差异）
    if (el > er * 1.2) {
      direction.value = 'left'
    } else if (er > el * 1.2) {
      direction.value = 'right'
    }

    requestAnimationFrame(analyzeRealtimeDirection)
  }

  analyzeRealtimeDirection()
}

// 组件卸载时清理所有资源
onBeforeUnmount(() => {
  // 停止实时感知
  if (isRealtimeListening.value) {
    stopRealtimeListening()
  }

  // 停止录音
  if (isRecording.value) {
    stopRecording()
  }

  // 清理所有定时器
  if (recordingTimer.value) {
    clearInterval(recordingTimer.value)
    recordingTimer.value = null
  }
  if (soundDetectionTimer.value) {
    clearInterval(soundDetectionTimer.value)
    soundDetectionTimer.value = null
  }
  if (silenceTimer.value) {
    clearTimeout(silenceTimer.value)
    silenceTimer.value = null
  }
  if (noiseTimer.value) {
    clearTimeout(noiseTimer.value)
    noiseTimer.value = null
  }

  // 清理音频流
  if (stream.value) {
    stream.value.getTracks().forEach((track: MediaStreamTrack) => track.stop())
    stream.value = null
  }
  if (realtimeStream.value) {
    realtimeStream.value.getTracks().forEach((track: MediaStreamTrack) => track.stop())
    realtimeStream.value = null
  }

  // 清理音频上下文
  if (audioCtx) {
    audioCtx.close()
    audioCtx = null
    leftAnalyser = null
    rightAnalyser = null
  }
  if (realtimeAudioCtx) {
    realtimeAudioCtx.close()
    realtimeAudioCtx = null
    realtimeAnalyser = null
    realtimeLeftAnalyser = null
    realtimeRightAnalyser = null
  }

  // 清理音频URL
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value)
    audioUrl.value = null
  }

  console.log('音频录制组件资源已清理')
})
</script>

<style scoped>
.audio-recorder {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  min-height: 100vh;
  background: #f8f9fa;
  position: relative;
}

.audio-recorder::before {
  display: none;
}

.audio-recorder::after {
  content: '';
  position: fixed;
  z-index: 1000;
  background: transparent;
  animation: none;
  top: 0;
  bottom: 0;
}

/* 背景闪烁动画 */
@keyframes bg-blink {

  0%,
  100% {
    opacity: 0.2;
  }

  50% {
    opacity: 0.8;
  }
}

/* 更明显的高风险快速闪烁动画 */
@keyframes high-risk-blink {

  0%,
  25%,
  50%,
  75%,
  100% {
    opacity: 0.3;
  }

  12.5%,
  37.5%,
  62.5%,
  87.5% {
    opacity: 1;
  }
}

/* 中等风险稍快闪烁动画 */
@keyframes medium-risk-blink {

  0%,
  50%,
  100% {
    opacity: 0.3;
  }

  25%,
  75% {
    opacity: 0.9;
  }
}

/* 边缘加粗闪烁动画 */
@keyframes edge-pulse {

  0%,
  100% {
    width: 12px;
    opacity: 0.6;
    box-shadow: inset 0 0 0 2px currentColor;
  }

  50% {
    width: 24px;
    opacity: 1;
    box-shadow: inset 0 0 0 2px currentColor, 0 0 20px currentColor;
  }
}

/* 超大屏幕边缘加粗闪烁动画 */
@keyframes edge-pulse-large {

  0%,
  100% {
    width: 20px;
    opacity: 0.6;
    box-shadow: inset 0 0 0 3px currentColor;
  }

  50% {
    width: 40px;
    opacity: 1;
    box-shadow: inset 0 0 0 3px currentColor, 0 0 30px currentColor;
  }
}

/* 左侧输入背景：线性渐变突出左侧 */
.audio-recorder.direction-left.risk-high::before {
  animation: bg-blink 2s infinite;
  background-image: linear-gradient(90deg, rgba(245, 108, 108, 0.6) 0%, rgba(245, 108, 108, 0.3) 50%, transparent 100%);
}

.audio-recorder.direction-left.risk-medium::before {
  animation: bg-blink 2s infinite;
  background-image: linear-gradient(90deg, rgba(230, 162, 60, 0.6) 0%, rgba(230, 162, 60, 0.3) 50%, transparent 100%);
}

.audio-recorder.direction-left.risk-low::before {
  animation: bg-blink 2s infinite;
  background-image: linear-gradient(90deg, rgba(103, 195, 58, 0.6) 0%, rgba(103, 195, 58, 0.3) 50%, transparent 100%);
}

/* 右侧输入背景：线性渐变突出右侧 */
.audio-recorder.direction-right.risk-high::before {
  animation: bg-blink 2s infinite;
  background-image: linear-gradient(270deg, rgba(245, 108, 108, 0.6) 0%, rgba(245, 108, 108, 0.3) 50%, transparent 100%);
}

.audio-recorder.direction-right.risk-medium::before {
  animation: bg-blink 2s infinite;
  background-image: linear-gradient(270deg, rgba(230, 162, 60, 0.6) 0%, rgba(230, 162, 60, 0.3) 50%, transparent 100%);
}

.audio-recorder.direction-right.risk-low::before {
  animation: bg-blink 2s infinite;
  background-image: linear-gradient(270deg, rgba(103, 195, 58, 0.6) 0%, rgba(103, 195, 58, 0.3) 50%, transparent 100%);
}



/* 左侧边缘闪烁 - 增强视觉效果，固定在网页边缘 */
.audio-recorder.direction-left.risk-high::after {
  left: 0;
  width: 20px;
  background-color: #ff4444;
  animation: high-risk-blink 0.8s infinite, edge-pulse 2s infinite;
  box-shadow: 0 0 30px rgba(255, 68, 68, 0.8), inset 0 0 0 3px rgba(255, 255, 255, 0.3);
  border-radius: 0 8px 8px 0;
}

.audio-recorder.direction-left.risk-medium::after {
  left: 0;
  width: 16px;
  background-color: #ff9500;
  animation: medium-risk-blink 1.2s infinite, edge-pulse 2.5s infinite;
  box-shadow: 0 0 20px rgba(255, 149, 0, 0.6), inset 0 0 0 2px rgba(255, 255, 255, 0.2);
  border-radius: 0 6px 6px 0;
}

.audio-recorder.direction-left.risk-low::after {
  left: 0;
  width: 12px;
  background-color: #52c41a;
  animation: bg-blink 2s infinite;
  box-shadow: 0 0 15px rgba(82, 196, 26, 0.4), inset 0 0 0 1px rgba(255, 255, 255, 0.1);
  border-radius: 0 4px 4px 0;
}

/* 右侧边缘闪烁 - 增强视觉效果，固定在网页边缘 */
.audio-recorder.direction-right.risk-high::after {
  right: 0;
  width: 20px;
  background-color: #ff4444;
  animation: high-risk-blink 0.8s infinite, edge-pulse 2s infinite;
  box-shadow: 0 0 30px rgba(255, 68, 68, 0.8), inset 0 0 0 3px rgba(255, 255, 255, 0.3);
  border-radius: 8px 0 0 8px;
}

.audio-recorder.direction-right.risk-medium::after {
  right: 0;
  width: 16px;
  background-color: #ff9500;
  animation: medium-risk-blink 1.2s infinite, edge-pulse 2.5s infinite;
  box-shadow: 0 0 20px rgba(255, 149, 0, 0.6), inset 0 0 0 2px rgba(255, 255, 255, 0.2);
  border-radius: 6px 0 0 6px;
}

.audio-recorder.direction-right.risk-low::after {
  right: 0;
  width: 12px;
  background-color: #52c41a;
  animation: bg-blink 2s infinite;
  box-shadow: 0 0 15px rgba(82, 196, 26, 0.4), inset 0 0 0 1px rgba(255, 255, 255, 0.1);
  border-radius: 4px 0 0 4px;
}



/* 卡片样式 - 简约设计 */
.el-card {
  border-radius: 12px;
  border: 1px solid #e9ecef;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
  margin-bottom: 20px;
}

.el-card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

/* 卡片头部 - 简化 */
.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 600;
  color: #2c3e50;
  padding: 4px 0;
}

.header-icon {
  font-size: 18px;
  color: #409EFF;
}

.header-title {
  font-size: 16px;
  flex: 1;
}

.status-tag {
  margin-left: auto;
  animation: pulse 2s infinite;
}

.pulse-icon {
  animation: pulse 1.5s infinite;
}

@keyframes pulse {

  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }

  50% {
    opacity: 0.7;
    transform: scale(1.05);
  }
}

/* 控制卡片 - 简化背景 */
.control-card {
  background: white;
}

.control-card :deep(.el-card__header) {
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.control-card :deep(.el-card__body) {
  background: white;
}

.control-content {
  padding: 20px 0;
}

.main-controls {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.record-btn,
.stop-btn {
  min-width: 140px;
  height: 44px;
  font-size: 16px;
  font-weight: 500;
  transition: all 0.3s ease;
}

/* 录音状态 - 简化 */
.recording-status {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  background: #f1f3f4;
  border-radius: 8px;
  margin-bottom: 20px;
}

.time-display {
  text-align: center;
}

.time-label {
  color: #6c757d;
  font-size: 14px;
  font-weight: 500;
}



/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}

/* 测试按钮样式 */
.test-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e9ecef;
}

.test-buttons .el-button {
  font-size: 12px;
  padding: 4px 8px;
}



/* 预览卡片 - 简化 */
.preview-card {
  background: white;
}

.preview-card :deep(.el-card__header) {
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.preview-card :deep(.el-card__body) {
  background: white;
}

.audio-preview {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.audio-player-container {
  display: flex;
  justify-content: center;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.audio-player {
  width: 100%;
  max-width: 400px;
  border-radius: 8px;
}

.audio-info {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
}

/* 处理卡片 - 简化 */
.processing-card {
  background: white;
}

.processing-card :deep(.el-card__header) {
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.processing-card :deep(.el-card__body) {
  background: white;
}

.processing-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding: 20px 0;
}

.progress-text {
  font-size: 20px;
  font-weight: 600;
  color: #409EFF;
}

.processing-message {
  color: #6c757d;
  text-align: center;
  margin: 0;
  font-size: 14px;
}

.loading-icon {
  animation: spin 2s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

/* 结果卡片 - 简化 */
.result-card {
  background: white;
}

.result-card :deep(.el-card__header) {
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.result-card :deep(.el-card__body) {
  background: white;
}

.result-content {
  padding: 20px 0;
}

.result-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.category-display {
  text-align: center;
}

.category-title {
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 12px 0;
}

.tags-container {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.category-tag,
.risk-tag {
  font-size: 14px;
  padding: 6px 12px;
}

.risk-tag {
  font-weight: 600;
}

.confidence-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.confidence-text {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}

.confidence-label {
  color: #6c757d;
  font-size: 14px;
  font-weight: 500;
  margin: 0;
}

/* 错误提示 */
.error-alert {
  margin: 20px 0;
  border-radius: 8px;
}

/* 响应式设计 */
/* 超大屏幕 (2560px及以上) */
@media (min-width: 2560px) {
  .audio-recorder {
    max-width: 1800px;
    padding: 40px;
  }

  .control-content {
    padding: 40px 0;
  }

  .main-controls {
    gap: 32px;
    margin-bottom: 40px;
  }

  .record-btn,
  .stop-btn {
    min-width: 200px;
    height: 60px;
    font-size: 20px;
  }

  .card-header {
    gap: 20px;
    padding: 8px 0;
  }

  .header-icon {
    font-size: 24px;
  }

  .header-title {
    font-size: 20px;
  }

  .warning-panel {
    margin-bottom: 40px;
  }

  .warning-header {
    gap: 24px;
    padding: 12px 0;
  }

  .warning-icon {
    font-size: 32px;
  }

  .warning-title {
    font-size: 24px;
  }

  .warning-status {
    font-size: 16px;
    padding: 12px 20px;
  }

  .direction-indicator {
    gap: 40px;
    padding: 24px;
  }

  .direction-arrow {
    width: 120px;
    height: 120px;
  }

  .direction-text h3 {
    font-size: 32px;
  }

  .risk-description {
    font-size: 20px;
  }

  .category-title {
    font-size: 32px;
  }

  .result-main {
    gap: 40px;
  }

  .confidence-text {
    font-size: 20px;
  }

  .processing-content {
    gap: 32px;
    padding: 32px 0;
  }

  .progress-text {
    font-size: 24px;
  }

  .processing-message {
    font-size: 18px;
  }

  .recording-status {
    padding: 32px;
    margin-bottom: 32px;
  }

  .time-label {
    font-size: 18px;
  }

  :deep(.el-statistic__content) {
    font-size: 36px;
  }

  .test-buttons {
    margin-top: 24px;
    padding-top: 24px;
    gap: 12px;
  }

  .test-buttons .el-button {
    font-size: 14px;
    padding: 6px 12px;
  }

  .action-buttons {
    gap: 20px;
  }

  .audio-player-container {
    padding: 32px;
  }

  .audio-info {
    padding: 24px;
  }

  /* 超大屏幕边缘闪烁增强效果 */
  .audio-recorder.direction-left.risk-high::after {
    width: 30px;
    animation: high-risk-blink 0.8s infinite, edge-pulse-large 2s infinite;
    box-shadow: 0 0 40px rgba(255, 68, 68, 0.9), inset 0 0 0 4px rgba(255, 255, 255, 0.4);
    border-radius: 0 12px 12px 0;
  }

  .audio-recorder.direction-left.risk-medium::after {
    width: 25px;
    animation: medium-risk-blink 1.2s infinite, edge-pulse-large 2.5s infinite;
    box-shadow: 0 0 30px rgba(255, 149, 0, 0.7), inset 0 0 0 3px rgba(255, 255, 255, 0.3);
    border-radius: 0 10px 10px 0;
  }

  .audio-recorder.direction-left.risk-low::after {
    width: 20px;
    box-shadow: 0 0 25px rgba(82, 196, 26, 0.5), inset 0 0 0 2px rgba(255, 255, 255, 0.2);
    border-radius: 0 8px 8px 0;
  }

  .audio-recorder.direction-right.risk-high::after {
    width: 30px;
    animation: high-risk-blink 0.8s infinite, edge-pulse-large 2s infinite;
    box-shadow: 0 0 40px rgba(255, 68, 68, 0.9), inset 0 0 0 4px rgba(255, 255, 255, 0.4);
    border-radius: 12px 0 0 12px;
  }

  .audio-recorder.direction-right.risk-medium::after {
    width: 25px;
    animation: medium-risk-blink 1.2s infinite, edge-pulse-large 2.5s infinite;
    box-shadow: 0 0 30px rgba(255, 149, 0, 0.7), inset 0 0 0 3px rgba(255, 255, 255, 0.3);
    border-radius: 10px 0 0 10px;
  }

  .audio-recorder.direction-right.risk-low::after {
    width: 20px;
    box-shadow: 0 0 25px rgba(82, 196, 26, 0.5), inset 0 0 0 2px rgba(255, 255, 255, 0.2);
    border-radius: 8px 0 0 8px;
  }
}

/* 大屏幕 (1920px到2559px) */
@media (min-width: 1920px) and (max-width: 2559px) {
  .audio-recorder {
    max-width: 1400px;
    padding: 30px;
  }

  .control-content {
    padding: 30px 0;
  }

  .main-controls {
    gap: 24px;
    margin-bottom: 32px;
  }

  .record-btn,
  .stop-btn {
    min-width: 170px;
    height: 50px;
    font-size: 18px;
  }

  .header-icon {
    font-size: 20px;
  }

  .header-title {
    font-size: 18px;
  }

  .warning-icon {
    font-size: 28px;
  }

  .warning-title {
    font-size: 20px;
  }

  .direction-arrow {
    width: 100px;
    height: 100px;
  }

  .direction-text h3 {
    font-size: 28px;
  }

  .risk-description {
    font-size: 18px;
  }

  .category-title {
    font-size: 28px;
  }

  .result-main {
    gap: 32px;
  }

  .recording-status {
    padding: 24px;
    margin-bottom: 24px;
  }

  :deep(.el-statistic__content) {
    font-size: 32px;
  }

  /* 大屏幕边缘闪烁增强效果 */
  .audio-recorder.direction-left.risk-high::after {
    width: 25px;
    box-shadow: 0 0 35px rgba(255, 68, 68, 0.85), inset 0 0 0 3px rgba(255, 255, 255, 0.35);
    border-radius: 0 10px 10px 0;
  }

  .audio-recorder.direction-left.risk-medium::after {
    width: 20px;
    box-shadow: 0 0 25px rgba(255, 149, 0, 0.65), inset 0 0 0 2px rgba(255, 255, 255, 0.25);
    border-radius: 0 8px 8px 0;
  }

  .audio-recorder.direction-right.risk-high::after {
    width: 25px;
    box-shadow: 0 0 35px rgba(255, 68, 68, 0.85), inset 0 0 0 3px rgba(255, 255, 255, 0.35);
    border-radius: 10px 0 0 10px;
  }

  .audio-recorder.direction-right.risk-medium::after {
    width: 20px;
    box-shadow: 0 0 25px rgba(255, 149, 0, 0.65), inset 0 0 0 2px rgba(255, 255, 255, 0.25);
    border-radius: 8px 0 0 8px;
  }
}

@media (max-width: 1200px) {
  .audio-recorder {
    max-width: 100%;
    padding: 16px;
  }
}

@media (max-width: 768px) {
  .audio-recorder {
    padding: 12px;
  }

  .main-controls {
    flex-direction: column;
    align-items: center;
  }

  .record-btn,
  .stop-btn {
    width: 100%;
    max-width: 280px;
  }

  .recording-status {
    padding: 16px;
  }

  .action-buttons {
    flex-direction: column;
    align-items: center;
  }

  .action-buttons .el-button {
    width: 100%;
    max-width: 200px;
  }

  .result-main {
    gap: 20px;
  }

  .category-title {
    font-size: 20px;
  }

  .card-header {
    flex-wrap: wrap;
    gap: 8px;
  }
}

@media (max-width: 480px) {
  .audio-recorder {
    padding: 8px;
  }

  .el-card {
    margin-bottom: 16px;
  }

  .header-title {
    font-size: 14px;
  }

  .header-icon {
    font-size: 16px;
  }

  .category-title {
    font-size: 18px;
  }

  .main-controls {
    gap: 12px;
  }

  .record-btn,
  .stop-btn {
    min-width: 120px;
    height: 40px;
    font-size: 14px;
  }
}

/* Element Plus 组件简化样式 */
:deep(.el-statistic__head) {
  color: #6c757d;
  font-weight: 500;
  font-size: 14px;
}

:deep(.el-statistic__content) {
  color: #2c3e50;
  font-weight: 600;
  font-size: 28px;
}

:deep(.el-progress-circle) {
  margin: 4px;
}

:deep(.el-descriptions) {
  background: transparent;
}

:deep(.el-descriptions__header) {
  margin-bottom: 12px;
}

:deep(.el-descriptions-item__label) {
  font-weight: 500;
  color: #6c757d;
}

:deep(.el-descriptions-item__content) {
  font-weight: 500;
  color: #2c3e50;
}

:deep(.el-tag) {
  border: none;
  font-weight: 500;
}

:deep(.el-button) {
  transition: all 0.3s ease;
  font-weight: 500;
}

:deep(.el-progress-bar__outer) {
  border-radius: 8px;
  background-color: #e9ecef;
}

:deep(.el-progress-bar__inner) {
  border-radius: 8px;
}

:deep(.el-switch) {
  height: 22px;
}

:deep(.el-switch__core) {
  border-radius: 11px;
  height: 22px;
  line-height: 20px;
}

/* 音频播放器样式 */
.audio-player {
  border-radius: 8px;
}

/* 风险警告面板样式 */
.warning-panel {
  border-radius: 16px;
  border: 2px solid transparent;
  margin-bottom: 24px;
  transition: all 0.3s ease;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
}

.warning-panel.warning-high {
  border-color: #ff4444;
  box-shadow: 0 8px 32px rgba(255, 68, 68, 0.3);
  animation: warning-pulse-high 2s infinite;
}

.warning-panel.warning-medium {
  border-color: #ff9500;
  box-shadow: 0 6px 24px rgba(255, 149, 0, 0.3);
  animation: warning-pulse-medium 2.5s infinite;
}

.warning-panel.warning-low {
  border-color: #52c41a;
  box-shadow: 0 4px 16px rgba(82, 196, 26, 0.2);
}

@keyframes warning-pulse-high {

  0%,
  100% {
    transform: scale(1);
    box-shadow: 0 8px 32px rgba(255, 68, 68, 0.3);
  }

  50% {
    transform: scale(1.02);
    box-shadow: 0 12px 40px rgba(255, 68, 68, 0.5);
  }
}

@keyframes warning-pulse-medium {

  0%,
  100% {
    transform: scale(1);
    box-shadow: 0 6px 24px rgba(255, 149, 0, 0.3);
  }

  50% {
    transform: scale(1.01);
    box-shadow: 0 8px 32px rgba(255, 149, 0, 0.4);
  }
}

.warning-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 0;
}

.warning-icon {
  font-size: 24px;
  animation: icon-pulse 2s infinite;
}

.warning-icon-high {
  color: #ff4444;
}

.warning-icon-medium {
  color: #ff9500;
}

.warning-icon-low {
  color: #52c41a;
}

@keyframes icon-pulse {

  0%,
  100% {
    transform: scale(1);
  }

  50% {
    transform: scale(1.1);
  }
}

.warning-title {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  flex: 1;
}

.warning-status {
  font-weight: 600;
  font-size: 14px;
  padding: 8px 16px;
  border-radius: 20px;
}

.warning-content {
  padding: 20px 0;
}

.direction-indicator {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 16px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 12px;
  border: 1px solid #dee2e6;
}

.direction-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
  animation: arrow-bounce 2s infinite;
}

.direction-arrow.arrow-left {
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
  box-shadow: 0 4px 16px rgba(255, 107, 107, 0.3);
}

.direction-arrow.arrow-right {
  background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%);
  box-shadow: 0 4px 16px rgba(78, 205, 196, 0.3);
}

.direction-arrow.arrow-detecting {
  background: linear-gradient(135deg, #909399 0%, #6c7293 100%);
  box-shadow: 0 4px 16px rgba(144, 147, 153, 0.3);
}

@keyframes arrow-bounce {

  0%,
  100% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-5px);
  }
}

.direction-text h3 {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
}

.risk-description {
  margin: 0;
  font-size: 16px;
  color: #5a6c7d;
  font-weight: 500;
}

/* 高风险时让文字更突出 */
.warning-panel.warning-high .direction-text h3 {
  color: #ff4444;
  animation: text-glow 2s infinite;
}

.warning-panel.warning-high .risk-description {
  color: #d63031;
  font-weight: 600;
  animation: text-glow 2s infinite;
}

@keyframes text-glow {

  0%,
  100% {
    text-shadow: 0 0 5px rgba(255, 68, 68, 0.3);
  }

  50% {
    text-shadow: 0 0 20px rgba(255, 68, 68, 0.6);
  }
}
</style>
