"""統合テスト.

MCPサーバー全体の動作を確認するテスト。
"""
import asyncio
import json
import os
import sys
from pathlib import Path
import tempfile
import shutil

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_config, reset_config, ConfigError
from src.crawler import APICrawler, CrawlerError
from src.rag_manager import GeminiRAGManager, RAGError
from src.logging_config import setup_logging, get_logger


# ロギング設定
setup_logging(log_level="INFO", use_stdout=True)
logger = get_logger(__name__)


class IntegrationTestError(Exception):
    """統合テストのエラー."""
    pass


async def test_crawler():
    """クローラーの基本動作をテスト."""
    logger.info("=" * 80)
    logger.info("Testing Crawler")
    logger.info("=" * 80)
    
    try:
        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_path = Path(temp_dir) / "docs"
            url_config_path = project_root / "config" / "url_config.json"
            
            # クローラーを初期化
            crawler = APICrawler(
                docs_path=str(docs_path),
                url_config_path=str(url_config_path)
            )
            
            # URL設定を確認
            apis = crawler.list_available_apis()
            logger.info(f"✓ Found {len(apis)} APIs in config")
            
            if not apis:
                raise IntegrationTestError("No APIs found in URL config")
            
            # 最初のAPIをテスト用に選択
            test_keyword = list(apis.keys())[0]
            test_api = apis[test_keyword]
            logger.info(f"✓ Testing with API: {test_api['name']} (keyword: {test_keyword})")
            
            # URL解決をテスト
            url = crawler.resolve_url(test_keyword)
            logger.info(f"✓ Resolved URL: {url}")
            
            # クロールをテスト（深度1で1ページのみ）
            logger.info("✓ Starting crawl (max_depth=1)...")
            file_paths = await crawler.crawl(
                start_url=url,
                max_depth=1,
                doc_type=test_keyword
            )
            
            logger.info(f"✓ Crawled {len(file_paths)} pages")
            
            # ファイルが作成されたことを確認
            if not file_paths:
                raise IntegrationTestError("No files were created during crawl")
            
            for file_path in file_paths:
                if not Path(file_path).exists():
                    raise IntegrationTestError(f"File not found: {file_path}")
            
            logger.info("✓ All crawled files exist")
            
            # ファイルの内容を確認
            first_file = Path(file_paths[0])
            content = first_file.read_text(encoding='utf-8')
            
            if not content:
                raise IntegrationTestError("Crawled file is empty")
            
            # メタデータが含まれているか確認
            if "doc_type:" not in content:
                raise IntegrationTestError("Metadata not found in crawled file")
            
            logger.info("✓ Crawled file contains metadata")
            logger.info("✓ Crawler test passed")
            
    except CrawlerError as e:
        logger.error(f"✗ Crawler error: {e}")
        raise IntegrationTestError(f"Crawler test failed: {e}")
    except Exception as e:
        logger.exception(f"✗ Unexpected error: {e}")
        raise IntegrationTestError(f"Crawler test failed: {e}")


async def test_rag_manager():
    """RAGマネージャーの基本動作をテスト."""
    logger.info("=" * 80)
    logger.info("Testing RAG Manager")
    logger.info("=" * 80)
    
    try:
        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "rag_config.json"
            
            # RAGマネージャーを初期化
            rag_manager = GeminiRAGManager(config_path=str(config_path))
            logger.info("✓ RAG Manager initialized")
            
            # 設定ファイルが作成されたことを確認
            if not config_path.exists():
                raise IntegrationTestError("RAG config file was not created")
            
            logger.info("✓ RAG config file created")
            
            # 設定ファイルの内容を確認
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if "rags" not in config:
                raise IntegrationTestError("Invalid RAG config format")
            
            logger.info("✓ RAG config file has valid format")
            
            # RAGの追加をテスト
            test_rag_id = "fileSearchStores/test123"
            test_doc_type = "test_docs"
            
            rag_entry = rag_manager.add_rag(
                doc_type=test_doc_type,
                rag_id=test_rag_id,
                description="Test RAG"
            )
            
            logger.info(f"✓ Added RAG: {rag_entry}")
            
            # RAGが追加されたことを確認
            rags = rag_manager.get_rags_by_type(test_doc_type)
            if not rags:
                raise IntegrationTestError("RAG was not added to config")
            
            if rags[0]["rag_id"] != test_rag_id:
                raise IntegrationTestError("RAG ID mismatch")
            
            logger.info("✓ RAG was added successfully")
            
            # 最新のRAG IDを取得
            latest_rag_id = rag_manager.get_latest_rag_id(test_doc_type)
            if latest_rag_id != test_rag_id:
                raise IntegrationTestError("Latest RAG ID mismatch")
            
            logger.info("✓ Latest RAG ID retrieved successfully")
            logger.info("✓ RAG Manager test passed")
            
    except RAGError as e:
        logger.error(f"✗ RAG error: {e}")
        raise IntegrationTestError(f"RAG Manager test failed: {e}")
    except Exception as e:
        logger.exception(f"✗ Unexpected error: {e}")
        raise IntegrationTestError(f"RAG Manager test failed: {e}")


async def test_error_handling():
    """エラーハンドリングをテスト."""
    logger.info("=" * 80)
    logger.info("Testing Error Handling")
    logger.info("=" * 80)
    
    try:
        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_path = Path(temp_dir) / "docs"
            url_config_path = project_root / "config" / "url_config.json"
            
            # クローラーを初期化
            crawler = APICrawler(
                docs_path=str(docs_path),
                url_config_path=str(url_config_path)
            )
            
            # 存在しないキーワードでエラーが発生することを確認
            try:
                crawler.resolve_url("nonexistent_keyword_12345")
                raise IntegrationTestError("Expected CrawlerError was not raised")
            except CrawlerError as e:
                logger.info(f"✓ CrawlerError raised as expected: {e}")
            
            # 無効なURLでクロールした場合、エラーをログに記録して空のリストを返すことを確認
            # （クローラーはエラーをログに記録して継続する設計のため）
            file_paths = await crawler.crawl("invalid://url", max_depth=1)
            if len(file_paths) == 0:
                logger.info("✓ Invalid URL crawl returned empty list as expected")
            else:
                raise IntegrationTestError("Expected empty list for invalid URL crawl")
            
            logger.info("✓ Error handling test passed")
            
    except IntegrationTestError:
        raise
    except Exception as e:
        logger.exception(f"✗ Unexpected error: {e}")
        raise IntegrationTestError(f"Error handling test failed: {e}")


async def test_config():
    """設定管理をテスト."""
    logger.info("=" * 80)
    logger.info("Testing Config Management")
    logger.info("=" * 80)
    
    try:
        # 環境変数が設定されているか確認
        required_env_vars = [
            "GEMINI_FILE_SEARCH_API_KEY",
            "GEMINI_CODE_GEN_API_KEY"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(f"⚠ Missing environment variables: {', '.join(missing_vars)}")
            logger.warning("⚠ Skipping config test (environment variables not set)")
            return
        
        # 一時ディレクトリを使用して設定をテスト
        with tempfile.TemporaryDirectory() as temp_dir:
            # 環境変数を一時的に上書き
            original_env = {}
            temp_paths = {
                "RAG_CONFIG_PATH": str(Path(temp_dir) / "config" / "rag_config.json"),
                "DOCS_STORE_PATH": str(Path(temp_dir) / "data" / "docs"),
                "URL_CONFIG_PATH": str(project_root / "config" / "url_config.json"),
            }
            
            for key, value in temp_paths.items():
                original_env[key] = os.getenv(key)
                os.environ[key] = value
            
            try:
                # 設定を取得
                reset_config()
                config = get_config()
                logger.info("✓ Config loaded successfully")
                
                # 設定値を確認
                if not config.get_gemini_file_search_api_key():
                    raise IntegrationTestError("GEMINI_FILE_SEARCH_API_KEY not set")
                
                if not config.get_gemini_code_gen_api_key():
                    raise IntegrationTestError("GEMINI_CODE_GEN_API_KEY not set")
                
                logger.info("✓ API keys are set")
                
                # パスを確認
                logger.info(f"✓ RAG config path: {config.get_rag_config_path()}")
                logger.info(f"✓ Docs store path: {config.get_docs_store_path()}")
                logger.info(f"✓ URL config path: {config.get_url_config_path()}")
                logger.info(f"✓ RAG max age days: {config.get_rag_max_age_days()}")
                
                logger.info("✓ Config test passed")
                
            finally:
                # 環境変数を元に戻す
                for key, value in original_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
                reset_config()
        
    except ConfigError as e:
        logger.error(f"✗ Config error: {e}")
        raise IntegrationTestError(f"Config test failed: {e}")
    except Exception as e:
        logger.exception(f"✗ Unexpected error: {e}")
        raise IntegrationTestError(f"Config test failed: {e}")


async def run_all_tests():
    """すべてのテストを実行."""
    logger.info("=" * 80)
    logger.info("Starting Integration Tests")
    logger.info("=" * 80)
    
    tests = [
        ("Config Management", test_config),
        ("Crawler", test_crawler),
        ("RAG Manager", test_rag_manager),
        ("Error Handling", test_error_handling),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test_name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except IntegrationTestError as e:
            failed += 1
            errors.append((test_name, str(e)))
            logger.error(f"✗ {test_name} test failed: {e}")
        except Exception as e:
            failed += 1
            errors.append((test_name, f"Unexpected error: {e}"))
            logger.exception(f"✗ {test_name} test failed with unexpected error")
    
    # 結果を出力
    logger.info("=" * 80)
    logger.info("Integration Test Results")
    logger.info("=" * 80)
    logger.info(f"Total tests: {len(tests)}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    
    if errors:
        logger.info("")
        logger.info("Failed tests:")
        for test_name, error in errors:
            logger.info(f"  - {test_name}: {error}")
    
    logger.info("=" * 80)
    
    return failed == 0


def main():
    """メインエントリーポイント."""
    try:
        success = asyncio.run(run_all_tests())
        
        if success:
            logger.info("✓ All integration tests passed")
            sys.exit(0)
        else:
            logger.error("✗ Some integration tests failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
