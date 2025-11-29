# セットアップガイド

このリポジトリをGitHub Templateから作成した場合の初期セットアップ手順です。

## 1. 設定ファイルの作成

### 環境変数ファイル（必須）

```bash
cp .env.template .env
```

`.env`ファイルを編集して、以下のAPIキーを設定してください：

- `GEMINI_FILE_SEARCH_API_KEY`: [Google AI Studio](https://ai.google.dev/)で取得
- `GEMINI_CODE_GEN_API_KEY`: [Google AI Studio](https://ai.google.dev/)で取得
- `CLOUDFLARE_API_TOKEN`: （オプション）[Cloudflare Dashboard](https://dash.cloudflare.com/)で取得
- `CLOUDFLARE_ACCOUNT_ID`: （オプション）[Cloudflare Dashboard](https://dash.cloudflare.com/)で取得

### URL設定ファイル（オプション）

独自のAPIドキュメントを追加する場合は、`config/url_config.json`を編集してください。

例：
```json
{
  "apis": {
    "my_api": {
      "name": "My API Documentation",
      "url": "https://docs.example.com/api/",
      "description": "My API documentation"
    }
  }
}
```

> **⚠️ 重要な注意事項**
> - `data/docs/`と`config/url_config.json`はリポジトリに含まれます
> - **公開リポジトリの場合**：公開されても問題ないAPIドキュメントのみをクロールしてください
> - **機密情報を含むドキュメント**：プライベートリポジトリとして使用するか、クロールしないでください

## 2. Dev Containerの起動

VS CodeまたはKiroでリポジトリを開き、Dev Containerで再起動してください。

## 3. MCPサーバーの設定

詳細は[KIRO_DOCKER_SETUP.md](docs/KIRO_DOCKER_SETUP.md)を参照してください。

## 4. 使用開始

設定が完了したら、MCPクライアント（Claude DesktopやKiro）から以下のツールを使用できます：

- `crawl_api_docs`: APIドキュメントをクロール
- `upload_documents`: クロールしたドキュメントをRAGにアップロード
- `query_api_docs`: RAGを使用してコード生成や質問応答
- `upload_file_directly`: ローカルファイルを直接RAGにアップロード

## 注意事項

### Gitignoreの設定

以下のファイル・ディレクトリは自動的に除外されます：

- `.env`: APIキーを含む環境変数ファイル
- `config/rag_config.json`: RAG設定（自動生成）
- `.kiro/`: Kiro設定フォルダ

**リポジトリに含まれるファイル：**
- `data/docs/`: クロールされたドキュメント（GitHub Actionsの結果を含む）
- `config/url_config.json`: クロール対象のURL設定

### データのバックアップ

重要なクロールデータやRAG設定は、別途バックアップを取ることをお勧めします：

```bash
# バックアップ例
tar -czf backup-$(date +%Y%m%d).tar.gz data/docs config/rag_config.json config/url_config.json
```

## トラブルシューティング

問題が発生した場合は、[README.md](README.md)のトラブルシューティングセクションを参照してください。
