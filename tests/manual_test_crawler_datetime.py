"""クローラーの日時フォーマットテスト."""
from src.crawler import APICrawler
from pathlib import Path
import tempfile

# 一時ディレクトリを作成
with tempfile.TemporaryDirectory() as tmpdir:
    docs_path = Path(tmpdir) / "docs"
    url_config_path = Path(tmpdir) / "url_config.json"
    
    # URL設定ファイルを作成
    import json
    url_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(url_config_path, 'w') as f:
        json.dump({"apis": {}}, f)
    
    # クローラーを初期化
    crawler = APICrawler(docs_path=str(docs_path), url_config_path=str(url_config_path))
    
    # テストドキュメントを保存
    test_url = "https://example.com/test"
    test_text = "これはテストドキュメントです。"
    doc_type = "test_api"
    
    file_path = crawler._save_document(test_url, test_text, doc_type)
    
    print("=== クローラーの日時フォーマットテスト ===\n")
    print(f"保存されたファイル: {file_path}\n")
    
    # ファイル内容を読み込んで表示
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("ファイル内容:")
    print("-" * 50)
    print(content[:300])  # 最初の300文字を表示
    print("-" * 50)
    print()
    
    # メタデータ部分を抽出
    lines = content.split('\n')
    print("メタデータ:")
    for line in lines[1:10]:  # メタデータ部分
        if line.startswith('crawled_at:'):
            print(f"  {line}")
            crawled_at = line.split('crawled_at: ')[1]
            print(f"  フォーマット: YYYY/MM/DD hh:mm:ss")
            print(f"  値: {crawled_at}")
            
            # 日時のパース確認
            from datetime import datetime
            try:
                parsed = datetime.strptime(crawled_at, '%Y/%m/%d %H:%M:%S')
                print(f"  パース成功: {parsed}")
            except Exception as e:
                print(f"  パース失敗: {e}")
            break
    
    print("\n=== テスト完了 ===")
