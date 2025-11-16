"""自動クロールスクリプト.

GitHub Actionsから週次で実行され、URL設定ファイルに登録された
すべてのAPIドキュメントをクロールします。
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawler import APICrawler, CrawlerError


# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def git_pull():
    """Git pullを実行."""
    try:
        logger.info("Executing git pull...")
        result = subprocess.run(
            ['git', 'pull'],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Git pull successful: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Git pull failed: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during git pull: {e}")
        return False


def git_commit_and_push(message: str):
    """Git commit and pushを実行."""
    try:
        # git add
        logger.info("Executing git add...")
        subprocess.run(
            ['git', 'add', 'data/docs/'],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        
        # git commit
        logger.info(f"Executing git commit with message: {message}")
        result = subprocess.run(
            ['git', 'commit', '-m', message],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        # コミットするものがない場合
        if result.returncode != 0:
            if 'nothing to commit' in result.stdout or 'nothing to commit' in result.stderr:
                logger.info("No changes to commit")
                return True
            else:
                logger.error(f"Git commit failed: {result.stderr}")
                return False
        
        logger.info(f"Git commit successful: {result.stdout.strip()}")
        
        # git push
        logger.info("Executing git push...")
        result = subprocess.run(
            ['git', 'push'],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Git push successful: {result.stdout.strip()}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during git operations: {e}")
        return False


async def crawl_all_apis():
    """
    URL設定ファイルに登録されたすべてのAPIドキュメントをクロール.
    
    Returns:
        dict: クロール結果の統計情報
    """
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info("Starting automatic API documentation crawl")
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    # Git pullを実行
    if not git_pull():
        logger.warning("Git pull failed, but continuing with crawl...")
    
    # 統計情報
    stats = {
        'total_apis': 0,
        'successful_apis': 0,
        'failed_apis': 0,
        'total_pages': 0,
        'errors': []
    }
    
    try:
        # パスを設定（環境変数が設定されている場合はそれを使用、なければプロジェクトルートからの相対パス）
        docs_path = os.getenv("DOCS_STORE_PATH")
        url_config_path = os.getenv("URL_CONFIG_PATH")
        
        if not docs_path or not Path(docs_path).exists():
            # 環境変数が設定されていないか、パスが存在しない場合は相対パスを使用
            docs_path = str(project_root / "data" / "docs")
            logger.info(f"Using default document store path: {docs_path}")
        
        if not url_config_path or not Path(url_config_path).exists():
            # 環境変数が設定されていないか、パスが存在しない場合は相対パスを使用
            url_config_path = str(project_root / "config" / "url_config.json")
            logger.info(f"Using default URL config path: {url_config_path}")
        
        logger.info(f"Document store path: {docs_path}")
        logger.info(f"URL config path: {url_config_path}")
        
        # クローラーを初期化
        crawler = APICrawler(docs_path=docs_path, url_config_path=url_config_path)
        
        # 登録されているAPI一覧を取得
        apis = crawler.list_available_apis()
        stats['total_apis'] = len(apis)
        
        logger.info(f"Found {len(apis)} APIs to crawl")
        logger.info("-" * 80)
        
        # 各APIをクロール
        for keyword, api_info in apis.items():
            logger.info(f"Crawling API: {api_info['name']} (keyword: {keyword})")
            logger.info(f"URL: {api_info['url']}")
            logger.info(f"Description: {api_info.get('description', 'N/A')}")
            
            try:
                # URLを解決
                url = crawler.resolve_url(keyword)
                
                # クロールを実行（最大深度3）
                file_paths = await crawler.crawl(
                    start_url=url,
                    max_depth=3,
                    doc_type=keyword
                )
                
                # 統計情報を更新
                stats['successful_apis'] += 1
                stats['total_pages'] += len(file_paths)
                
                logger.info(f"✓ Successfully crawled {len(file_paths)} pages for {api_info['name']}")
                
            except CrawlerError as e:
                # クローラーエラー
                stats['failed_apis'] += 1
                error_msg = f"Failed to crawl {api_info['name']}: {e}"
                stats['errors'].append(error_msg)
                logger.error(f"✗ {error_msg}")
                
            except Exception as e:
                # 予期しないエラー
                stats['failed_apis'] += 1
                error_msg = f"Unexpected error while crawling {api_info['name']}: {e}"
                stats['errors'].append(error_msg)
                logger.exception(f"✗ {error_msg}")
            
            logger.info("-" * 80)
        
    except Exception as e:
        logger.exception(f"Unexpected error during crawl: {e}")
        stats['errors'].append(f"Unexpected error: {e}")
        return stats
    
    finally:
        # 終了時刻と統計情報を出力
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info("=" * 80)
        logger.info("Crawl completed")
        logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Duration: {duration}")
        logger.info("")
        logger.info("Statistics:")
        logger.info(f"  Total APIs: {stats['total_apis']}")
        logger.info(f"  Successful: {stats['successful_apis']}")
        logger.info(f"  Failed: {stats['failed_apis']}")
        logger.info(f"  Total pages crawled: {stats['total_pages']}")
        
        if stats['errors']:
            logger.info("")
            logger.info("Errors:")
            for error in stats['errors']:
                logger.info(f"  - {error}")
        
        logger.info("=" * 80)
        
        # Git commit and pushを実行
        if stats['total_pages'] > 0:
            commit_message = f"Auto-crawl: Updated {stats['successful_apis']} APIs ({stats['total_pages']} pages) at {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
            if not git_commit_and_push(commit_message):
                logger.warning("Git commit and push failed")
                stats['errors'].append("Git commit and push failed")
        else:
            logger.info("No pages crawled, skipping git commit and push")
    
    return stats


def main():
    """メインエントリーポイント."""
    try:
        # 非同期でクロールを実行
        stats = asyncio.run(crawl_all_apis())
        
        # 終了コードを決定
        if stats['failed_apis'] > 0:
            logger.warning(f"Crawl completed with {stats['failed_apis']} failures")
            sys.exit(1)
        else:
            logger.info("All APIs crawled successfully")
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("Crawl interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
