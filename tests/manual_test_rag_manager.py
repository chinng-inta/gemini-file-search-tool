"""RAGマネージャーの手動テスト."""
from src.rag_manager import GeminiRAGManager
from datetime import datetime

# RAGマネージャーを初期化
# 注: 環境変数GEMINI_FILE_SEARCH_API_KEYとGEMINI_CODE_GEN_API_KEYが設定されている必要があります
manager = GeminiRAGManager("config/rag_config.json")

print("=== RAGマネージャーのテスト ===\n")

# 1. RAGを追加
print("1. RAGを追加:")
rag1 = manager.add_rag(
    doc_type="gemini",
    rag_id="fileSearchStores/test123",
    description="Gemini API Documentation"
)
print(f"   追加されたRAG: {rag1}")
print(f"   作成日時（JST）: {rag1['created_at']}")
print()

# 2. 別のRAGを追加
print("2. 別のRAGを追加:")
rag2 = manager.add_rag(
    doc_type="gemini",
    rag_id="fileSearchStores/test456",
    description="Gemini Advanced Features"
)
print(f"   追加されたRAG: {rag2}")
print()

# 3. 異なるdoc_typeのRAGを追加
print("3. 異なるdoc_typeのRAGを追加:")
rag3 = manager.add_rag(
    doc_type="gas",
    rag_id="fileSearchStores/gas789"
)
print(f"   追加されたRAG: {rag3}")
print()

# 4. 特定のdoc_typeのRAGを取得
print("4. 'gemini'タイプのRAGを取得:")
gemini_rags = manager.get_rags_by_type("gemini")
for i, rag in enumerate(gemini_rags, 1):
    print(f"   {i}. {rag['rag_id']} - {rag.get('description', 'N/A')}")
print()

# 5. すべてのRAGを取得
print("5. すべてのRAGを取得:")
all_rags = manager.get_all_rags()
for doc_type, rags in all_rags.items():
    print(f"   {doc_type}: {len(rags)}個のRAG")
    for rag in rags:
        print(f"      - {rag['rag_id']}")
print()

# 6. 日時フォーマットの確認
print("6. 日時フォーマットの確認:")
print(f"   フォーマット: YYYY/MM/DD hh:mm:ss")
print(f"   例: {rag1['created_at']}")
try:
    parsed_date = datetime.strptime(rag1['created_at'], '%Y/%m/%d %H:%M:%S')
    print(f"   パース成功: {parsed_date}")
except Exception as e:
    print(f"   パース失敗: {e}")
print()

print("=== テスト完了 ===")
