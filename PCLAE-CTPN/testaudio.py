import csv
import os
import sys
import argparse
import datetime
import time
import numpy as np
import pandas as pd
import importlib
import torch
import torch.nn as nn
from torch.optim import lr_scheduler
import torch.backends.cudnn as cudnn
import config
from models.htsat import HTSAT_Swin_Transformer
from msclap import CLAP
from utils import Logger, save_networks, load_networks
from core import train, test

# flask相关库
from flask import Flask, request, jsonify
from flask_cors import CORS
import soundfile as sf
import uuid

app = Flask(__name__)
CORS(app)  # 启用跨域

dataset_dir = "DATASET"

dataset_config = {
    "meta_csv": os.path.join(dataset_dir, "meta2.csv"),
    "audio_path": os.path.join(dataset_dir, "audio"),
}

# 创建临时文件夹存储录音
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "temp_audio")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

parser = argparse.ArgumentParser("Training")

# Dataset
parser.add_argument(
    "--dataset", type=str, default="ESC_48", help="ESC_48 | UrbanSound8K"
)
parser.add_argument("--audio_dir", type=str, default=dataset_config["audio_path"])
parser.add_argument("--meta_dir", type=str, default=dataset_config["meta_csv"])
parser.add_argument("--fold", type=int, default=1)
# 使用相对路径替代硬编码路径
project_root = os.path.dirname(os.path.abspath(__file__))
dataset_dir = os.path.join(project_root, "DATASET")

dataset_config = {
    "meta_csv": os.path.join(dataset_dir, "meta2.csv"),
    "audio_path": os.path.join(dataset_dir, "audio"),
}

parser.add_argument("--out-num", type=int, default=50, help="For CIFAR100")
parser.add_argument("--num", type=int, default=1)
parser.add_argument("--class", type=str, default="ESC48_CTPN")

# optimization
parser.add_argument("--batch-size", type=int, default=64)
parser.add_argument("--lr", type=float, default=0.01, help="learning rate for model")
parser.add_argument("--max-epoch", type=int, default=100)
parser.add_argument("--stepsize", type=int, default=30)
parser.add_argument("--temp", type=float, default=1, help="temp")
parser.add_argument("--num_centers", type=int, default=1)
parser.add_argument("--item", type=int, default=0)

# model
parser.add_argument(
    "--weight-pl", type=float, default=0.1, help="weight for center loss"
)
parser.add_argument("--beta", type=float, default=0.1, help="weight for entropy loss")
parser.add_argument("--model", type=str, default="classifier32")

# misc
parser.add_argument("--nz", type=int, default=100)
parser.add_argument("--ns", type=int, default=1)
parser.add_argument("--eval-freq", type=int, default=1)
parser.add_argument("--print-freq", type=int, default=5)
parser.add_argument("--seed", type=int, default=0)
parser.add_argument("--use-gpu", action="store_true", default=True)
parser.add_argument("--gpu", type=str, default="0")
# 添加缺失的参数
parser.add_argument("--loss", type=str, default="ARPLoss")
parser.add_argument("--cs", action="store_true", help="Confusing Sample", default=False)
parser.add_argument("--port", type=int, default=5000, help="Flask server port")
# 修改第101行附近参数定义
parser.add_argument(
    "--save-dir", dest="outf", type=str, default=os.path.join(project_root, "log")
)

# 修改第141行附近路径构造
# 修改第93行附近的代码，删除这一行：
# model_path = os.path.join(args.outf, "models", args.class_name)  # 替换原options参数


# 在load_model函数中（第91行之后），修改model_path的构建方式：
def load_model(options):
    torch.manual_seed(options["seed"])
    os.environ["CUDA_VISIBLE_DEVICES"] = options["gpu"]

    if options["use_gpu"]:
        print("Currently using GPU: {}".format(options["gpu"]))
        cudnn.benchmark = True
        torch.cuda.manual_seed_all(options["seed"])
    else:
        print("Currently using CPU")

    # Dataset
    # audio_path = r"D:\PCLAE-CTPN\DATASET\audio\1-7-A-20.wav"
    options["num_classes"] = 48

    net = HTSAT_Swin_Transformer(
        spec_size=config.htsat_spec_size,
        patch_size=config.htsat_patch_size,
        in_chans=1,
        num_classes=options["num_classes"],
        window_size=config.htsat_window_size,
        config=config,
        depths=config.htsat_depth,
        embed_dim=config.htsat_dim,
        patch_stride=config.htsat_stride,
        num_heads=config.htsat_num_head,
    )

    feat_dim = 128

    # Loss
    options.update({"feat_dim": feat_dim})

    Loss = importlib.import_module("loss." + options["loss"])
    criterion = getattr(Loss, options["loss"])(**options)

    if options["use_gpu"]:
        net = nn.DataParallel(net).cuda()
        criterion = criterion.cuda()

    model_path = os.path.join(options["outf"], "models", options["class"])
    if not os.path.exists(model_path):
        os.makedirs(model_path)

    with open(
        os.path.join(os.path.dirname(__file__), "category_mapping.csv"),
        "r",
        encoding="utf-8",
    ) as f:
        reader = csv.reader(f, delimiter=",")
        lines = list(reader)

    labels = []
    for i1 in range(len(lines)):
        label = lines[i1]
        labels.append(label)

    file_name = "{}_{}_{}_{}".format(
        options["model"], options["loss"], options["item"], options["cs"]
    )
    clap_model_path=os.path.join(project_root,'CLAP_weights_2023.pth')
    # Load and initialize CLAP
    clap_model = CLAP(
        version="2023", use_cuda=False, model_fp=clap_model_path
    )

    net, criterion = load_networks(net, model_path, file_name, criterion=criterion)
    net.eval()

    return net, criterion, clap_model, labels


def analyze_audio(net, criterion, clap_model, labels, audio_path, options):
    with torch.no_grad():
        try:
            print(f"处理音频: {audio_path}")

            data = clap_model.get_audio_embeddings([audio_path], resample=True)

            if options["use_gpu"]:
                data = data.cuda()

            x, y = net(data, mixup_lambda=None, infer_mode=False, return_feature=True)
            logits, _ = criterion(x, y)
            centers = criterion.center_points
            predictions = logits.data.max(1)[1]
            min_distance = logits.data.max(1)[0].item()
            prob = torch.softmax(logits, dim=1).max(1).values.item()

            result = {
                "status": "success",
                "is_known": min_distance >= 5,
                "confidence": float(prob),
                "distance": float(min_distance),
            }

            if min_distance >= 5:
                a = labels[predictions.item() + 1]
                result["class_name"] = a[0]
                result["class_id"] = int(predictions.item())
                result["category"] = a[1]
            else:
                result["class_name"] = "未知类别"
                result["class_id"] = -1

            return result
        except Exception as e:
            print(f"音频分析错误: {str(e)}")
            import traceback

            traceback.print_exc()
            return {"status": "error", "message": f"音频分析失败: {str(e)}"}


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    global global_model, global_criterion, global_clap_model, global_labels, global_options

    if "audio" not in request.files:
        return jsonify({"status": "error", "message": "没有找到音频文件"}), 400

    audio_file = request.files["audio"]

    if audio_file.filename == "":
        return jsonify({"status": "error", "message": "文件名为空"}), 400

    # 生成唯一文件名（不带扩展名）
    filename = str(uuid.uuid4())
    raw_path = os.path.join(UPLOAD_FOLDER, f"{filename}.webm")  # 保存原始文件
    wav_path = os.path.join(UPLOAD_FOLDER, f"{filename}.wav")  # 转换后的WAV文件

    try:
        # 保存原始文件
        audio_file.save(raw_path)
        print(f"已保存原始音频到: {raw_path}")
        print(f"文件大小: {os.path.getsize(raw_path)} 字节")

        # 使用pyffmpeg将音频转换为WAV格式
        try:
            import ffmpeg

            print(f"执行ffmpeg转换: {raw_path} -> {wav_path}")

            # 使用ffmpeg-python的正确API
            (
                ffmpeg.input(raw_path)
                .output(wav_path, acodec="pcm_s16le", ar=16000, ac=1)
                .overwrite_output()  # 等同于 -y 参数
                .run(quiet=True)  # 安静模式，减少输出
            )

            # 检查转换结果
            if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
                print("ffmpeg转换失败：输出文件不存在或为空")
                return jsonify({"status": "error", "message": "音频格式转换失败"}), 400

            print(f"ffmpeg转换成功，输出文件: {wav_path}")
            print(f"WAV文件大小: {os.path.getsize(wav_path)} 字节")

        except ImportError:
            print("ffmpeg-python未安装，尝试使用系统ffmpeg")
            # 如果ffmpeg-python未安装，尝试使用subprocess调用系统ffmpeg
            try:
                import subprocess

                cmd = [
                    "ffmpeg",
                    "-i",
                    raw_path,
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-y",
                    wav_path,
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                print(f"使用系统ffmpeg转换成功: {wav_path}")
            except subprocess.CalledProcessError as se:
                print(f"系统ffmpeg也失败: {str(se)}")
                return (
                    jsonify({"status": "error", "message": f"音频转换失败: {str(se)}"}),
                    500,
                )
            except FileNotFoundError:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "未找到ffmpeg，请确保已安装ffmpeg",
                        }
                    ),
                    500,
                )

        except Exception as e:
            print(f"ffmpeg执行异常: {str(e)}")
            # 如果ffmpeg-python失败，尝试使用subprocess调用系统ffmpeg
            try:
                import subprocess

                cmd = [
                    "ffmpeg",
                    "-i",
                    raw_path,
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-y",
                    wav_path,
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                print(f"使用系统ffmpeg转换成功: {wav_path}")
            except subprocess.CalledProcessError as se:
                print(f"系统ffmpeg也失败: {str(se)}")
                return (
                    jsonify({"status": "error", "message": f"音频转换失败: {str(e)}"}),
                    500,
                )
            except FileNotFoundError:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "未找到ffmpeg，请确保已安装ffmpeg",
                        }
                    ),
                    500,
                )

        # 分析转换后的WAV文件
        result = analyze_audio(
            global_model,
            global_criterion,
            global_clap_model,
            global_labels,
            wav_path,
            global_options,
        )

        # 返回结果
        return jsonify(result)
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": f"处理错误: {str(e)}"}), 500
    finally:
        # 清理临时文件
        try:
            if os.path.exists(raw_path):
                os.remove(raw_path)
            if os.path.exists(wav_path):
                os.remove(wav_path)
        except Exception as e:
            print(f"清理临时文件失败: {str(e)}")


@app.route("/api/status", methods=["GET"])
def api_status():
    """检查API状态"""
    return jsonify({"status": "running", "message": "音频分析服务已就绪"})


def main_cli():
    """处理命令行调用的原始功能"""
    args = parser.parse_args()
    options = vars(args)

    # 使用固定测试音频路径
    audio_path = os.path.join(project_root, "DATASET", "audio", "1-7-A-20.wav")

    # 加载模型
    net, criterion, clap_model, labels = load_model(options)

    # 分析音频
    result = analyze_audio(net, criterion, clap_model, labels, audio_path, options)

    # 打印分析结果
    print("************* Acoustic Event Detected: *****************")
    if not result["is_known"]:
        print("测试音频属于未知类别。")
    else:
        print(f'测试音频属于已知类别，预测类别为：{result["class_name"]}')
    print(f'预测acc：{result["confidence"]}')
    print(f'预测distance：{result["distance"]}')
    print("********************************************************")


def main_api():
    """运行Flask API服务"""
    args = parser.parse_args()
    options = vars(args)

    # 全局模型初始化，避免每次API请求都加载模型
    global global_model, global_criterion, global_clap_model, global_labels, global_options
    global_model, global_criterion, global_clap_model, global_labels = load_model(
        options
    )
    global_options = options

    print("模型加载完成，API服务启动中...")
    # 启动Flask服务
    app.run(host="0.0.0.0", port=options["port"], debug=False)


if __name__ == "__main__":
    # 检查是否有--api参数指定运行模式
    if "--api" in sys.argv:
        # 移除自定义参数，防止argparse错误
        sys.argv.remove("--api")
        main_api()
    else:
        main_cli()
