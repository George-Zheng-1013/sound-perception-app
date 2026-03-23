<template>
    <div class="audio-recorder"
        :class="['direction-' + direction, (result && (result.risk_level_css || result.risk_level)) ? 'risk-' + mapRiskToCss(result?.risk_level, result?.confidence) : '']">
        <div v-if="result || isRealtimeListening || isRecording" class="risk-banner"
            :class="`risk-banner-${mapRiskToCss(result?.risk_level, result?.confidence)}`">
            <div class="risk-banner-main">
                <span class="risk-banner-kicker">实时声学态势</span>
                <strong class="risk-banner-title">{{ getVisualRiskLabel(mapRiskToCss(result?.risk_level,
                    result?.confidence)) }}</strong>
                <span class="risk-banner-subtitle">{{ getRiskActionSuggestion(mapRiskToCss(result?.risk_level,
                    result?.confidence), direction) }}</span>
            </div>
            <div class="risk-banner-meta">
                <el-tag effect="dark" :type="getRiskTagType(result?.risk_level || 'safe')">
                    {{ getRiskLevelText(result?.risk_level || 'safe') }}
                </el-tag>
                <span class="risk-banner-dir">方向：{{ getDirectionText(direction) }}</span>
            </div>
        </div>

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
                                :disabled="isRecording || isRealtimeListening" :loading="isStarting" class="record-btn"
                                round>
                                {{ isRecording ? '录音中...' : '开始录音' }}
                            </el-button>

                            <el-button type="danger" size="large" :icon="VideoPause" @click="stopRecording"
                                :disabled="!isRecording" class="stop-btn" round>
                                停止录音
                            </el-button>

                            <el-button type="success" size="large" :icon="isRealtimeListening ? VideoPause : Microphone"
                                @click="toggleRealtimeListening" :loading="isStartingRealtime" class="realtime-btn"
                                round>
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

        <div class="mobile-quick-actions">
            <el-button type="primary" :icon="Microphone" @click="startRecording"
                :disabled="isRecording || isRealtimeListening" :loading="isStarting" round>
                {{ isRecording ? '录音中' : '录音' }}
            </el-button>
            <el-button type="danger" :icon="VideoPause" @click="stopRecording" :disabled="!isRecording" round>
                停止
            </el-button>
            <el-button type="success" :icon="isRealtimeListening ? VideoPause : Microphone"
                @click="toggleRealtimeListening" :loading="isStartingRealtime" round>
                {{ isRealtimeListening ? '停止感知' : '实时感知' }}
            </el-button>
        </div>

        <!-- 音频预览和分析结果 -->

        <!-- 风险警告面板 -->
        <el-row :gutter="24" justify="center" v-if="(isRecording && direction) || result">
            <el-col :lg="20" :md="22" :sm="24">
                <el-card class="warning-panel" :class="[
                    `warning-${mapRiskToCss(result?.risk_level, result?.confidence)}`,
                    direction ? `warning-direction-${direction}` : ''
                ]" shadow="always">
                    <template #header>
                        <div class="warning-header">
                            <el-icon class="warning-icon"
                                :class="`warning-icon-${mapRiskToCss(result?.risk_level, result?.confidence)}`">
                                <Warning />
                            </el-icon>
                            <span class="warning-title">声源方向检测与风险提示</span>
                            <el-tag class="warning-status" :type="getRiskTagType(result?.risk_level || 'low')"
                                effect="dark" size="large">
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
                                <p class="risk-description">
                                    {{ getRiskDescription(mapRiskToCss(result?.risk_level, result?.confidence)) }}
                                </p>
                            </div>
                        </div>
                    </div>
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="24"
            v-if="audioUrl || isRealtimeListening || isRecording || result || isStartingRealtime || direction"
            justify="center">
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
                            <audio ref="audioElement" :src="audioUrl || undefined" controls class="audio-player"
                                @loadedmetadata="onAudioLoaded" @play="onAudioPlay" @pause="onAudioPause"></audio>
                            <div v-if="!audioUrl && (isRealtimeListening || isStartingRealtime || direction)"
                                class="realtime-placeholder">
                                <el-tag type="info">检测中...</el-tag>
                            </div>
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
                        <el-progress type="circle" :percentage="processingProgress" :width="120" :stroke-width="8"
                            color="#409EFF">
                            <template #default="{ percentage }">
                                <span class="progress-text">{{ percentage }}%</span>
                            </template>
                        </el-progress>
                        <p class="processing-message">正在使用AI模型分析您的录音内容...</p>
                    </div>
                </el-card>

                <el-card v-else-if="result || isRealtimeListening || isStartingRealtime || direction"
                    class="result-card" shadow="hover">
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
                                        <h3 class="category-title">{{ result?.category ?? (isRealtimeListening ?
                                            '检测中...' :
                                            '--') }}</h3>
                                        <div class="tags-container">
                                            <el-tag
                                                :type="result?.is_known ? 'success' : (isRealtimeListening ? 'info' : 'warning')"
                                                size="large" class="category-tag">
                                                {{ result?.is_known ? '已知类别' : (isRealtimeListening ? '检测中' : '未知类别') }}
                                            </el-tag>
                                            <el-tag v-if="result?.risk_level" :type="getRiskTagType(result.risk_level)"
                                                size="large" class="risk-tag">
                                                {{ getRiskLevelText(result.risk_level) }}
                                            </el-tag>
                                        </div>
                                    </div>

                                    <div class="confidence-display">
                                        <el-progress type="circle" :percentage="(result?.confidence ?? 0) * 100"
                                            :color="getConfidenceColor(result?.confidence ?? 0)" :width="100"
                                            :stroke-width="10">
                                            <template #default="{ percentage }">
                                                <span class="confidence-text">{{ percentage.toFixed(1) }}%</span>
                                            </template>
                                        </el-progress>
                                        <p class="confidence-label">置信度</p>
                                    </div>
                                </div>
                                <!-- 候选预测列表（按置信度降序） -->
                                <div v-if="result?.predictions && result?.predictions.length" style="margin-top:16px">
                                    <h4 style="margin:0 0 8px 0">候选结果</h4>
                                    <el-table :data="result?.predictions" style="width:100%" :show-header="false"
                                        size="small">
                                        <el-table-column prop="class_name" label="类别"></el-table-column>
                                        <el-table-column prop="confidence" label="置信度">
                                            <template #default="{ row }">{{ (row.confidence * 100).toFixed(1)
                                                }}%</template>
                                        </el-table-column>
                                        <el-table-column label="风险等级">
                                            <template #default="{ row }">
                                                <el-tag
                                                    :type="getRiskTagType(row.risk_level || getRiskLevelByClassId(row.class_id))">{{
                                                        getRiskLevelText(row.risk_level ||
                                                            getRiskLevelByClassId(row.class_id)) }}</el-tag>
                                            </template>
                                        </el-table-column>
                                    </el-table>
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
import { ref, onBeforeUnmount, onUnmounted } from 'vue'
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
import axios from 'axios'
// 类型定义
interface Prediction {
    class_id: number
    class_name: string
    confidence: number
}

interface AudioResult {
    category?: string
    confidence?: number
    is_known?: boolean
    class_id?: number
    risk_level?: string
    risk_level_css?: string
    // 多预测：按置信度降序
    predictions?: Prediction[]
    top_predictions?: Prediction[]
}

type DirectionValue = 'left' | 'right' | null

// 振动反馈工具函数（仅在支持的移动设备上工作）
const vibrate = (pattern: number | number[]) => {
    if (typeof navigator !== 'undefined' && navigator.vibrate) {
        try {
            navigator.vibrate(pattern)
        } catch (e) {
            console.warn('振动调用失败', e)
        }
    }
}

// 常用振动模式
const vibrationPatterns = {
    light: 30,           // 轻微振动 30ms
    medium: 50,          // 中等振动 50ms
    strong: 100,         // 强烈振动 100ms
    double: [50, 30, 50],     // 双击振动 50ms-停30ms-50ms
    alert: [100, 50, 100],    // 警报振动 100ms-停50ms-100ms
    highRisk: [200, 100, 200, 100, 200], // 高风险：快速多次振动
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
const pollingTimer = ref<number | null>(null) // 新增计时器引用
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
const directionAvailable = ref(true)
const directionUnavailableReason = ref<string | null>(null)
const isMobileDevice =
    typeof navigator !== 'undefined' && /android|iphone|ipad|ipod|mobile/i.test(navigator.userAgent)
let audioCtx: AudioContext | null = null
let leftAnalyser: AnalyserNode | null = null
let rightAnalyser: AnalyserNode | null = null
let leftEnergyEma = 0
let rightEnergyEma = 0
let realtimeLeftEnergyEma = 0
let realtimeRightEnergyEma = 0

const buildAudioConstraints = (): MediaTrackConstraints => {
    // 桌面端方向检测优先：关闭降噪/回声消除/自动增益，尽量保留左右通道差异
    if (!isMobileDevice) {
        return {
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false,
            sampleRate: { ideal: 48000 },
            channelCount: { ideal: 2 },
        }
    }

    // 移动端只保留采集稳定性，方向检测后续会降级
    return {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        sampleRate: 44100,
        channelCount: 1,
    }
}

const checkDirectionCapability = (audioStream: MediaStream, scene: '录音' | '实时感知') => {
    if (isMobileDevice) {
        directionAvailable.value = false
        directionUnavailableReason.value = '移动端麦克风通常无法提供稳定双通道，已自动关闭方向识别'
        ElMessage.info(`${scene}模式：${directionUnavailableReason.value}`)
        return false
    }

    // 尝试通过实际创建声音节点来验证双通道能力
    try {
        const testCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
        const testSrc = testCtx.createMediaStreamSource(audioStream)
        const testSplitter = testCtx.createChannelSplitter(2)
        testSrc.connect(testSplitter)
        // 成功创建意味着至少支持双通道分割
        testCtx.close()
        directionAvailable.value = true
        directionUnavailableReason.value = null
        return true
    } catch (err) {
        directionAvailable.value = false
        directionUnavailableReason.value = '当前设备未提供双通道输入，已关闭方向识别'
        ElMessage.warning(`${scene}模式：${directionUnavailableReason.value}`)
        return false
    }
}

const detectDirectionByEnergy = (
    left: AnalyserNode,
    right: AnalyserNode,
    state: { leftEma: number; rightEma: number },
) => {
    const size = left.fftSize
    const ldata = new Float32Array(size)
    const rdata = new Float32Array(size)
    left.getFloatTimeDomainData(ldata)
    right.getFloatTimeDomainData(rdata)

    const energy = (arr: Float32Array) => arr.reduce((s, v) => s + v * v, 0)
    const el = energy(ldata)
    const er = energy(rdata)

    // 静音或极低能量时不做方向判断，避免抖动
    if (el + er < 0.002) {
        return { detected: null as 'left' | 'right' | null, leftEma: state.leftEma, rightEma: state.rightEma }
    }

    // 使用 EMA 平滑瞬时能量，减少噪声干扰
    const alpha = 0.2
    state.leftEma = state.leftEma * (1 - alpha) + el * alpha
    state.rightEma = state.rightEma * (1 - alpha) + er * alpha

    const ratio = state.leftEma / (state.rightEma + 1e-9)
    const threshold = 1.25
    const detected: DirectionValue = ratio > threshold ? 'left' : ratio < 1 / threshold ? 'right' : null
    return { detected, leftEma: state.leftEma, rightEma: state.rightEma }
}

// 新增：处理来自服务器的预测数据（可被轮询或其他机制重用）
// 类型定义：来自后端的单条预测结构
type ServerPrediction = {
    class_id?: number
    class_name?: string
    class?: string
    confidence?: number
    risk_level?: string
    risk_label?: string
}
type ServerResult = {
    predictions?: ServerPrediction[]
    top_predictions?: ServerPrediction[]
    all_results?: ServerPrediction[]
    class_id?: number
    class_name?: string
    category?: string
    confidence?: number
    is_known?: boolean
    risk_level?: string
    risk_label?: string
}

type NormalizedPrediction = {
    class_id: number
    class_name: string
    confidence: number
    risk_level?: string
    risk_label?: string
}

const getPredRiskLevel = (p: NormalizedPrediction) => p.risk_level ?? getRiskLevelByClassId(p.class_id)

// 将后端二分类 risk + 置信度映射到前端三档视觉风险
const mapRiskToCss = (risk?: string | null, confidence?: number | null) => {
    const conf = Number(confidence ?? 0)
    if (risk === 'danger') {
        return conf >= 0.75 ? 'high' : 'medium'
    }
    if (risk === 'safe') {
        return conf >= 0.7 ? 'low' : 'medium'
    }
    return conf >= 0.8 ? 'medium' : 'low'
}

const getVisualRiskLabel = (visualRisk: string) => {
    switch (visualRisk) {
        case 'high':
            return '高风险预警'
        case 'medium':
            return '中风险警戒'
        default:
            return '低风险安全'
    }
}

const getRiskActionSuggestion = (visualRisk: string, dir: DirectionValue) => {
    const dirText = dir === 'left' ? '左侧' : dir === 'right' ? '右侧' : '周围'
    switch (visualRisk) {
        case 'high':
            return `请立即查看${dirText}并确认是否存在危险声源`
        case 'medium':
            return `请重点关注${dirText}环境变化，建议持续观察`
        default:
            return `当前环境总体安全，建议继续保持${dirText}监听`
    }
}

function applyPredictionsFromData(data: ServerResult) {
    try {
        const preds: NormalizedPrediction[] = []
        if (Array.isArray(data.predictions) && data.predictions.length > 0) {
            for (const p of data.predictions) {
                preds.push({
                    class_id: p.class_id ?? -1,
                    class_name: p.class_name ?? p.class ?? '未知类别',
                    confidence: Number(p.confidence ?? 0),
                    risk_level: p.risk_level,
                    risk_label: p.risk_label,
                })
            }
        } else if (Array.isArray(data.top_predictions) && data.top_predictions.length > 0) {
            for (const p of data.top_predictions) {
                preds.push({
                    class_id: p.class_id ?? -1,
                    class_name: p.class_name ?? '未知类别',
                    confidence: Number(p.confidence ?? 0),
                    risk_level: p.risk_level,
                    risk_label: p.risk_label,
                })
            }
        } else if (Array.isArray(data.all_results) && data.all_results.length > 0) {
            for (const p of data.all_results) {
                preds.push({
                    class_id: p.class_id ?? -1,
                    class_name: p.class_name ?? p.class ?? '未知类别',
                    confidence: Number(p.confidence ?? 0),
                    risk_level: p.risk_level,
                    risk_label: p.risk_label,
                })
            }
        } else if (data.class_id !== undefined) {
            preds.push({
                class_id: data.class_id,
                class_name: data.class_name ?? data.category ?? '未知类别',
                confidence: Number(data.confidence ?? 0),
                risk_level: data.risk_level,
                risk_label: data.risk_label,
            })
        }

        console.debug('[analyze] preds built', preds)

        if (preds.length === 0) return

        const now = Date.now()
        for (const p of preds) {
            const id = p.class_id
            const prev = emaMap.value[id] ?? p.confidence
            emaMap.value[id] = prev * (1 - emaAlpha) + p.confidence * emaAlpha
            lastSeenMap.value[id] = now
            if (getPredRiskLevel(p) === 'high' && (emaMap.value[id] ?? 0) >= 0.7) {
                holdUntil.value[id] = now + holdMs
            }
        }

        cleanupOldEma()

        // 按风险等级优先（高->低），风险相同时按 EMA(平滑置信度) 降序
        preds.sort((a, b) => {
            const ra = (riskOrder[getPredRiskLevel(b)] || 0) - (riskOrder[getPredRiskLevel(a)] || 0)
            if (ra !== 0) return ra
            return (emaMap.value[b.class_id] ?? b.confidence) - (emaMap.value[a.class_id] ?? a.confidence)
        })
        const displayTop = chooseDisplayTop(preds) ?? preds[0]
        maybeUpdateDisplay(displayTop, preds, data)
    } catch (err) {
        console.warn('处理服务器预测时出错', err)
    }
}

// (已移除) 旧的 toggleRealtime 函数被替换为 toggleRealtimeListening

// 页面销毁时清理定时器，防止内存泄漏
onUnmounted(() => {
    if (pollingTimer.value) clearInterval(pollingTimer.value)
})
//新增结束

// 持续分析方向（高灵敏度，只检测左右）
const analyzeDirection = () => {
    if (!leftAnalyser || !rightAnalyser || !directionAvailable.value) return
    const directionResult = detectDirectionByEnergy(leftAnalyser, rightAnalyser, {
        leftEma: leftEnergyEma,
        rightEma: rightEnergyEma,
    })
    if (directionResult.detected) direction.value = directionResult.detected
    leftEnergyEma = directionResult.leftEma
    rightEnergyEma = directionResult.rightEma

    requestAnimationFrame(analyzeDirection)
}

// 风险等级分类映射
const riskCategories = {
    low: [0, 1, 5, 6, 7, 8, 9, 10, 11, 18, 19, 20, 21, 23, 29, 41, 42],
    medium: [3, 12, 13, 14, 15, 16, 17, 22, 28, 30, 34, 35, 36, 43, 44, 45, 46, 47],
    high: [2, 4, 24, 25, 31, 32, 33, 37, 38, 39, 40]
}

// 根据类别ID获取风险等级
function getRiskLevelByClassId(classId: number): string {
    for (const id of (riskCategories.high || [])) {
        if (id === classId) return 'danger'
    }
    for (const id of (riskCategories.medium || [])) {
        if (id === classId) return 'danger'
    }
    // 其余视为 safe（低风险）
    return 'safe'
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
            audio: buildAudioConstraints()
        })

        const canDetectDirection = checkDirectionCapability(stream.value, '录音')

        // 初始化 Web Audio API 分析器
        if (canDetectDirection) {
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
            leftEnergyEma = 0
            rightEnergyEma = 0
            analyzeDirection()
        } else {
            direction.value = null
        }

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

        // 绑定本地实时流到 audio 元素用于预览（静音以避免回录）
        try {
            if (audioElement.value) {
                // @ts-ignore
                audioElement.value.srcObject = stream.value
                audioElement.value.muted = true
                const p = audioElement.value.play()
                if (p && typeof p.then === 'function') p.catch(() => { })
            }
        } catch (e) {
            console.warn('绑定本地流到 audio 元素失败', e)
        }

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
    // 解绑任何 srcObject，确保 audio 使用 file URL 播放
    try {
        if (audioElement.value) {
            // @ts-ignore
            audioElement.value.srcObject = null
        }
    } catch (e) {
        console.warn('清理音频元素 srcObject 失败', e)
    }
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

// EMA 平滑与高风险保持（在发送请求并设置 result 前后维护短期记忆）
const emaAlpha = 0.3
const holdMs = 4000
const emaMap = ref<Record<number, number>>({})
const lastSeenMap = ref<Record<number, number>>({})
const holdUntil = ref<Record<number, number>>({})
// 记录最后一次更新 result 的时间（ms），用于实时模式下的陈旧判断
const resultLastUpdated = ref<number>(0)

const nowMs = () => Date.now()

const isHighRisk = (classId: number) => {
    return getRiskLevelByClassId(classId) === 'high'
}

const cleanupOldEma = (thresholdMs = 20000) => {
    const now = nowMs()
    for (const idStr of Object.keys(lastSeenMap.value)) {
        const id = Number(idStr)
        if (now - (lastSeenMap.value[id] || 0) > thresholdMs) {
            delete lastSeenMap.value[id]
            delete emaMap.value[id]
            delete holdUntil.value[id]
        }
    }
}

const chooseDisplayTop = (preds: NormalizedPrediction[]) => {
    const now = nowMs()
    const held = Object.keys(holdUntil.value)
        .map(k => Number(k))
        .filter(id => (holdUntil.value[id] || 0) > now)

    if (held.length > 0) {
        let bestId = held[0]
        for (const id of held) {
            if ((emaMap.value[id] ?? 0) > (emaMap.value[bestId] ?? 0)) bestId = id
        }
        const p = preds.find(x => x.class_id === bestId)
        if (p) return p
    }

    let bestPred: typeof preds[0] | null = null
    for (const p of preds) {
        const e = emaMap.value[p.class_id] ?? p.confidence
        if (!bestPred || e > (emaMap.value[bestPred.class_id] ?? bestPred.confidence)) bestPred = p
    }
    return bestPred ?? preds[0] ?? null
}

// 决定是否更新界面显示：惰性规则，防止低风险短时覆盖高风险或当前显示
const switchMargin = 0.12 // 新候选需要超过当前 EMA 至少该差值才能替换
const riskOrder: Record<string, number> = { low: 0, medium: 1, high: 2 }

const setResultFromCandidate = (
    displayTop: NormalizedPrediction,
    preds: NormalizedPrediction[],
    data: ServerResult,
) => {
    console.debug('[display] setResultFromCandidate', displayTop, preds)
    // 为了保证圆圈内显示的置信度与候选列表第一条一致，
    // 在展示时使用 EMA 平滑后的置信度（若存在），并将 preds 中的 confidence 同步为 EMA。
    const mappedPreds = preds.map(p => ({
        ...p,
        confidence: emaMap.value[p.class_id] ?? p.confidence,
    }))

    const riskLevel = getPredRiskLevel(displayTop)
    result.value = {
        category: displayTop.class_name,
        confidence: emaMap.value[displayTop.class_id] ?? displayTop.confidence,
        is_known: data?.is_known ?? true,
        class_id: displayTop.class_id,
        risk_level: riskLevel,
        predictions: mappedPreds,
        top_predictions: mappedPreds,
    } as unknown as AudioResult
    resultLastUpdated.value = nowMs()

    // 根据风险等级触发相应的振动反馈
    if (riskLevel === 'danger') {
        vibrate(vibrationPatterns.highRisk) // 高风险：多次快速强烈振动
    } else if (riskLevel === 'medium') {
        vibrate(vibrationPatterns.alert)    // 中风险：警报振动
    } else {
        vibrate(vibrationPatterns.double)   // 低风险：双击振动
    }
}

const maybeUpdateDisplay = (
    displayTop: NormalizedPrediction | null,
    preds: NormalizedPrediction[],
    data: ServerResult,
) => {
    if (!displayTop) return
    const now = Date.now()
    const candId = displayTop.class_id
    const candEma = emaMap.value[candId] ?? displayTop.confidence
    const candRisk = getPredRiskLevel(displayTop)

    const cur = result.value
    if (!cur || cur.class_id === undefined) {
        setResultFromCandidate(displayTop, preds, data)
        return
    }

    const curId = cur.class_id as number
    const curEma = emaMap.value[curId] ?? (cur.confidence ?? 0)
    const curRisk = cur.risk_level ?? getRiskLevelByClassId(curId)

    // 如果当前为高风险且仍在 hold 时间内，保持不变
    if (curRisk === 'high' && (holdUntil.value[curId] || 0) > now) {
        return
    }

    // 如果候选风险更高，则允许切换（快速响应）
    if (riskOrder[candRisk] > riskOrder[curRisk]) {
        setResultFromCandidate(displayTop, preds, data)
        return
    }

    // 实时模式更灵敏：降低 margin，或当当前显示足够陈旧时强制更新
    const isRealtime = isRealtimeListening.value
    const realtimeSwitchMargin = 0.02
    const effectiveMargin = isRealtime ? realtimeSwitchMargin : switchMargin
    const staleMs = 3000
    if (candEma > curEma + effectiveMargin) {
        setResultFromCandidate(displayTop, preds, data)
        return
    }
    if (isRealtime && now - (resultLastUpdated.value || 0) > staleMs) {
        // 如果当前显示已经很久没有更新了，接受新的候选以保持界面活跃
        setResultFromCandidate(displayTop, preds, data)
        return
    }

    // 其余情况：保留当前显示
}

// 发送音频进行分析（支持多预测），并维护 EMA 与 hold
const sendAudioForAnalysis = async (audioBlob: Blob, silent: boolean = false) => {
    const formData = new FormData()
    const file = new File([audioBlob], 'recording.webm', { type: 'audio/webm' })
    formData.append('audio', file)

    try {
        console.debug('[analyze] sending segment, size=', audioBlob.size)
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData,
        })
        // 先尝试解析为 JSON（若不是 JSON 则尝试读取文本以便诊断 500 错误）
        let data: any = null
        try {
            // 使用 clone() 避免消费原始 response 的 body 流
            data = await response.clone().json()
        } catch (jsonErr) {
            console.warn('解析后端返回 JSON 失败', jsonErr)
        }

        if (!response.ok) {
            // 尝试获取响应文本以便查看错误细节（使用 clone() 读取文本）
            let respText: string | null = null
            try {
                respText = await response.clone().text()
            } catch (tErr) {
                console.warn('读取非 OK 响应文本失败', tErr)
            }
            console.warn('[analyze] 非 OK 响应', response.status, respText)
            error.value = `音频分析服务错误: ${response.status} ${respText ? (' - ' + respText.slice(0, 200)) : ''}`
            if (!silent) ElMessage.error('音频分析服务返回错误')
            return
        }

        console.debug('[analyze] response data=', data)

        const preds: NormalizedPrediction[] = []
        if (Array.isArray(data.predictions) && data.predictions.length > 0) {
            for (const p of data.predictions) {
                preds.push({
                    class_id: p.class_id ?? -1,
                    class_name: p.class_name ?? p.class ?? '未知类别',
                    confidence: Number(p.confidence ?? 0),
                    risk_level: p.risk_level,
                    risk_label: p.risk_label,
                })
            }
        } else if (Array.isArray(data.top_predictions) && data.top_predictions.length > 0) {
            for (const p of data.top_predictions) {
                preds.push({
                    class_id: p.class_id ?? -1,
                    class_name: p.class_name ?? '未知类别',
                    confidence: Number(p.confidence ?? 0),
                    risk_level: p.risk_level,
                    risk_label: p.risk_label,
                })
            }
        } else if (Array.isArray(data.all_results) && data.all_results.length > 0) {
            for (const p of data.all_results) {
                preds.push({
                    class_id: p.class_id ?? -1,
                    class_name: p.class_name ?? p.class ?? '未知类别',
                    confidence: Number(p.confidence ?? 0),
                    risk_level: p.risk_level,
                    risk_label: p.risk_label,
                })
            }
        } else if (data.class_id !== undefined) {
            preds.push({
                class_id: data.class_id,
                class_name: data.class_name ?? data.category ?? '未知类别',
                confidence: Number(data.confidence ?? 0),
                risk_level: data.risk_level,
                risk_label: data.risk_label,
            })
        }

        if (preds.length === 0) {
            result.value = {
                category: data.class_name ?? '未知类别',
                confidence: Number(data.confidence ?? 0),
                is_known: data.is_known ?? false,
                class_id: data.class_id ?? -1,
                risk_level: data.risk_level ?? (data.class_id !== undefined ? getRiskLevelByClassId(data.class_id) : 'medium'),
                predictions: [],
                top_predictions: [],
            } as unknown as AudioResult
            if (!silent) ElMessage.success('音频分析完成')
            return
        }

        const now = nowMs()
        for (const p of preds) {
            const id = p.class_id
            const prev = emaMap.value[id] ?? p.confidence
            emaMap.value[id] = prev * (1 - emaAlpha) + p.confidence * emaAlpha
            lastSeenMap.value[id] = now
            if (getPredRiskLevel(p) === 'high' && (emaMap.value[id] ?? 0) >= 0.7) {
                holdUntil.value[id] = now + holdMs
            }
        }

        console.debug('[analyze] emaMap after update', emaMap.value)

        cleanupOldEma()

        // 按风险等级优先（高->低），风险相同时按 EMA(平滑置信度) 降序
        preds.sort((a, b) => {
            const ra = (riskOrder[getPredRiskLevel(b)] || 0) - (riskOrder[getPredRiskLevel(a)] || 0)
            if (ra !== 0) return ra
            return (emaMap.value[b.class_id] ?? b.confidence) - (emaMap.value[a.class_id] ?? a.confidence)
        })

        const displayTop = chooseDisplayTop(preds) ?? preds[0]
        console.debug('[analyze] displayTop', displayTop, 'currentResult', result.value)
        maybeUpdateDisplay(displayTop, preds, data)

        if (!silent) ElMessage.success('音频分析完成')
    } catch (err: unknown) {
        console.warn('后端服务不可用或返回错误:', err)
        // 不再自动回退到模拟数据以避免频繁的虚假提示。
        // 记录错误并仅在首次出现时提示一次给用户。
        error.value = '音频分析后端不可用，请检查 http://localhost:5000 '
        try {
            // 使用 window 上的标记避免重复弹窗
            if (!window.__audioBackendErrorShown) {
                ElMessage.error('音频分析服务不可用，已停止使用模拟数据')
                window.__audioBackendErrorShown = true
            }
        } catch (e) {
            console.warn('提示错误时发生异常', e)
        }
        return
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

// 获取风险等级标签类型（二分类）
const getRiskTagType = (riskLevel: string) => {
    switch (riskLevel) {
        case 'danger':
            return 'danger'
        case 'safe':
            return 'success'
        default:
            return 'info'
    }
}

// 获取风险等级文本（展示为中文二分类）
const getRiskLevelText = (riskLevel: string) => {
    switch (riskLevel) {
        case 'danger':
            return '危险'
        case 'safe':
            return '安全'
        default:
            return '未知'
    }
}

// 获取方向文本
const getDirectionText = (direction: 'left' | 'right' | null) => {
    if (!directionAvailable.value) return '当前设备不支持'
    if (direction === 'left') return '左侧'
    if (direction === 'right') return '右侧'
    if (isRecording.value || isRealtimeListening.value) return '检测中...'
    return '未检测'
}

// 获取风险描述（基于三档视觉风险）
const getRiskDescription = (visualRisk: string) => {
    switch (visualRisk) {
        case 'high':
            return '高风险：疑似危险事件声源，请立即确认并采取措施。'
        case 'medium':
            return '中风险：声源存在异常特征，建议持续关注与复核。'
        default:
            return '低风险：环境整体稳定，持续监测中。'
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
// 后台短片段录音（用于实时上传分析，不依赖噪声触发）
let realtimeRecorder: MediaRecorder | null = null
let realtimeSegmentTimer: number | null = null
// 并发控制：允许最多同时几个实时请求进行中，避免完全串行导致丢片或卡顿
let pendingRealtimeRequests = 0
const MAX_CONCURRENT_REALTIME = 2

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
            audio: buildAudioConstraints()
        })

        const canDetectDirection = checkDirectionCapability(realtimeStream.value, '实时感知')

        // 初始化音频分析器
        realtimeAudioCtx = new AudioContext()
        const srcNode = realtimeAudioCtx.createMediaStreamSource(realtimeStream.value)
        const splitter = realtimeAudioCtx.createChannelSplitter(2)
        srcNode.connect(splitter)

        // 创建音量检测分析器
        realtimeAnalyser = realtimeAudioCtx.createAnalyser()
        realtimeAnalyser.fftSize = 2048
        srcNode.connect(realtimeAnalyser)

        // 创建方向检测分析器（仅在方向可用时）
        if (canDetectDirection) {
            realtimeLeftAnalyser = realtimeAudioCtx.createAnalyser()
            realtimeRightAnalyser = realtimeAudioCtx.createAnalyser()
            realtimeLeftAnalyser.fftSize = 2048
            realtimeRightAnalyser.fftSize = 2048
            splitter.connect(realtimeLeftAnalyser, 0)
            splitter.connect(realtimeRightAnalyser, 1)
            realtimeLeftEnergyEma = 0
            realtimeRightEnergyEma = 0
        } else {
            realtimeLeftAnalyser = null
            realtimeRightAnalyser = null
            direction.value = null
        }

        isRealtimeListening.value = true
        isStartingRealtime.value = false

        // 只做方向分析；不再依赖声音触发录音，改为始终每秒上传短片段供后端分析
        if (canDetectDirection) startRealtimeDirectionAnalysis()

        // 启动每秒独立短片段录音：每秒创建一个 MediaRecorder，记录 1s 后停止，确保每个 Blob 为完整 WebM 文件
        try {
            const mimeType = 'audio/webm;codecs=opus'

            const recordSegment = () => {
                if (!realtimeStream.value) return
                if (isRecording.value) return
                if (pendingRealtimeRequests >= MAX_CONCURRENT_REALTIME) return

                const segRecorder = new MediaRecorder(realtimeStream.value!, { mimeType })
                const chunks: Blob[] = []

                segRecorder.ondataavailable = (ev: BlobEvent) => {
                    if (ev.data && ev.data.size > 0) chunks.push(ev.data)
                }

                segRecorder.onstop = async () => {
                    if (chunks.length === 0) return
                    const blob = new Blob(chunks, { type: mimeType })
                    try {
                        console.debug('[realtime] segment onstop, blob size=', blob.size)
                        pendingRealtimeRequests++
                        await sendAudioForAnalysis(blob, true)
                    } catch (err) {
                        console.warn('实时片段分析失败', err)
                    } finally {
                        pendingRealtimeRequests--
                    }
                }

                try {
                    segRecorder.start()
                    // 停止录音在 1000ms 后，确保为完整短录音
                    setTimeout(() => {
                        try {
                            if (segRecorder.state !== 'inactive') segRecorder.stop()
                        } catch (e) {
                            console.warn('停止分段录音出错', e)
                        }
                    }, 1000)
                } catch (e) {
                    console.warn('启动分段录音失败', e)
                }
            }

            // 立即启动一次，然后每秒触发
            recordSegment()
            realtimeSegmentTimer = window.setInterval(recordSegment, 1000)

            // 将实时流绑定到页面的 audio 元素，用于预览（静音以避免回录）
            try {
                if (audioElement.value) {
                    // @ts-ignore
                    audioElement.value.srcObject = realtimeStream.value
                    audioElement.value.muted = true
                    const p = audioElement.value.play()
                    if (p && typeof p.then === 'function') p.catch(() => { })
                }
            } catch (e) {
                console.warn('绑定实时流到 audio 元素失败', e)
            }
        } catch (err) {
            console.warn('无法启动后台实时片段录音器', err)
        }

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

    // 停止后台片段录音
    try {
        if (realtimeRecorder) {
            if (realtimeRecorder.state !== 'inactive') realtimeRecorder.stop()
            realtimeRecorder = null
        }
    } catch (err) {
        console.warn('停止实时Recorder时出错', err)
    }

    // 停止每秒分段录音定时器
    if (realtimeSegmentTimer) {
        clearInterval(realtimeSegmentTimer)
        realtimeSegmentTimer = null
    }

    // 清除 audio 元素的流
    try {
        if (audioElement.value) {
            // @ts-ignore
            audioElement.value.srcObject = null
            audioElement.value.pause()
        }
    } catch (e) {
        console.warn('清理 audio 元素失败', e)
    }

    // 如果正在录音，停止录音
    if (isRecording.value) {
        stopRecording()
    }

    isEnvironmentNoisy.value = false
    direction.value = null

    ElMessage.info('实时感知已停止')
}

// (已移除) 声音触发的自动录音逻辑。实时识别已改为持续每秒上传短片段处理，
// 如需恢复基于噪声触发的行为，可在此处恢复相应实现。

// 实时方向分析
const startRealtimeDirectionAnalysis = () => {
    const analyzeRealtimeDirection = () => {
        if (!realtimeLeftAnalyser || !realtimeRightAnalyser || !isRealtimeListening.value || !directionAvailable.value) return

        const directionResult = detectDirectionByEnergy(realtimeLeftAnalyser, realtimeRightAnalyser, {
            leftEma: realtimeLeftEnergyEma,
            rightEma: realtimeRightEnergyEma,
        })
        if (directionResult.detected) direction.value = directionResult.detected
        realtimeLeftEnergyEma = directionResult.leftEma
        realtimeRightEnergyEma = directionResult.rightEma

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
    --risk-high: #e03131;
    --risk-medium: #f08c00;
    --risk-low: #2f9e44;
    --surface-main: #f2f5f9;
    --surface-card: #ffffff;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    min-height: 100vh;
    background: radial-gradient(circle at 10% 0%, #eef5ff 0%, #f3f6fa 45%, #f8fafc 100%);
    position: relative;
}

.risk-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    margin: 4px 0 18px;
    padding: 14px 16px;
    border-radius: 14px;
    border: 1px solid transparent;
    background: #fff;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
}

.risk-banner-main {
    display: flex;
    flex-direction: column;
    gap: 3px;
}

.risk-banner-kicker {
    font-size: 12px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    opacity: 0.85;
}

.risk-banner-title {
    font-size: 24px;
    line-height: 1.1;
    font-weight: 800;
}

.risk-banner-subtitle {
    font-size: 13px;
    opacity: 0.95;
}

.risk-banner-meta {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
}

.risk-banner-dir {
    font-size: 13px;
    font-weight: 600;
}

.risk-banner-high {
    border-color: rgba(224, 49, 49, 0.45);
    background: linear-gradient(92deg, rgba(224, 49, 49, 0.22), rgba(255, 237, 237, 0.95));
    color: #651111;
    animation: high-risk-blink 0.9s infinite;
}

.risk-banner-medium {
    border-color: rgba(240, 140, 0, 0.4);
    background: linear-gradient(92deg, rgba(240, 140, 0, 0.2), rgba(255, 247, 230, 0.95));
    color: #5c3d00;
}

.risk-banner-low {
    border-color: rgba(47, 158, 68, 0.35);
    background: linear-gradient(92deg, rgba(47, 158, 68, 0.18), rgba(233, 248, 237, 0.95));
    color: #123d20;
}

.mobile-quick-actions {
    display: none;
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
    background: var(--surface-card);
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
    background: var(--surface-card);
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
    background: var(--surface-card);
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
    background: var(--surface-card);
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
        padding: 12px 12px 96px;
    }

    .risk-banner {
        align-items: flex-start;
        flex-direction: column;
        gap: 10px;
        padding: 12px;
    }

    .risk-banner-title {
        font-size: 20px;
    }

    .risk-banner-meta {
        align-items: flex-start;
    }

    .main-controls {
        display: none;
    }

    .mobile-quick-actions {
        position: fixed;
        left: 10px;
        right: 10px;
        bottom: 10px;
        z-index: 1200;
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 8px;
        padding: 10px;
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.94);
        backdrop-filter: blur(10px);
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.2);
    }

    .mobile-quick-actions :deep(.el-button) {
        margin: 0;
        min-height: 44px;
        font-weight: 700;
        font-size: 13px;
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
        padding: 8px 8px 92px;
    }

    .risk-banner-title {
        font-size: 18px;
    }

    .risk-banner-subtitle {
        font-size: 12px;
    }

    .mobile-quick-actions {
        left: 8px;
        right: 8px;
        bottom: 8px;
        padding: 8px;
        gap: 6px;
    }

    .mobile-quick-actions :deep(.el-button) {
        min-height: 40px;
        font-size: 12px;
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
    border-color: var(--risk-high);
    box-shadow: 0 10px 36px rgba(224, 49, 49, 0.42);
    animation: warning-pulse-high 1.4s infinite;
}

.warning-panel.warning-medium {
    border-color: var(--risk-medium);
    box-shadow: 0 8px 28px rgba(240, 140, 0, 0.34);
    animation: warning-pulse-medium 2s infinite;
}

.warning-panel.warning-low {
    border-color: var(--risk-low);
    box-shadow: 0 4px 16px rgba(47, 158, 68, 0.24);
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
    color: var(--risk-high);
}

.warning-icon-medium {
    color: var(--risk-medium);
}

.warning-icon-low {
    color: var(--risk-low);
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
    color: var(--risk-high);
    animation: text-glow 2s infinite;
}

.warning-panel.warning-high .risk-description {
    color: #972020;
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
