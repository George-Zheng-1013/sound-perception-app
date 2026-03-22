import os
import sys
import time
import numpy as np
import torch
import torch.nn as nn
import soundfile as sf
import scipy.signal as signal
import threading
import sounddevice as sd
import sqlite3
import datetime
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS

# 必须导入 CNN14 相关组件
from panns_dataset import ALL_LABELS
from train_cnn14_finetune import load_cnn14_for_features, SimpleClassifier

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "temp_audio")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 加载 CSV 风险映射（class_id -> 'safe'|'danger'）
CLASS_RISK_CSV = os.path.join(os.path.dirname(__file__), 'risk_labels.csv')
class_risk_map = {}
def load_class_risk_map():
    global class_risk_map
    if not os.path.exists(CLASS_RISK_CSV):
        print(f"风险映射文件未找到: {CLASS_RISK_CSV}，将使用默认映射")
        return
    import csv
    try:
        with open(CLASS_RISK_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # 尝试识别列名
            id_key = None
            risk_key = None
            headers = [h.lower() for h in reader.fieldnames or []]
            for h in headers:
                if 'class' in h and 'id' in h:
                    id_key = h
                if 'risk' in h or 'label' in h:
                    risk_key = h
            # 回退到常见名
            if id_key is None:
                id_key = reader.fieldnames[0]
            if risk_key is None:
                risk_key = reader.fieldnames[1] if len(reader.fieldnames) > 1 else reader.fieldnames[0]
            for row in reader:
                try:
                    cid = int(row[id_key])
                except Exception:
                    continue
                r = str(row.get(risk_key, '')).strip().lower()
                # 规范化：中文/英文映射到 safe/danger
                if r in ('safe','s','ok','normal','safe '):
                    class_risk_map[cid] = 'safe'
                elif r in ('danger','risk','dangerous','d','risk '):
                    class_risk_map[cid] = 'danger'
                elif '安' in r:
                    class_risk_map[cid] = 'safe'
                elif '危' in r or '险' in r:
                    class_risk_map[cid] = 'danger'
                else:
                    # 默认根据值长度或数值猜测
                    class_risk_map[cid] = 'danger' if r in ('1','true','yes') else 'safe'
        print(f"已加载风险映射，条目数={len(class_risk_map)}")
    except Exception as e:
        print(f"加载风险映射出错: {e}")

load_class_risk_map()

# --- 1. 新增：信号预处理函数（搬运自 real-time-detection.py） ---
def preprocess_audio(wav: np.ndarray, sr=16000):
    # 去直流偏置
    wav = wav - np.mean(wav)
    # 高通滤波
    b, a = signal.butter(4, 80 / (sr / 2), btype="high")
    wav = signal.lfilter(b, a, wav)
    # RMS 自动增益控制
    rms = np.sqrt(np.mean(wav ** 2))
    if rms > 1e-6:
        target_rms = 0.1
        gain = min(target_rms / rms, 8.0)
        wav = np.clip(wav * gain, -1.0, 1.0)
    return wav

# --- 2. 修改：模型加载逻辑（改为加载 CNN14 + MLP） ---
def load_model(options):
    device = torch.device("cuda" if options.get("use_gpu") and torch.cuda.is_available() else "cpu")
    
    # 加载特征提取器
    checkpoint_path = r"D:\audioset\Cnn14_16k_mAP=0.438.pth"
    cnn_model = load_cnn14_for_features(checkpoint_path)
    
    # 加载分类头
    num_classes = len(ALL_LABELS)
    classifier = SimpleClassifier(2048, num_classes).to(device)
    
    # 加载合并权重
    combined_path = r"D:\audioset\cnn14_mlp_combined.pt"
    if os.path.exists(combined_path):
        state = torch.load(combined_path, map_location=device)
        cnn_model.load_state_dict(state["cnn_state"])
        classifier.load_state_dict(state["mlp_state"])
        print(f"成功加载 CNN14 联合模型")
    else:
        print("未找到合并权重，请检查路径")

    return cnn_model.to(device).eval(), classifier.to(device).eval(), None, ALL_LABELS

# --- 3. 修改：音频分析函数（改为概率阈值逻辑） ---
def analyze_audio(cnn_model, classifier, _, labels, audio_path, options):
    device = next(cnn_model.parameters()).device
    try:
        # 读取并预处理
        wav, sr = sf.read(audio_path)
        if len(wav.shape) > 1: wav = np.mean(wav, axis=1) # 转单声道
        # 确保采样率为 16000（ffmpeg 已尝试转换），并对过短音频进行补齐以避免后续计算产生 0 长度问题
        target_sr = 16000
        if sr != target_sr:
            # 简单重采样（使用 scipy.signal.resample）
            try:
                num_samples = int(len(wav) * target_sr / sr)
                wav = signal.resample(wav, num_samples)
                sr = target_sr
            except Exception:
                pass

        # 处理过短的音频：至少保持 1 秒长度（16000 samples），不足则补零
        min_length = target_sr  # 1s
        if len(wav) < min_length:
            pad_len = min_length - len(wav)
            wav = np.concatenate([wav, np.zeros(pad_len, dtype=wav.dtype)])

        wav = preprocess_audio(wav, sr)
        
        waveform = torch.tensor(wav, dtype=torch.float32).to(device).unsqueeze(0)
        
        with torch.no_grad():
            out_dict = cnn_model(waveform)
            emb = out_dict["clipwise_output"]
            logits = classifier(emb)
            probs = torch.sigmoid(logits).squeeze(0)
            
        # --- 修改点：提取多个结果 ---
        THRESHOLD = 0.1  # 只要概率大于10%的结果都记录
        
        # 获取所有概率值及其对应的索引
        all_probs = probs.cpu().numpy()
        
        # 找到所有超过阈值的索引，并按概率从大到小排序
        top_indices = np.where(all_probs >= THRESHOLD)[0]
        top_indices = top_indices[np.argsort(all_probs[top_indices])[::-1]]
        
        results_list = []
        for idx in top_indices:
            # 默认二分类：high/medium -> danger, low -> safe（后端将返回二分类）
            prob = float(all_probs[idx])
            prev_risk = "high" if prob > 0.6 else "medium"
            # 优先使用 CSV 映射，如不存在则按概率推断
            mapped = class_risk_map.get(int(idx))
            if mapped in ('safe','danger'):
                bin_risk = mapped
            else:
                bin_risk = "danger" if prev_risk in ("high", "medium") else "safe"
            css_risk = "high" if bin_risk == "danger" else "low"
            results_list.append({
                "class_id": int(idx),
                "class_name": labels[idx],
                "confidence": prob,
                "risk_level": bin_risk,
                "risk_level_css": css_risk
            })
            
        # 如果一个都没匹配到，给一个兜底
        if not results_list:
            top_idx = np.argmax(all_probs)
            prob = float(all_probs[top_idx])
            prev_risk = "high" if prob > 0.6 else "medium"
            mapped = class_risk_map.get(int(top_idx))
            if mapped in ('safe','danger'):
                bin_risk = mapped
            else:
                bin_risk = "danger" if prev_risk in ("high", "medium") else "safe"
            css_risk = "high" if bin_risk == "danger" else "low"
            results_list.append({
                "class_id": int(top_idx),
                "class_name": labels[top_idx],
                "confidence": prob,
                "risk_level": bin_risk,
                "risk_level_css": css_risk
            })

        # 返回格式调整：主结果依然保留，但新增 all_results 列表
        # 在顶层返回二分类 risk_level 与用于样式的 risk_level_css
        top = results_list[0]
        return {
            "status": "success",
            "class_name": top["class_name"],
            "confidence": top["confidence"],
            "risk_level": top.get("risk_level"),
            "risk_level_css": top.get("risk_level_css"),
            "all_results": results_list,  # 保存排序后的列表
            "is_known": top["confidence"] >= 0.25
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 4. 实时监听线程保持不变，但调用新的分析逻辑 ---
def realtime_worker():
    SAMPLE_RATE = 16000
    DURATION = 5 
    while True:
        try:
            filename = f"rt_{int(time.time())}"
            wav_path = os.path.join(UPLOAD_FOLDER, f"{filename}.wav")
            
            recording = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1)
            sd.wait()
            sf.write(wav_path, recording, SAMPLE_RATE)
            
            result = analyze_audio(global_model, global_classifier, None, global_labels, wav_path, {})
            save_result_to_db(filename, result)
            print(f"[实时识别]: {result.get('class_name')} ({result.get('confidence'):.2%})")
            
            if os.path.exists(wav_path): os.remove(wav_path)
        except Exception as e:
            print(f"实时模块错误: {e}")
        time.sleep(0.1)

# --- 数据库初始化与保存函数（保持 testaudio_rt.py 原样） ---
def init_db():
    db_path = os.path.join(os.path.dirname(__file__), "audio_results.db")
    conn = sqlite3.connect(db_path)
    conn.execute('CREATE TABLE IF NOT EXISTS audio_results (id INTEGER PRIMARY KEY AUTOINCREMENT, audio_filename TEXT, class_name TEXT, class_id INTEGER, confidence REAL, distance REAL, risk_level TEXT, timestamp TEXT)')
    conn.close()

def save_result_to_db(filename, result):
    db_path = os.path.join(os.path.dirname(__file__), "audio_results.db")
    conn = sqlite3.connect(db_path)
    # 风险保存为二分类：safe/danger（若结果含 risk_level，使用之，否则按照置信度判断）
    rl = result.get("risk_level")
    if rl in ("safe", "danger"):
        risk = rl
    else:
        # 兜底：以置信度判断（>0.6 safe 否则 danger）
        risk = "safe" if result.get("confidence", 0) > 0.6 else "danger"
    conn.execute('INSERT INTO audio_results (audio_filename, class_name, class_id, confidence, distance, risk_level, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)',
                 (filename, result.get("class_name"), result.get("class_id"), result.get("confidence"), 0.0, risk, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# --- Flask 接口部分保持不变 ---
@app.route("/api/latest_result", methods=["GET"])
def api_latest_result():
    db_path = os.path.join(os.path.dirname(__file__), "audio_results.db")
    conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row
    row = conn.execute('SELECT * FROM audio_results ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()
    return jsonify(dict(row) if row else {"status": "no_data"})

@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    # 声明全局变量，确保使用的是加载好的 CNN 模型
    global global_model, global_classifier, global_labels

    # 1. 字段检查：必须与前端 FormData.append('audio', ...) 一致
    if "audio" not in request.files:
        return jsonify({"status": "error", "message": "没有找到音频文件(需使用'audio'字段)"}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"status": "error", "message": "文件名为空"}), 400

    # 2. 路径准备
    file_uuid = str(uuid.uuid4())
    raw_path = os.path.join(UPLOAD_FOLDER, f"{file_uuid}.webm")  # 临时原始文件
    wav_path = os.path.join(UPLOAD_FOLDER, f"{file_uuid}.wav")   # 转换后的目标文件

    try:
        # 3. 保存原始 WebM 文件
        audio_file.save(raw_path)
        
        # 4. 调用 FFmpeg 转换为标准 WAV (16000Hz, 单声道, pcm_s16le)
        import subprocess
        try:
            cmd = [
                "ffmpeg", "-i", raw_path,
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                "-y", wav_path
            ]
            # quiet 模式避免干扰 Flask 输出
            subprocess.run(cmd, check=True, capture_output=True)
        except Exception as fe:
            print(f"音频转换失败: {str(fe)}")
            return jsonify({"status": "error", "message": "FFmpeg 转换失败，请检查环境"}), 500

        # 5. 调用新集成的 CNN 分析函数
        # 注意：这里传 global_model 和 global_classifier
        result = analyze_audio(
            global_model, 
            global_classifier, 
            None, 
            global_labels, 
            wav_path, 
            {}
        )

        # 6. 如果分析返回错误，向调用方返回 500 并打印错误信息
        if not isinstance(result, dict) or result.get("status") != "success":
            print(f"Web端分析失败: {result.get('message')}")
            return jsonify(result), 500

        # 7. 保存结果到数据库
        save_result_to_db(file_uuid, result)
        
        # 打印结果供调试（确保 confidence 不为 None）
        conf = result.get('confidence')
        try:
            conf_display = f"{conf:.2%}" if conf is not None else "--"
        except Exception:
            conf_display = str(conf)
        print(f"Web端分析成功: {result.get('class_name')} ({conf_display})")

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"服务器处理异常: {str(e)}"}), 500
    
    finally:
        # 7. 最终清理所有临时文件
        for p in [raw_path, wav_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

def main_api():
    init_db()
    global global_model, global_classifier, global_labels
    # 修改为 CNN14 的加载返回
    global_model, global_classifier, _, global_labels = load_model({"use_gpu": True})
    
    threading.Thread(target=realtime_worker, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    main_api()