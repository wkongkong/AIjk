@echo off
chcp 65001 >nul
echo ========================================
echo   API自动化测试执行脚本
echo   混合模式 - 通用测试 + 独立测试
echo ========================================
echo.

REM 检查测试目录是否存在
if not exist "testcases" (
    echo ❌ 错误: testcases 目录不存在
    pause
    exit /b 1
)

if not exist "data_csv" (
    echo ⚠ 警告: data_csv 目录不存在
)

if not exist "data_yaml" (
    echo ⚠ 警告: data_yaml 目录不存在
)

echo ✅ 准备运行测试...
echo.

REM 检查Java环境
echo [1/4] 检查Java环境...
java -version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未检测到Java环境
    echo 请安装Java 8或更高版本以使用Allure报告
    echo 下载地址: https://www.oracle.com/java/technologies/downloads/
    echo.
    echo 提示: 可以继续运行测试，但无法生成Allure报告
    echo.
    set SKIP_ALLURE=1
) else (
    echo ✅ Java环境检查通过
    set SKIP_ALLURE=0
)
echo.

REM 清理旧的测试结果（每次重新执行）
echo [2/4] 准备测试环境...
if exist allure-results (
    echo 🗑 清理旧的测试结果...
    rmdir /s /q allure-results
    echo ✅ 已清理旧的测试结果
) else (
    echo ℹ 首次运行，创建结果目录
)
echo.

REM 运行测试
echo [3/4] 运行测试用例...
echo.
echo 📂 执行所有测试（通用测试 + 独立测试）
python -m pytest testcases/ -v --alluredir=./allure-results
echo.

if errorlevel 1 (
    echo ⚠ 测试执行完成，但有失败的用例
    echo.
) else (
    echo ✅ 测试执行完成
    echo.
)

REM 生成并打开Allure报告
if "%SKIP_ALLURE%"=="0" (
    echo [4/4] 生成Allure报告...
    if exist allure-results (
        echo 正在生成报告，请稍候...
        echo.
        allure-2.35.1\bin\allure.bat serve allure-results
    ) else (
        echo ❌ 错误: 未找到测试结果文件
        echo 请检查测试是否正常执行
        pause
        exit /b 1
    )
) else (
    echo.
    echo ⚠ 跳过Allure报告生成（Java环境未安装）
    echo.
    echo 测试结果已保存到: allure-results
    echo 安装Java后可以使用以下命令查看报告：
    echo   allure-2.35.1\bin\allure.bat serve allure-results
    echo.
)

echo.
echo ========================================
echo   测试完成！
echo ========================================
echo.
echo 📁 目录结构：
echo   - testcases/          通用测试脚本目录
echo   - testcases/dl_*.py   独立测试脚本
echo   - data_csv/           CSV格式测试用例
echo   - data_yaml/          YAML格式测试用例
echo.
echo 📝 测试模式：
echo   - 通用模式: test_*.csv / test_*.yaml （自动执行）
echo   - 独立模式: dl_*.csv / dl_*.yaml （自动执行）
echo.
echo 📚 详细说明：
echo   - 混合模式使用说明.md - 混合模式详细说明
echo   - 通用测试脚本使用指南.md - 通用模式使用指南
echo   - testcases/README.md - 测试脚本说明
echo.
echo 🔧 其他执行方式：
echo   - 通用测试: pytest testcases/test_common.py -v
echo   - 独立测试: pytest testcases/dl_test.py -v
echo   - CSV测试: pytest testcases/test_common.py --data-dir=data_csv -v
echo   - YAML测试: pytest testcases/test_common.py --data-dir=data_yaml -v
echo   - 生成独立脚本: python generate_dl_test.py data_yaml/dl_test.yaml
echo.
pause
