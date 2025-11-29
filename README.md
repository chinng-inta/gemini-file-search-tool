# Gemini RAG MCP Server

APIドキュメントを自動的にクロール・学習し、Gemini AIのFile Search toolを使ってコード生成を支援するMCPサーバーシステムです。Claude DesktopやKiroなどのMCPクライアントから利用でき、最新のAPI仕様に基づいた正確なコード生成を可能にします。

## 主な機能

- **APIドキュメントクローラー**: キーワードまたはURLを指定してAPIドキュメントサイトを再帰的にクロール
- **動的ページ対応**: Cloudflare Browser Renderingを使用したJavaScript実行が必要なSPAページのクロール
- **ファイル直接アップロード**: ローカルファイル（.txt、.md、.pdf、画像）を直接RAGにアップロード
- **Gemini RAG統合**: Gemini File Search APIを使用したドキュメント学習とコード生成
- **MCPプロトコル対応**: Claude DesktopやKiroなどのMCPクライアントから利用可能
- **自動更新**: GitHub Actionsによる週次自動クロール
- **複数RAG管理**: ドキュメント種類ごとに複数のRAGバージョンを管理

## セットアップ手順

### 1. リポジトリの取得

**方法A: GitHub Templateから作成（推奨）**

1. GitHubで「Use this template」ボタンをクリック
2. 新しいリポジトリ名を入力して作成
3. 作成したリポジトリをクローン

```bash
git clone <your-repository-url>
cd gemini-rag-mcp
```

**方法B: Forkして使用**

1. GitHubで「Fork」ボタンをクリック
2. フォークしたリポジトリをクローン

```bash
git clone <your-forked-repository-url>
cd gemini-rag-mcp
```

### 2. 環境変数の設定

`.env.template`をコピーして`.env`ファイルを作成：

```bash
cp .env.template .env
```

**URL設定（オプション）**

独自のAPIドキュメントを追加する場合は、`config/url_config.json`を編集してください。

> **⚠️ 重要な注意事項**
> - `data/docs/`と`config/url_config.json`はリポジトリに含まれます
> - **公開リポジトリの場合**：公開されても問題ないAPIドキュメントのみをクロールしてください
> - **機密情報を含むドキュメント**：プライベートリポジトリとして使用するか、クロールしないでください

`.env`ファイルを編集して、APIキーとパスを設定：

```bash
# Gemini API Key
# Get your API key from: https://ai.google.dev/
GEMINI_FILE_SEARCH_API_KEY=your_file_search_api_key_here
GEMINI_CODE_GEN_API_KEY=your_code_gen_api_key_here

# Cloudflare Browser Rendering (Optional - for dynamic page crawling)
# Get your credentials from: https://dash.cloudflare.com/
CLOUDFLARE_API_TOKEN=your_cloudflare_api_token_here
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here

# Paths (default values for Dev Container)
RAG_CONFIG_PATH=/workspace/config/rag_config.json
DOCS_STORE_PATH=/workspace/data/docs
URL_CONFIG_PATH=/workspace/config/url_config.json

# RAG Cleanup (days)
RAG_MAX_AGE_DAYS=90
```

**Cloudflare Browser Rendering（オプション）:**

動的にレンダリングされるSPAページ（React、Vue、Angularなど）をクロールする場合は、Cloudflare Browser Rendering APIの認証情報を設定してください。設定しない場合は、従来のBeautifulSoupベースのクロールが使用されます。

- `CLOUDFLARE_API_TOKEN`: Cloudflare APIトークン
- `CLOUDFLARE_ACCOUNT_ID`: CloudflareアカウントID

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
        "CLOUDFLARE_API_TOKEN": "your_cloudflare_api_token_here",
        "CLOUDFLARE_ACCOUNT_ID": "your_cloudflare_account_id_here",
        "RAG_CONFIG_PATH": "/workspace/config/rag_config.json",
        "DOCS_STORE_PATH": "/workspace/data/docs",
        "URL_CONFIG_PATH": "/workspace/config/url_config.json",
        "RAG_MAX_AGE_DAYS": "90"
      }
    }
  }
}
```

**注意:** `CLOUDFLARE_API_TOKEN`と`CLOUDFLARE_ACCOUNT_ID`はオプションです。設定しない場合は、従来のBeautifulSoupベースのクロールが使用されます。

#### Kiro

##### ローカル環境での実行

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
        "CLOUDFLARE_API_TOKEN": "${localEnv:CLOUDFLARE_API_TOKEN}",
        "CLOUDFLARE_ACCOUNT_ID": "${localEnv:CLOUDFLARE_ACCOUNT_ID}",
        "RAG_CONFIG_PATH": "C:/path/to/your/project/config/rag_config.json",
        "DOCS_STORE_PATH": "C:/path/to/your/project/data/docs",
        "URL_CONFIG_PATH": "C:/path/to/your/project/config/url_config.json",
        "RAG_MAX_AGE_DAYS": "90"
      }
    }
  }
}
```

**注意:** `CLOUDFLARE_API_TOKEN`と`CLOUDFLARE_ACCOUNT_ID`はオプションです。設定しない場合は、従来のBeautifulSoupベースのクロールが使用されます。

##### Docker環境での実行（推奨）

Dev Containerを起動した状態で、`.kiro/settings/mcp.json`に以下を追加：

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
        "CLOUDFLARE_API_TOKEN=${localEnv:CLOUDFLARE_API_TOKEN}",
        "-e",
        "CLOUDFLARE_ACCOUNT_ID=${localEnv:CLOUDFLARE_ACCOUNT_ID}",
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

**コンテナ名の確認と設定の自動生成:**

便利なヘルパースクリプトを用意しています：

```bash
# Bash/WSLの場合
bash scripts/get_container_name.sh

# PowerShellの場合
powershell -ExecutionPolicy Bypass -File scripts/get_container_name.ps1
```

または手動で確認：

```bash
# Windowsの場合
docker ps --format "{{.Names}}"

# WSLの場合
docker.exe ps --format "{{.Names}}"
```

コンテナ名は通常`gemini-fie-search-tool-devcontainer-1`のような形式になります。上記コマンドで確認した名前を`YOUR_CONTAINER_NAME`の部分に置き換えてください。

**注意事項:**
- Dev Containerが起動している必要があります
- 環境変数`GEMINI_FILE_SEARCH_API_KEY`と`GEMINI_CODE_GEN_API_KEY`をローカル環境（`.env`ファイルまたはシステム環境変数）に設定してください
- `CLOUDFLARE_API_TOKEN`と`CLOUDFLARE_ACCOUNT_ID`はオプションです。動的ページのクロールが必要な場合のみ設定してください

### 利用可能なMCPツール

#### 1. crawl_api_docs

APIドキュメントをクロールします。動的ページ（SPA）の場合、Cloudflare Browser Renderingが自動的に使用されます。

```
キーワードまたはURLを指定してAPIドキュメントをクロールしてください。
例: "Arduino Docs"または"https://docs.arduino.cc/"
```

**動的ページの自動検出:**
- JavaScriptフレームワーク（React、Vue、Angular、Next.js、Nuxtなど）を検出
- テキストコンテンツが少ないページを動的として判定
- Cloudflare Browser Renderingでレンダリング後、Markdown形式で保存

#### 2. upload_file_directly

ローカルファイルを直接RAGにアップロードします。

```
"/path/to/document.pdf"をRAGにアップロードしてください。
```

**パラメータ:**
- `file_path` (必須): アップロードするファイルのパス
- `doc_type` (オプション): ドキュメントの種類（省略時はファイル名から推測）
- `description` (オプション): RAGの説明

**サポートされているファイル形式:**
- テキスト: `.txt`, `.md`
- ドキュメント: `.pdf`
- 画像: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`
- 最大ファイルサイズ: 50MB

**使用例:**

```
# 単一ファイルのアップロード
"/workspace/data/manual.pdf"をRAGにアップロードしてください。

# doc_typeを指定してアップロード
"/workspace/data/api_spec.md"を"API Documentation"としてアップロードしてください。

# 複数ファイルのアップロード
以下のファイルをRAGにアップロードしてください：
- /workspace/data/guide1.pdf
- /workspace/data/guide2.md
- /workspace/data/diagram.png
```

#### 3. list_api_docs

登録されているAPIドキュメントの一覧を表示します。

```
登録されているAPIドキュメントの一覧を表示してください。
```

#### 4. upload_documents

クロールしたドキュメントをGemini RAGにアップロードします。

```
"Arduino Docs"のドキュメントをアップロードしてください。
```

#### 5. generate_code

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

## 新機能の詳細

### Cloudflare Browser Rendering統合

JavaScriptで動的にレンダリングされるSPA（Single Page Application）ページをクロールできます。

**対応フレームワーク:**
- React
- Vue.js
- Angular
- Next.js
- Nuxt.js
- その他のJavaScriptフレームワーク

**動作の仕組み:**

1. **自動検出**: クローラーがページを取得し、JavaScriptフレームワークの存在とテキストコンテンツの量を分析
2. **動的判定**: フレームワークが検出され、テキストコンテンツが少ない場合、動的ページと判定
3. **Cloudflareレンダリング**: Cloudflare Browser Rendering APIでページをレンダリング
4. **Markdown変換**: レンダリングされたHTMLをMarkdown形式に変換して保存
5. **フォールバック**: Cloudflare APIがエラーを返した場合、自動的にBeautifulSoupにフォールバック

**レート制限とリトライ:**
- レート制限エラー時は指数バックオフで最大3回再試行
- タイムアウトは30秒
- 既存のクロール遅延（1秒）を尊重

### ファイル直接アップロード

ローカルファイルシステム上のファイルを直接RAGにアップロードできます。

**サポートされているファイル形式:**
- テキスト: `.txt`, `.md`
- ドキュメント: `.pdf`
- 画像: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`

**制限事項:**
- 最大ファイルサイズ: 50MB
- ファイルは存在する必要があります
- サポートされていない拡張子は拒否されます

**メタデータ:**
- アップロードタイムスタンプ（JST形式）
- 元のファイルパス
- ファイルサイズ
- ファイル拡張子
- doc_type（自動推測または手動指定）

**複数ファイルのアップロード:**
- 複数のファイルを同じRAGストアにアップロード可能
- 1つのファイルが失敗しても、残りのファイルは処理継続
- アップロード完了後、RAG設定ファイルが自動更新

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

### Cloudflare Browser Rendering関連

#### Cloudflare認証エラー

```
Cloudflare authentication failed, falling back to BeautifulSoup
```

→ `CLOUDFLARE_API_TOKEN`と`CLOUDFLARE_ACCOUNT_ID`が正しく設定されているか確認してください。

#### Cloudflareタイムアウト

```
Cloudflare API timeout, falling back to BeautifulSoup
```

→ ネットワーク接続を確認してください。タイムアウト後は自動的にBeautifulSoupにフォールバックします。

#### Cloudflareレート制限

```
Cloudflare rate limit exceeded, retrying with backoff...
```

→ システムは自動的に指数バックオフで再試行します。最大3回の再試行後、BeautifulSoupにフォールバックします。

### ファイル直接アップロード関連

#### ファイルが見つからない

```
File not found: /path/to/file.pdf
```

→ ファイルパスが正しいか、ファイルが存在するか確認してください。

#### サポートされていない拡張子

```
Unsupported file extension: .docx
```

→ サポートされている拡張子（.txt、.md、.pdf、.png、.jpg、.jpeg、.gif、.webp）を使用してください。

#### ファイルサイズ超過

```
File too large: 75.5MB. Maximum: 50MB
```

→ ファイルサイズを50MB以下に削減してください。

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