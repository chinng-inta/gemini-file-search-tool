#!/bin/bash
# Docker コンテナ名を取得するスクリプト

echo "=== Docker コンテナ一覧 ==="
echo ""

# Windowsの場合はdocker.exeを使用
if command -v docker.exe &> /dev/null; then
    DOCKER_CMD="docker.exe"
else
    DOCKER_CMD="docker"
fi

# 実行中のコンテナを表示
$DOCKER_CMD ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

echo ""
echo "=== Kiro MCP設定用のコンテナ名 ==="
echo ""

# devcontainerを含むコンテナを検索
CONTAINER_NAME=$($DOCKER_CMD ps --filter "name=devcontainer" --format "{{.Names}}" | head -n 1)

if [ -z "$CONTAINER_NAME" ]; then
    echo "Dev Containerが見つかりませんでした。"
    echo "VSCodeでDev Containerを起動してから、このスクリプトを再実行してください。"
    exit 1
fi

echo "検出されたコンテナ名: $CONTAINER_NAME"
echo ""
echo "以下の設定を .kiro/settings/mcp.json に使用してください："
echo ""
cat << EOF
{
  "mcpServers": {
    "gemini-rag-mcp": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "-e",
        "GEMINI_FILE_SEARCH_API_KEY=\${localEnv:GEMINI_FILE_SEARCH_API_KEY}",
        "-e",
        "GEMINI_CODE_GEN_API_KEY=\${localEnv:GEMINI_CODE_GEN_API_KEY}",
        "-e",
        "RAG_CONFIG_PATH=/workspace/config/rag_config.json",
        "-e",
        "DOCS_STORE_PATH=/workspace/data/docs",
        "-e",
        "URL_CONFIG_PATH=/workspace/config/url_config.json",
        "-e",
        "RAG_MAX_AGE_DAYS=90",
        "$CONTAINER_NAME",
        "python",
        "/workspace/mcp_server.py"
      ],
      "disabled": false,
      "autoApprove": []
    }
  }
}
EOF
