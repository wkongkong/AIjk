@echo off
chcp 65001 >nul
echo ============================================================
echo   API 文档解析服务 - 启动脚本
echo ============================================================
echo.

echo [1/4] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo ❌ Python 未安装或未配置到 PATH
    echo 请先安装 Python 3.7 或更高版本
    pause
    exit /b 1
)
echo ✅ Python 环境正常
echo.

echo [2/4] 检查并安装依赖包...
echo 正在检查必要的依赖包...

REM 检查并安装 Flask
pip show Flask >nul 2>&1
if errorlevel 1 (
    echo 正在安装 Flask...
    pip install Flask
)

REM 检查并安装其他必要依赖
pip show flask-cors >nul 2>&1
if errorlevel 1 (
    echo 正在安装 flask-cors...
    pip install flask-cors
)

pip show requests >nul 2>&1
if errorlevel 1 (
    echo 正在安装 requests...
    pip install requests
)

pip show PyYAML >nul 2>&1
if errorlevel 1 (
    echo 正在安装 PyYAML...
    pip install PyYAML
)

pip show python-dotenv >nul 2>&1
if errorlevel 1 (
    echo 正在安装 python-dotenv...
    pip install python-dotenv
)

echo ✅ 依赖包检查完成
echo.

echo [3/4] 检查配置文件...
if not exist ".env" (
    echo ⚠️  警告: 未找到 .env 配置文件
    echo 请确保已正确配置 Dify API 密钥等必要参数
    echo.
) else (
    echo ✅ 找到 .env 配置文件
)

REM 检查必要的目录
if not exist "data" mkdir data
if not exist "temp" mkdir temp
if not exist "svn_workspace" mkdir svn_workspace
if not exist "svn_workspace_debug" mkdir svn_workspace_debug

echo ✅ 目录结构检查完成
echo.

echo [4/4] 启动服务...
echo.
echo ============================================================
echo   服务地址: http://localhost:5000
echo   健康检查: http://localhost:5000/api/health
echo   按 Ctrl+C 停止服务
echo ============================================================
echo.

python run.py
