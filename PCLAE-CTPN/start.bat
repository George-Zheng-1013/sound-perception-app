@echo off
@chcp 65001 > nul
echo 启动PCLAE-CTPN项目...

REM 激活conda环境
echo 激活conda环境...
call conda activate dachuang
if %errorlevel% neq 0 (
    echo 警告: conda环境激活失败，继续使用系统Python环境
)

REM 检查Python环境
python --version
if %errorlevel% neq 0 (
    echo Python未安装或未添加到PATH
    pause
    exit /b 1
)

REM 创建必要的目录
if not exist "log" (
    echo 创建目录: %cd%\log
    mkdir log
)
if not exist "log\models\ESC48_CTPN" (
    echo 创建目录: %cd%\log\models\ESC48_CTPN
    mkdir "log\models\ESC48_CTPN"
)
if not exist "results" (
    echo 创建目录: %cd%\results
    mkdir results
)
if not exist "temp_audio" (
    echo 创建目录: %cd%\temp_audio
    mkdir temp_audio
)

REM 安装依赖（如果需要）
if exist requirements.txt (
    echo 安装Python依赖...
    pip install -r requirements.txt
)

REM 运行setup脚本
python setup.py

REM 启动测试服务器
echo 启动音频分析服务器...
python testaudio.py --api --port 5000