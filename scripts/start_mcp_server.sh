#!/bin/bash
# MCPサーバーを起動するスクリプト
# .envファイルから環境変数を読み込んで起動

# .envファイルが存在する場合は読み込む
if [ -f /workspace/.env ]; then
    export $(cat /workspace/.env | grep -v '^#' | xargs)
fi

# MCPサーバーを起動
exec python /workspace/mcp_server.py
