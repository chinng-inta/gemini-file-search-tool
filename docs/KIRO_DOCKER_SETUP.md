# Kiro から Docker 環境の MCP サーバーを呼び出す設定ガイド

このドキュメントでは、Kiro から Docker コンテナ内で実行されている Gemini RAG MCP サーバーを呼び出すための設定方法を説明します。

## 前提条件

1. Docker Desktop がインストールされ、起動していること
2. VSCode で Dev Container が起動していること
3. 環境変数 `GEMINI_FILE_SEARCH_API_KEY` と `GEMINI_CODE_GEN_API_KEY` が設定されていること

## セットアップ手順

### 1. コンテナ名の確認

Dev Container が起動している状態で、以下のスクリプトを実行してコンテナ名を確認します：

**PowerShell の場合:**
```powershell
powershell -ExecutionPolicy Bypass -File scripts/get_container_name.ps1
```

**Bash/WSL の場合:**
```bash
bash scripts/get_container_name.sh
```

スクリプトが自動的に MCP 設定を生成してくれます。

### 2. MCP 設定ファイルの作成/更新

`.kiro/settings/mcp.json` ファイルを作成または更新します：

```json
{
  "mcpServers": {
    "gemini-rag-mcp": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "-e",
        "GEMINI_FILE_SEARCH_API_KEY=${localEnv:GEMINI_FILE_SEARCH_API_KEY}",
        "-e",
        "GEMINI_CODE_GEN_API_KEY=${localEnv:GEMINI_CODE_GEN_API_KEY}",
        "-e",
        "RAG_CONFIG_PATH=/workspace/config/rag_config.json",
        "-e",
        "DOCS_STORE_PATH=/workspace/data/docs",
        "-e",
        "URL_CONFIG_PATH=/workspace/config/url_config.json",
        "-e",
        "RAG_MAX_AGE_DAYS=90",
        "YOUR_CONTAINER_NAME",
        "python",
        "/workspace/mcp_server.py"
      ],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

`YOUR_CONTAINER_NAME` の部分を、ステップ1で確認したコンテナ名に置き換えてください。

### 3. 環境変数の設定

Kiro が環境変数を読み込めるように、以下のいずれかの方法で設定します：

**方法1: システム環境変数として設定（推奨）**

Windows の場合：
1. 「システムのプロパティ」→「環境変数」を開く
2. ユーザー環境変数に以下を追加：
   - `GEMINI_FILE_SEARCH_API_KEY`: あなたの File Search API キー
   - `GEMINI_CODE_GEN_API_KEY`: あなたの Code Generation API キー

**方法2: .env ファイルを使用**

プロジェクトルートの `.env` ファイルに以下を記述：
```bash
GEMINI_FILE_SEARCH_API_KEY=your_file_search_api_key_here
GEMINI_CODE_GEN_API_KEY=your_code_gen_api_key_here
```

### 4. Kiro の再起動

MCP 設定を反映させるため、Kiro を再起動します。

### 5. 動作確認

Kiro のチャットで以下のように試してみてください：

```
登録されているAPIドキュメントの一覧を表示してください
```

または

```
Arduino Docs をクロールしてください
```

## トラブルシューティング

### エラー: "Cannot connect to the Docker daemon"

**原因:** Docker Desktop が起動していない、または Docker デーモンにアクセスできない

**解決策:**
1. Docker Desktop を起動する
2. WSL を使用している場合、Docker Desktop の設定で「WSL 2 based engine」が有効になっているか確認

### エラー: "Container not found"

**原因:** コンテナ名が間違っている、または Dev Container が起動していない

**解決策:**
1. VSCode で Dev Container が起動しているか確認
2. `docker ps` コマンドでコンテナ名を再確認
3. `.kiro/settings/mcp.json` のコンテナ名を更新

### エラー: "GEMINI_API_KEY not found"

**原因:** 環境変数が正しく設定されていない

**解決策:**
1. システム環境変数が正しく設定されているか確認
2. Kiro を再起動して環境変数を再読み込み
3. `.env` ファイルが正しい場所にあるか確認

### MCP サーバーが応答しない

**原因:** MCP サーバーが正常に起動していない

**解決策:**
1. Dev Container 内で手動実行してエラーを確認：
   ```bash
   docker exec -it YOUR_CONTAINER_NAME python /workspace/mcp_server.py
   ```
2. ログを確認して問題を特定

## コンテナ名が変わった場合

Dev Container を再作成すると、コンテナ名が変わることがあります。その場合は：

1. 再度 `scripts/get_container_name.sh` または `scripts/get_container_name.ps1` を実行
2. 新しいコンテナ名で `.kiro/settings/mcp.json` を更新
3. Kiro を再起動

## 参考情報

- [Kiro MCP ドキュメント](https://kiro.dev/docs/mcp/)
- [Docker CLI リファレンス](https://docs.docker.com/engine/reference/commandline/cli/)
- [Gemini API ドキュメント](https://ai.google.dev/gemini-api/docs)
