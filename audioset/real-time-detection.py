import os
import time

import torch
import torch.nn as nn
import numpy as np
import sounddevice as sd
import soundfile as sf
import scipy.signal as signal
import queue

from panns_dataset import ALL_LABELS
from train_cnn14_finetune import load_cnn14_for_features, SimpleClassifier


SAMPLE_RATE = 16000
WINDOW_SECONDS = 5
STEP_SECONDS = 1

WINDOW_SIZE = SAMPLE_RATE * WINDOW_SECONDS
STEP_SIZE = SAMPLE_RATE * STEP_SECONDS

THRESHOLD = 0.25

OUTPUT_DIR = r"D:\audioset\rt_windows"
os.makedirs(OUTPUT_DIR, exist_ok=True)

COMBINED_MODEL_PATH = r"D:\audioset\cnn14_mlp_combined.pt"
FORCE_INPUT_DEVICE_INDEX = None

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("使用设备:", device)

try:
    default_input = sd.query_devices(kind="input")
    print(f"已检测到默认麦克风: {default_input['name']} (index={sd.default.device[0]})")
except Exception as e:
    print(f"查询默认麦克风失败: {e}")

print("可用输入设备列表:")
for idx, dev in enumerate(sd.query_devices()):
    if dev["max_input_channels"] > 0:
        print(f"  #{idx}: {dev['name']} (channels={dev['max_input_channels']})")

# =============================
# 加载 CNN14 + MLP 分类器（优先读取合并模型）
# =============================

checkpoint_path = r"D:\audioset\Cnn14_16k_mAP=0.438.pth"

use_combined = False
cnn_model = None
classifier = None

if os.path.exists(COMBINED_MODEL_PATH):
    try:
        state = torch.load(COMBINED_MODEL_PATH, map_location=device)
        if isinstance(state, dict) and "cnn_state" in state and "mlp_state" in state:
            cnn_model = load_cnn14_for_features(checkpoint_path)
            cnn_model.load_state_dict(state["cnn_state"])

            input_dim = state.get("cnn_input_dim", 2048)
            num_classes = len(ALL_LABELS)
            classifier = SimpleClassifier(input_dim, num_classes).to(device)
            classifier.load_state_dict(state["mlp_state"])

            use_combined = True
            print(f"已从合并模型 state_dict 加载权重: {COMBINED_MODEL_PATH}")
    except Exception as e:
        print(f"加载合并模型失败，回退到 cnn+mlp 分开加载: {e}")

if not use_combined:
    cnn_model = load_cnn14_for_features(checkpoint_path)

    input_dim = 2048
    num_classes = len(ALL_LABELS)
    classifier = SimpleClassifier(input_dim, num_classes).to(device)

    classifier_state = torch.load("mlp_classifier_best.pth", map_location=device)
    classifier.load_state_dict(classifier_state)

    print("特征提取模型和分类头加载完成（cnn+mlp 模式）")

    safe_state = {
        "cnn_state": cnn_model.state_dict(),
        "mlp_state": classifier.state_dict(),
        "cnn_input_dim": input_dim,
    }
    try:
        torch.save(safe_state, COMBINED_MODEL_PATH)
        print(f"已保存安全合并模型 state_dict 到: {COMBINED_MODEL_PATH}")
    except Exception as e:
        print(f"保存合并模型失败（不影响当前运行）: {e}")

cnn_model = cnn_model.to(device).eval()
classifier = classifier.to(device).eval()


def remove_dc(audio: np.ndarray):
    return audio - np.mean(audio)


def highpass_filter(audio: np.ndarray, sr=16000, cutoff=80):
    b, a = signal.butter(4, cutoff / (sr / 2), btype="high")
    return signal.lfilter(b, a, audio)


class RMSController:
    def __init__(self, target_rms=0.1, max_gain=8.0):
        self.target_rms = target_rms
        self.max_gain = max_gain

    def process(self, audio: np.ndarray):
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 1e-6:
            return audio
        gain = self.target_rms / rms
        gain = min(gain, self.max_gain)
        audio = audio * gain
        audio = np.clip(audio, -1.0, 1.0)
        return audio


def spectral_denoise(audio: np.ndarray):
    fft = np.fft.rfft(audio)
    mag = np.abs(fft)
    phase = np.angle(fft)
    noise_floor = np.mean(mag[:10])
    mag = np.maximum(mag - noise_floor, 0)
    cleaned = mag * np.exp(1j * phase)
    return np.fft.irfft(cleaned)


USE_DENOISE = False


def preprocess_audio(wav: np.ndarray, sr=16000):
    wav = remove_dc(wav)
    wav = highpass_filter(wav, sr)
    controller = RMSController(target_rms=0.1)
    wav = controller.process(wav)
    if USE_DENOISE:
        wav = spectral_denoise(wav)
    return wav


audio_queue = queue.Queue()
ring_buffer = np.zeros(WINDOW_SIZE, dtype=np.float32)
window_index = 0


def audio_callback(indata, frames, time, status):
    if status:
        print("音频回调状态:", status)
    audio_queue.put(indata.copy())


def predict(audio_np):
    global window_index

    max_amp = float(np.max(np.abs(audio_np)))
    print(f"[窗口] 最大幅度={max_amp:.3f}")

    audio_flat = np.asarray(audio_np, dtype=np.float32).reshape(-1)
    audio_flat = preprocess_audio(audio_flat, SAMPLE_RATE)

    waveform = torch.tensor(audio_flat, dtype=torch.float32).to(device)
    waveform = waveform.unsqueeze(0)  # [1, T]

    with torch.no_grad():
        out_dict = cnn_model(waveform)
        emb = out_dict["clipwise_output"]
        logits = classifier(emb)
        probs = torch.sigmoid(logits).squeeze(0)

    indices = (probs >= THRESHOLD).nonzero().flatten().tolist()

    if len(indices) == 0:
        return [], probs.cpu().numpy()

    from panns_dataset import ALL_LABELS
    labels = [ALL_LABELS[i] for i in indices]

    return labels, probs.cpu().numpy()

# =============================
# 开始实时识别
# =============================
print("开始实时识别（5秒窗口，每1秒更新）...")

step_counter = 0

stream_kwargs = dict(
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="float32",
    callback=audio_callback,
)
if FORCE_INPUT_DEVICE_INDEX is not None:
    stream_kwargs["device"] = FORCE_INPUT_DEVICE_INDEX

with sd.InputStream(**stream_kwargs):
    while True:
        data = audio_queue.get().flatten()

        ring_buffer = np.roll(ring_buffer, -len(data))
        ring_buffer[-len(data):] = data

        step_counter += len(data)

        if step_counter >= STEP_SIZE:
            step_counter = 0

            labels, probs = predict(ring_buffer)

            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            print("=" * 40)
            print(f"[{now_str}] 检测结果:")
            import numpy as _np
            probs_np = _np.asarray(probs, dtype=float)

            display_threshold = 0.20
            has_any = False
            for name, p in zip(ALL_LABELS, probs_np):
                if p >= display_threshold:
                    print(f"  {name:30s}: {p:6.2%}")
                    has_any = True
            if not has_any:
                print("未检测到声音")
