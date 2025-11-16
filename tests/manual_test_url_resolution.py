"""URL解決機能の手動テストスクリプト."""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawler import APICrawler, CrawlerError


def test_url_resolution():
    """URL解決機能をテスト."""
    print("=== URL解決機能のテスト ===\n")
    
    try:
        # クローラーを初期化
        crawler = APICrawler(
            docs_path="data/docs",
            url_config_path="config/url_config.json"
        )
        print("✓ クローラーの初期化成功\n")
        
        # 登録されているAPI一覧を表示
        print("登録されているAPI:")
        apis = crawler.list_available_apis()
        for key, value in apis.items():
            print(f"  - {key}: {value['url']}")
        print()
        
        # テストケース1: キーワードでURL解決（完全一致）
        print("テスト1: キーワード 'Arduino Docs' でURL解決")
        url = crawler.resolve_url("Arduino Docs")
        print(f"  結果: {url}")
        print(f"  ✓ 成功\n")
        
        # テストケース2: キーワードでURL解決（大文字小文字を無視）
        print("テスト2: キーワード 'arduino docs' でURL解決（大文字小文字を無視）")
        url = crawler.resolve_url("arduino docs")
        print(f"  結果: {url}")
        print(f"  ✓ 成功\n")
        
        # テストケース3: キーワードでURL解決（部分一致）
        print("テスト3: キーワード 'arduino' でURL解決（部分一致）")
        url = crawler.resolve_url("arduino")
        print(f"  結果: {url}")
        print(f"  ✓ 成功\n")
        
        # テストケース3-2: M5 Docsでもテスト
        print("テスト3-2: キーワード 'M5 Docs' でURL解決")
        url = crawler.resolve_url("M5 Docs")
        print(f"  結果: {url}")
        print(f"  ✓ 成功\n")
        
        # テストケース3-3: M5の部分一致でもテスト
        print("テスト3-3: キーワード 'm5' でURL解決（部分一致）")
        url = crawler.resolve_url("m5")
        print(f"  結果: {url}")
        print(f"  ✓ 成功\n")
        
        # テストケース4: 直接URLを渡す
        print("テスト4: 直接URL 'https://example.com/docs' を渡す")
        url = crawler.resolve_url("https://example.com/docs")
        print(f"  結果: {url}")
        print(f"  ✓ 成功\n")
        
        # テストケース5: 存在しないキーワード（エラーケース）
        print("テスト5: 存在しないキーワード 'nonexistent' でURL解決")
        try:
            url = crawler.resolve_url("nonexistent")
            print(f"  ✗ エラーが発生すべきでした")
        except CrawlerError as e:
            print(f"  期待通りエラー: {e}")
            print(f"  ✓ 成功\n")
        
        print("=== すべてのテストが成功しました ===")
        
    except Exception as e:
        print(f"✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = test_url_resolution()
    sys.exit(0 if success else 1)
