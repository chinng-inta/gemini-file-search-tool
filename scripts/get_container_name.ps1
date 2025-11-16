# Docker コンテナ名を取得するスクリプト (PowerShell)

Write-Host "=== Docker コンテナ一覧 ===" -ForegroundColor Cyan
Write-Host ""

# 実行中のコンテナを表示
docker ps --format "table {{.Names}}`t{{.Image}}`t{{.Status}}"

Write-Host ""
Write-Host "=== Kiro MCP設定用のコンテナ名 ===" -ForegroundColor Cyan
Write-Host ""

# devcontainerを含むコンテナを検索
$containerName = docker ps --filter "name=devcontainer" --format "{{.Names}}" | Select-Object -First 1

if ([string]::IsNullOrEmpty($containerName)) {
    Write-Host "Dev Containerが見つかりませんでした。" -ForegroundColor Red
    Write-Host "VSCodeでDev Containerを起動してから、このスクリプトを再実行してください。"
    exit 1
}

Write-Host "検出されたコンテナ名: $containerName" -ForegroundColor Green
Write-Host ""
Write-Host "以下の設定を .kiro/settings/mcp.json に使用してください：" -ForegroundColor Yellow
Write-Host ""

$config = @"
{
  "mcpServers": {
    "gemini-rag-mcp": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "-e",
        "GEMINI_FILE_SEARCH_API_KEY=`${localEnv:GEMINI_FILE_SEARCH_API_KEY}",
        "-e",
        "GEMINI_CODE_GEN_API_KEY=`${localEnv:GEMINI_CODE_GEN_API_KEY}",
        "-e",
        "RAG_CONFIG_PATH=/workspace/config/rag_config.json",
        "-e",
        "DOCS_STORE_PATH=/workspace/data/docs",
        "-e",
        "URL_CONFIG_PATH=/workspace/config/url_config.json",
        "-e",
        "RAG_MAX_AGE_DAYS=90",
        "$containerName",
        "python",
        "/workspace/mcp_server.py"
      ],
      "disabled": false,
      "autoApprove": []
    }
  }
}
"@

Write-Host $config
Write-Host ""
Write-Host "設定をクリップボードにコピーしますか? (Y/N)" -ForegroundColor Yellow
$response = Read-Host

if ($response -eq "Y" -or $response -eq "y") {
    $config | Set-Clipboard
    Write-Host "クリップボードにコピーしました！" -ForegroundColor Green
}
