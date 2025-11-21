"""APIドキュメントをクロールするモジュール."""
import asyncio
import json
import logging
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urljoin, urldefrag
import hashlib

import aiohttp
from bs4 import BeautifulSoup
import html2text

from src.config import get_config, ConfigError
from src.errors import MCPError
from src.logging_config import get_logger
from src.cloudflare_renderer import CloudflareRenderer
from src.page_classifier import PageClassifier

# ロガーの設定
logger = get_logger(__name__)


class CrawlerError(MCPError):
    """クローラー関連のエラー.
    
    Webページの取得、HTML解析、ファイル保存、
    URL解決などで発生するエラー。
    """
    pass


class APICrawler:
    """APIドキュメントをクロールするクラス."""
    
    # 日本標準時のタイムゾーン
    JST = timezone(timedelta(hours=9))
    
    def __init__(self, docs_path: Optional[str] = None, url_config_path: Optional[str] = None, auto_git_push: bool = False):
        """
        APIクローラーを初期化.
        
        Args:
            docs_path: ドキュメント保存先パス（Noneの場合は設定から取得）
            url_config_path: URL設定ファイルのパス（Noneの場合は設定から取得）
            auto_git_push: クロール完了後に自動的にGit push（デフォルト: False）
            
        Raises:
            CrawlerError: 初期化に失敗した場合
        """
        # パスが明示的に指定されている場合は、設定を使用しない
        if docs_path is not None and url_config_path is not None:
            self.docs_path = Path(docs_path)
            self.url_config_path = Path(url_config_path)
            self.cloudflare_renderer = None
        else:
            # 設定から取得（環境変数が必要）
            try:
                config = get_config()
                self.docs_path = Path(docs_path or config.get_docs_store_path())
                self.url_config_path = Path(url_config_path or config.get_url_config_path())
                
                # Cloudflare Browser Rendering統合を初期化
                if config.cloudflare_api_token and config.cloudflare_account_id:
                    self.cloudflare_renderer = CloudflareRenderer(
                        api_token=config.cloudflare_api_token,
                        account_id=config.cloudflare_account_id
                    )
                    logger.info("Cloudflare Browser Rendering enabled")
                else:
                    self.cloudflare_renderer = None
                    logger.info("Cloudflare Browser Rendering disabled (credentials not set)")
            except ConfigError as e:
                raise CrawlerError(f"Failed to initialize crawler: {e}")
        
        # URL設定を読み込む
        self.url_config = self._load_url_config()
        
        # クロール状態管理
        self.visited_urls = set()
        self.rate_limit_delay = 1.0  # 秒
        self.auto_git_push = auto_git_push
        
        # プロジェクトルートを取得
        self.project_root = self.docs_path.parent.parent
    
    def _load_url_config(self) -> dict:
        """
        URL設定ファイルを読み込む.
        
        Returns:
            dict: URL設定（apis辞書）
            
        Raises:
            CrawlerError: 設定ファイルの読み込みに失敗した場合
        """
        try:
            if not self.url_config_path.exists():
                raise CrawlerError(
                    f"URL config file not found: {self.url_config_path}"
                )
            
            with open(self.url_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 設定ファイルの構造を検証
            if 'apis' not in config:
                raise CrawlerError(
                    "Invalid URL config format: 'apis' key not found"
                )
            
            return config['apis']
            
        except json.JSONDecodeError as e:
            raise CrawlerError(f"Failed to parse URL config file: {e}")
        except Exception as e:
            raise CrawlerError(f"Failed to load URL config: {e}")
    
    def resolve_url(self, keyword_or_url: str) -> str:
        """
        キーワードまたはURLからURLを解決.
        
        Args:
            keyword_or_url: APIドキュメントのキーワードまたはURL
            
        Returns:
            str: 解決されたURL
            
        Raises:
            CrawlerError: URLの解決に失敗した場合
        """
        if not keyword_or_url:
            raise CrawlerError("keyword_or_url cannot be empty")
        
        # URLかどうかを判定（http://またはhttps://で始まる場合）
        if self._is_url(keyword_or_url):
            return keyword_or_url
        
        # キーワードとして扱い、設定ファイルから検索
        return self._resolve_keyword(keyword_or_url)
    
    def _is_url(self, text: str) -> bool:
        """
        文字列がURLかどうかを判定.
        
        Args:
            text: 判定する文字列
            
        Returns:
            bool: URLの場合True
        """
        try:
            result = urlparse(text)
            return result.scheme in ('http', 'https') and bool(result.netloc)
        except Exception:
            return False
    
    def _resolve_keyword(self, keyword: str) -> str:
        """
        キーワードからURLを解決.
        
        Args:
            keyword: APIドキュメントのキーワード
            
        Returns:
            str: 解決されたURL
            
        Raises:
            CrawlerError: キーワードが見つからない場合
        """
        # 完全一致で検索
        if keyword in self.url_config:
            return self.url_config[keyword]['url']
        
        # 大文字小文字を無視して検索
        keyword_lower = keyword.lower()
        for key, value in self.url_config.items():
            if key.lower() == keyword_lower:
                return value['url']
        
        # 部分一致で検索
        matches = []
        for key, value in self.url_config.items():
            if keyword_lower in key.lower():
                matches.append((key, value['url']))
        
        if len(matches) == 1:
            return matches[0][1]
        elif len(matches) > 1:
            # 複数マッチした場合はエラー
            matched_keys = [m[0] for m in matches]
            raise CrawlerError(
                f"Keyword '{keyword}' matches multiple APIs: {', '.join(matched_keys)}. "
                "Please be more specific."
            )
        
        # 見つからない場合
        available_keywords = list(self.url_config.keys())
        raise CrawlerError(
            f"Keyword '{keyword}' not found in URL config. "
            f"Available keywords: {', '.join(available_keywords)}"
        )
    
    def reload_url_config(self) -> None:
        """
        URL設定ファイルを再読み込み.
        
        Raises:
            CrawlerError: 設定ファイルの読み込みに失敗した場合
        """
        logger.info(f"Reloading URL config from {self.url_config_path}")
        self.url_config = self._load_url_config()
        logger.info(f"Successfully reloaded URL config with {len(self.url_config)} APIs")
    
    def list_available_apis(self) -> dict:
        """
        登録されているAPI一覧を取得.
        
        Returns:
            dict: API情報の辞書
        """
        return self.url_config.copy()
    
    def _should_use_cloudflare(self, html: str) -> bool:
        """
        Cloudflareを使用すべきか判定.
        
        Args:
            html: HTMLコンテンツ
            
        Returns:
            bool: Cloudflareを使用すべき場合True
        """
        # Cloudflare Rendererが利用可能でない場合はFalse
        if not self.cloudflare_renderer or not self.cloudflare_renderer.is_available():
            return False
        
        # ページが動的かどうかを判定
        return PageClassifier.is_dynamic_page(html)
    
    async def _fetch_page_with_cloudflare(self, url: str) -> str:
        """
        Cloudflareを使用してページを取得.
        
        Args:
            url: 取得するページのURL
            
        Returns:
            str: レンダリングされたMarkdown
            
        Raises:
            CrawlerError: レンダリングに失敗した場合
        """
        try:
            logger.info(f"Using Cloudflare Browser Rendering for: {url}")
            markdown = await self.cloudflare_renderer.render_to_markdown(url)
            return markdown
        except CrawlerError as e:
            logger.warning(f"Cloudflare rendering failed for {url}: {e}")
            raise
    
    async def _fetch_page(self, url: str, session: aiohttp.ClientSession) -> str:
        """
        Webページを非同期で取得（Cloudflare統合を含む）.
        
        処理フロー:
        1. 通常のHTTP GETでページを取得
        2. 動的ページかどうかを判定
        3. 動的ページの場合、Cloudflareでレンダリング
        4. 静的ページの場合、BeautifulSoupで処理
        
        Args:
            url: 取得するページのURL
            session: aiohttpのクライアントセッション
            
        Returns:
            str: 取得したHTMLコンテンツまたはMarkdown
            
        Raises:
            CrawlerError: ページの取得に失敗した場合
        """
        try:
            logger.info(f"Fetching page: {url}")
            
            # レート制限を適用（前回のリクエストから1秒待機）
            await asyncio.sleep(self.rate_limit_delay)
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                # HTTPステータスコードをチェック
                if response.status == 200:
                    html = await response.text()
                    logger.info(f"Successfully fetched page: {url} ({len(html)} bytes)")
                    
                    # 動的ページかどうかを判定
                    if self._should_use_cloudflare(html):
                        try:
                            # Cloudflareでレンダリング
                            markdown = await self._fetch_page_with_cloudflare(url)
                            logger.info(f"Successfully rendered with Cloudflare: {url}")
                            return markdown
                        except CrawlerError as e:
                            # Cloudflareエラー時はBeautifulSoupにフォールバック
                            logger.warning(
                                f"Cloudflare rendering failed, falling back to BeautifulSoup: {e}"
                            )
                            return html
                    
                    # 静的ページの場合はそのまま返す
                    return html
                    
                elif response.status == 404:
                    raise CrawlerError(f"Page not found (404): {url}")
                elif response.status == 403:
                    raise CrawlerError(f"Access forbidden (403): {url}")
                elif response.status == 429:
                    raise CrawlerError(f"Rate limit exceeded (429): {url}")
                elif response.status >= 500:
                    raise CrawlerError(f"Server error ({response.status}): {url}")
                else:
                    raise CrawlerError(f"HTTP error ({response.status}): {url}")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching {url}: {e}")
            raise CrawlerError(f"Network error while fetching {url}: {e}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout while fetching {url}")
            raise CrawlerError(f"Timeout while fetching {url}")
        except Exception as e:
            logger.error(f"Unexpected error while fetching {url}: {e}")
            raise CrawlerError(f"Unexpected error while fetching {url}: {e}")

    def _convert_to_text(self, html: str, url: str) -> str:
        """
        HTMLをテキスト形式に変換.
        
        Args:
            html: 変換するHTMLコンテンツ
            url: ページのURL
            
        Returns:
            str: 変換されたテキスト
            
        Raises:
            CrawlerError: 変換に失敗した場合
        """
        try:
            # BeautifulSoupでHTMLをパース
            soup = BeautifulSoup(html, 'html.parser')
            
            # スクリプトとスタイルタグを削除
            for script in soup(['script', 'style']):
                script.decompose()
            
            # html2textでテキストに変換
            h = html2text.HTML2Text()
            h.ignore_links = False  # リンクを保持
            h.ignore_images = True  # 画像は無視
            h.ignore_emphasis = False  # 強調を保持
            h.body_width = 0  # 行の折り返しを無効化
            
            text = h.handle(str(soup))
            
            logger.info(f"Successfully converted HTML to text: {url}")
            return text.strip()
            
        except Exception as e:
            logger.error(f"Failed to convert HTML to text for {url}: {e}")
            raise CrawlerError(f"Failed to convert HTML to text: {e}")
    
    def _save_document(self, url: str, text: str, doc_type: str, is_first_page: bool = False) -> str:
        """
        ドキュメントをメタデータ付きでファイルに保存.
        
        Args:
            url: ページのURL
            text: 保存するテキストコンテンツ
            doc_type: ドキュメントの種類
            is_first_page: 最初のページかどうか（Trueの場合は新規作成、Falseの場合は追記）
            
        Returns:
            str: 保存したファイルのパス
            
        Raises:
            CrawlerError: ファイルの保存に失敗した場合
        """
        try:
            # ドキュメントストアのディレクトリを作成
            self.docs_path.mkdir(parents=True, exist_ok=True)
            
            # doc_typeをファイル名として使用
            file_name = f"{doc_type}.txt"
            file_path = self.docs_path / file_name
            
            if is_first_page:
                # 最初のページの場合は新規作成してメタデータを追加
                metadata = {
                    'doc_type': doc_type,
                    'crawled_at': datetime.now(self.JST).strftime('%Y/%m/%d %H:%M:%S'),
                    'first_url': url
                }
                
                # メタデータとテキストを結合
                content = "---\n"
                for key, value in metadata.items():
                    content += f"{key}: {value}\n"
                content += "---\n\n"
                content += f"# Page: {url}\n\n"
                content += text
                content += "\n\n" + "=" * 80 + "\n\n"
                
                # ファイルに保存（新規作成）
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"Successfully created document: {file_path}")
            else:
                # 2ページ目以降は追記
                content = f"# Page: {url}\n\n"
                content += text
                content += "\n\n" + "=" * 80 + "\n\n"
                
                # ファイルに追記
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"Successfully appended to document: {file_path}")
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save document for {url}: {e}")
            raise CrawlerError(f"Failed to save document: {e}")
    
    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """
        ページ内のリンクを抽出.
        
        Args:
            html: HTMLコンテンツ
            base_url: ベースURL（相対URLを絶対URLに変換するため）
            
        Returns:
            list[str]: 抽出されたURLのリスト
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            links = []
            
            # ベースURLのパスを取得
            base_parsed = urlparse(base_url)
            base_path = base_parsed.path.rstrip('/')
            
            # すべてのaタグを取得
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                
                # フラグメント（#以降）を除去
                href, _ = urldefrag(href)
                
                # 空のhrefはスキップ
                if not href:
                    continue
                
                # 絶対URLに変換
                absolute_url = urljoin(base_url, href)
                
                # 同じドメインのURLのみを対象とする
                link_parsed = urlparse(absolute_url)
                if base_parsed.netloc != link_parsed.netloc:
                    continue
                
                # 現在のパスより上の階層へのリンクを除外
                link_path = link_parsed.path.rstrip('/')
                if not link_path.startswith(base_path):
                    logger.debug(f"Skipping link to parent path: {absolute_url}")
                    continue
                
                links.append(absolute_url)
            
            # 重複を除去
            unique_links = list(set(links))
            logger.info(f"Extracted {len(unique_links)} unique links from {base_url}")
            
            return unique_links
            
        except Exception as e:
            logger.error(f"Failed to extract links from {base_url}: {e}")
            return []
    
    def _git_commit_and_push(self, doc_type: str, page_count: int) -> bool:
        """
        クロール結果をGitにコミット・プッシュ.
        
        Args:
            doc_type: ドキュメントの種類
            page_count: クロールしたページ数
            
        Returns:
            bool: 成功した場合True
        """
        try:
            # git add
            logger.info("Executing git add...")
            subprocess.run(
                ['git', 'add', str(self.docs_path.relative_to(self.project_root))],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            # git commit
            commit_message = f"Auto-crawl: Updated {doc_type} ({page_count} pages) at {datetime.now(self.JST).strftime('%Y-%m-%d %H:%M:%S')}"
            logger.info(f"Executing git commit with message: {commit_message}")
            result = subprocess.run(
                ['git', 'commit', '-m', commit_message],
                cwd=self.project_root,
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
                cwd=self.project_root,
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
    
    async def crawl(self, start_url: str, max_depth: int = 3, doc_type: Optional[str] = None) -> list[str]:
        """
        再帰的にページをクロール.
        
        Args:
            start_url: クロール開始URL
            max_depth: 最大深度（デフォルト: 3）
            doc_type: ドキュメントの種類（Noneの場合はURLから推測）
            
        Returns:
            list[str]: クロールしたファイルパスのリスト
            
        Raises:
            CrawlerError: クロールに失敗した場合
        """
        # 訪問済みURLをリセット
        self.visited_urls = set()
        
        # doc_typeが指定されていない場合、URLから推測
        if doc_type is None:
            # URL設定から逆引き
            for key, value in self.url_config.items():
                if value['url'] in start_url or start_url in value['url']:
                    doc_type = key
                    break
            
            # 見つからない場合はドメイン名を使用
            if doc_type is None:
                parsed = urlparse(start_url)
                doc_type = parsed.netloc.replace('.', '_')
        
        logger.info(f"Starting crawl from {start_url} with max_depth={max_depth}, doc_type={doc_type}")
        
        # クロールしたファイルパスのリスト
        file_paths = []
        
        # ページカウンター（最初のページかどうかを判定するため）
        page_counter = {'count': 0}
        
        # aiohttpセッションを作成
        async with aiohttp.ClientSession() as session:
            # 再帰的クロールを実行
            await self._crawl_recursive(
                url=start_url,
                session=session,
                depth=0,
                max_depth=max_depth,
                doc_type=doc_type,
                file_paths=file_paths,
                page_counter=page_counter
            )
        
        logger.info(f"Crawl completed. Total pages crawled: {len(file_paths)}")
        
        # 自動Git pushが有効な場合
        if self.auto_git_push and len(file_paths) > 0:
            logger.info("Auto git push is enabled, committing and pushing changes...")
            if self._git_commit_and_push(doc_type, page_counter['count']):
                logger.info("Successfully pushed changes to Git")
            else:
                logger.warning("Failed to push changes to Git")
        
        return file_paths
    
    async def _crawl_recursive(
        self,
        url: str,
        session: aiohttp.ClientSession,
        depth: int,
        max_depth: int,
        doc_type: str,
        file_paths: list[str],
        page_counter: dict
    ):
        """
        再帰的にページをクロール（内部メソッド）.
        
        Args:
            url: クロールするURL
            session: aiohttpのクライアントセッション
            depth: 現在の深度
            max_depth: 最大深度
            doc_type: ドキュメントの種類
            file_paths: クロールしたファイルパスのリスト（出力用）
            page_counter: ページカウンター（最初のページかどうかを判定するため）
        """
        # 最大深度を超えた場合は終了
        if depth > max_depth:
            logger.debug(f"Max depth reached for {url}")
            return
        
        # 既に訪問済みの場合はスキップ
        if url in self.visited_urls:
            logger.debug(f"Already visited: {url}")
            return
        
        # 訪問済みとしてマーク
        self.visited_urls.add(url)
        
        try:
            # ページを取得
            html = await self._fetch_page(url, session)
            
            # [HTTPS POST]
            # URL: https://api.cloudflare.com/client/v4/accounts/{accountId}/
            #     browser-rendering/Markdown
            # Headers: Authorization: Bearer {API_TOKEN}
            # Body: {"url": "https://example-spa.com/"}

            # テキストに変換
            text = self._convert_to_text(html, url)
            
            # 最初のページかどうかを判定
            is_first_page = page_counter['count'] == 0
            page_counter['count'] += 1
            
            # ファイルに保存
            file_path = self._save_document(url, text, doc_type, is_first_page)
            if is_first_page or file_path not in file_paths:
                file_paths.append(file_path)
            
            # 最大深度に達していない場合、リンクを抽出して再帰的にクロール
            if depth < max_depth:
                links = self._extract_links(html, url)
                logger.info(f"Found {len(links)} links at depth {depth} from {url}")
                
                # 各リンクを再帰的にクロール
                for link in links:
                    await self._crawl_recursive(
                        url=link,
                        session=session,
                        depth=depth + 1,
                        max_depth=max_depth,
                        doc_type=doc_type,
                        file_paths=file_paths,
                        page_counter=page_counter
                    )
        
        except CrawlerError as e:
            # エラーをログに記録して継続
            logger.error(f"Error crawling {url}: {e}")
        except Exception as e:
            # 予期しないエラーもログに記録して継続
            logger.exception(f"Unexpected error crawling {url}: {e}")
