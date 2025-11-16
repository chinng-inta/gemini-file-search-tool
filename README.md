# Gemini RAG MCP Server

APIドキュメントを自動的にクロール・学習し、Gemini AIのFile Search toolを使ってコード生成を支援するMCPサーバーシステムです。Claude DesktopやKiroなどのMCPクライアントから利用でき、最新のAPI仕様に基づいた正確なコード生成を可能にします。

## 主な機能

- **APIドキュメントクローラー**: キーワードまたはURLを指定してAPIドキュメントサイトを再帰的にクロール
- **Gemini RAG統合**: Gemini File Search APIを使用したドキュメント学習とコード生成
- **MCPプロトコル対応**: Claude DesktopやKiroなどのMCPクライアントから利用可能
- **自動更新**: GitHub Actionsによる週次自動クロール
- **複数RAG管理**: ドキュメント種類ごとに複数のRAGバージョンを管理

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd gemini-rag-mcp
```

### 2. 環境変数の設定

`.env.template`をコピーして`.env`ファイルを作成：

```bash
cp .env.template .env
```

`.env`ファイルを編集して、APIキーとパスを設定：

```bash
# Gemini API Key
# Get your API key from: https://ai.google.dev/
GEMINI_FILE_SEARCH_API_KEY=your_file_search_api_key_here
GEMINI_CODE_GEN_API_KEY=your_code_gen_api_key_here

# Paths (default values for Dev Container)
RAG_CONFIG_PATH=/workspace/config/rag_config.json
DOCS_STORE_PATH=/workspace/data/docs
URL_CONFIG_PATH=/workspace/config/url_config.json

# RAG Cleanup (days)
RAG_MAX_AGE_DAYS=90
```

### 3. Dev Containerでの起動（推奨）

VSCodeでプロジェクトを開き、Dev Containerで再起動：

```
1. VSCodeでプロジェクトフォルダを開く
2. コマンドパレット（Ctrl+Shift+P / Cmd+Shift+P）を開く
3. "Dev Containers: Reopen in Container"を選択
```

### 4. ローカル環境での起動

```bash
# 依存関係のインストール
pip install -r requirements.txt

# MCPサーバーの起動
python mcp_server.py
```

## 使用方法

### MCPクライアント設定

#### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`（macOS）または`%APPDATA%\Claude\claude_desktop_config.json`（Windows）に以下を追加：

```json
{
  "mcpServers": {
    "gemini-rag": {
      "command": "python",
      "args": ["/workspace/mcp_server.py"],
      "env": {
        "GEMINI_FILE_SEARCH_API_KEY": "your_file_search_api_key_here",
        "GEMINI_CODE_GEN_API_KEY": "your_code_gen_api_key_here",
        "RAG_CONFIG_PATH": "/workspace/config/rag_config.json",
        "DOCS_STORE_PATH": "/workspace/data/docs",
        "URL_CONFIG_PATH": "/workspace/config/url_config.json",
        "RAG_MAX_AGE_DAYS": "90"
      }
    }
  }
}
```

#### Kiro

`.kiro/settings/mcp.json`に以下を追加：

```json
{
  "mcpServers": {
    "gemini-rag": {
      "command": "python",
      "args": ["C:/path/to/your/project/mcp_server.py"],
      "env": {
        "GEMINI_FILE_SEARCH_API_KEY": "${localEnv:GEMINI_FILE_SEARCH_API_KEY}",
        "GEMINI_CODE_GEN_API_KEY": "${localEnv:GEMINI_CODE_GEN_API_KEY}",
        "RAG_CONFIG_PATH": "C:/path/to/your/project/config/rag_config.json",
        "DOCS_STORE_PATH": "C:/path/to/your/project/data/docs",
        "URL_CONFIG_PATH": "C:/path/to/your/project/config/url_config.json",
        "RAG_MAX_AGE_DAYS": "90"
      }
    }
  }
}
```

### 利用可能なMCPツール

#### 1. crawl_api_docs

APIドキュメントをクロールします。

```
キーワードまたはURLを指定してAPIドキュメントをクロールしてください。
例: "Arduino Docs"または"https://docs.arduino.cc/"
```

#### 2. list_api_docs

登録されているAPIドキュメントの一覧を表示します。

```
登録されているAPIドキュメントの一覧を表示してください。
```

#### 3. upload_documents

クロールしたドキュメントをGemini RAGにアップロードします。

```
"Arduino Docs"のドキュメントをアップロードしてください。
```

#### 4. generate_code

APIドキュメントに基づいてコードを生成します。

```
Arduino UNO R4 WiFiのLEDを点滅させるスケッチを作成してください。
```

### URL設定ファイルの編集

`config/url_config.json`でAPIドキュメントのキーワードとURLを管理できます：

```json
{
  "apis": {
    "Arduino Docs": {
      "name": "Arduino Docs",
      "url": "https://docs.arduino.cc/",
      "description": "Arduino公式ドキュメント"
    },
    "M5 Docs": {
      "name": "M5 Docs",
      "url": "https://docs.m5stack.com/ja/start",
      "description": "M5シリーズ公式ドキュメント"
    },
    "your-api": {
      "name": "Your API Name",
      "url": "https://your-api-docs.com",
      "description": "Your API description"
    }
  }
}
```

## 自動クロール設定

GitHub Actionsを使用して、週次で自動的にAPIドキュメントをクロールします。

### 設定手順

1. GitHubリポジトリのSettings > Secrets and variablesに移動
2. `GEMINI_FILE_SEARCH_API_KEY`と`GEMINI_CODE_GEN_API_KEY`をシークレットとして追加
3. `.github/workflows/crawl.yml`が自動的に毎週日曜日00:00 UTCに実行されます

手動実行も可能です：

```
1. GitHubリポジトリのActionsタブを開く
2. "Weekly API Documentation Crawl"ワークフローを選択
3. "Run workflow"ボタンをクリック
```

## プロジェクト構造

```
.
├── .devcontainer/          # Dev Container設定
├── .github/workflows/      # GitHub Actionsワークフロー
├── config/                 # 設定ファイル
│   ├── rag_config.json    # RAG ID管理
│   └── url_config.json    # URL設定
├── data/docs/             # クロールしたドキュメント
├── scripts/               # 自動化スクリプト
│   └── auto_crawl.py     # 自動クロールスクリプト
├── src/                   # ソースコード
│   ├── config.py         # 設定管理
│   ├── crawler.py        # APIクローラー
│   └── rag_manager.py    # Gemini RAGマネージャー
├── tests/                 # テストコード
├── mcp_server.py         # MCPサーバーエントリーポイント
├── requirements.txt      # Python依存関係
└── README.md            # このファイル
```

## テストの実行

```bash
# すべてのテストを実行
pytest

# カバレッジレポート付きで実行
pytest --cov=. --cov-report=html

# 特定のテストファイルのみ実行
pytest tests/test_crawler.py
```

## トラブルシューティング

### APIキーエラー

```
Error: GEMINI_API_KEY not found
```

→ `.env`ファイルが正しく設定されているか確認してください。

### クロールエラー

```
CrawlerError: Failed to fetch page
```

→ ネットワーク接続とURLが正しいか確認してください。レート制限により1秒間隔でリクエストが送信されます。

### RAGアップロードエラー

```
RAGError: Failed to upload documents
```

→ Gemini APIキーが有効か、ファイルが存在するか確認してください。最大3回まで自動リトライされます。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。

## 参考リンク

- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Claude Desktop](https://claude.ai/desktop)
- [Kiro](https://kiro.dev/)