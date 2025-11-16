# Gemini RAG MCP Server

Gemini File Search APIを使用したRAG（Retrieval-Augmented Generation）システムのMCPサーバー実装です。

## 環境変数の設定

このプロジェクトでは、2つの異なるGemini APIキーを使用します：

1. **GEMINI_FILE_SEARCH_API_KEY**: ドキュメントのアップロードとRAGストアの作成に使用
2. **GEMINI_CODE_GEN_API_KEY**: RAGを使用したコード生成に使用

### セットアップ手順

1. `.env.template`をコピーして`.env`ファイルを作成：
```bash
cp .env.template .env
```

2. `.env`ファイルを編集して、APIキーを設定：
```bash
# Gemini File Search API Key (for uploading documents and creating RAG stores)
GEMINI_FILE_SEARCH_API_KEY=your_file_search_api_key_here

# Gemini Code Generation API Key (for generating code with RAG)
GEMINI_CODE_GEN_API_KEY=your_code_gen_api_key_here
```

3. APIキーは[Google AI Studio](https://ai.google.dev/)から取得できます

## テストの実行

```bash
python -m pytest tests/test_rag_manager.py -v
```

## 使用方法

```python
from src.rag_manager import GeminiRAGManager

# RAGマネージャーを初期化
manager = GeminiRAGManager("config/rag_config.json")

# ドキュメントをアップロード
rag_id = await manager.upload_documents(
    doc_type="gemini",
    file_paths=["docs/api_doc1.txt", "docs/api_doc2.txt"],
    description="Gemini API Documentation"
)

# コードを生成
code = await manager.generate_code(
    prompt="Create a function to call Gemini API",
    doc_type="gemini"
)
print(code)
```