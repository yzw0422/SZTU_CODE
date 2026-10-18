﻿$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host ""
Write-Host "  SZTU_Code  v0.2.0  -  一键配置" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# ---------- 1. 检查 Python ----------
Write-Host "[1/4] 检查 Python..." -NoNewline
$pyOk = $false
try {
    $pyLine = python --version 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0) { $pyOk = $true; Write-Host " OK ($pyLine.Trim())" -ForegroundColor Green }
} catch {}
if (-not $pyOk) {
    Write-Host " 错误: 未找到 Python 3.10+" -ForegroundColor Red
    Write-Host " 下载: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# ---------- 2. pip install ----------
Write-Host "[2/4] 安装依赖 (pip install -e .)..." -NoNewline
Push-Location $ProjectRoot
pip install -e . --quiet 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host " 错误: pip install 失败" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location
Write-Host " OK" -ForegroundColor Green

# ---------- 3. 配置文件 ----------
Write-Host "[3/4] 检查配置文件..." -NoNewline
$ConfigPath = Join-Path $ProjectRoot ".sztu_code"
$HomeConfig = Join-Path $env:USERPROFILE ".sztu_code"

if ((Test-Path $ConfigPath) -or (Test-Path $HomeConfig)) {
    Write-Host " OK (已存在)" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host ""
    Write-Host " 未找到 .sztu_code 配置文件" -ForegroundColor Yellow
    Write-Host ""
    Write-Host " 请选择 API Provider:"
    Write-Host "   1. DeepSeek (deepseek-v4-flash)"
    Write-Host "   2. OpenAI (gpt-4o-mini)"
    Write-Host "   3. 手动输入"
    Write-Host ""
    $choice = Read-Host " 请输入选项 (1/2/3)"
    Write-Host ""

    if ($choice -eq "1") {
        $apiKey = Read-Host " 请输入 DeepSeek API Key"
        $model = "deepseek-v4-flash"
        $type = "deepseek"
        $baseUrl = "https://api.deepseek.com/v1"
    } elseif ($choice -eq "2") {
        $apiKey = Read-Host " 请输入 OpenAI API Key"
        $model = "gpt-4o-mini"
        $type = "openai"
        $baseUrl = "https://api.openai.com/v1"
    } else {
        $type = Read-Host " Provider 类型 (deepseek/openai)"
        $model = Read-Host " 模型名"
        $apiKey = Read-Host " API Key"
        $baseUrl = Read-Host " API Base URL"
    }

    $lines = @(
        "[provider]"
        "type = `"$type`""
        "api_key = `"$apiKey`""
        "model = `"$model`""
        "base_url = `"$baseUrl`""
        ""
        "[agent]"
        "max_turns = 25"
        "max_tokens = 4096"
    )
    [System.IO.File]::WriteAllLines($ConfigPath, $lines, [System.Text.Encoding]::UTF8)
    Write-Host " 已创建: $ConfigPath" -ForegroundColor Green
}

# ---------- 4. 验证 ----------
Write-Host "[4/4] 验证 sztu-code..." -NoNewline
$sztuCmd = Get-Command sztu-code -ErrorAction SilentlyContinue
if ($sztuCmd) {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host " 错误: 未找到 sztu-code" -ForegroundColor Red
    Write-Host " 请重新打开终端后再运行" -ForegroundColor Yellow
    exit 1
}

# ---------- 完成 ----------
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  配置完成! 运行:" -ForegroundColor Cyan
Write-Host ""
Write-Host "    sztu-code" -ForegroundColor Yellow
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""