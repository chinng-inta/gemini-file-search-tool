"""APIクローラーのテスト."""
import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from src.crawler import APICrawler, CrawlerError
import aiohttp


@pytest.fixture
def temp_config_dir(tmp_path):
    """一時的な設定ディレクトリを作成."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    # URL設定ファイルを作成（実際のconfig/url_config.jsonと同じ構造）
    url_config = {
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
            }
        }
    }
    
    url_config_path = config_dir / "url_config.json"
    with open(url_config_path, 'w', encoding='utf-8') as f:
        json.dump(url_config, f, ensure_ascii=False, indent=2)
    
    return config_dir


@pytest.fixture
def crawler(temp_config_dir, tmp_path):
    """テスト用のクローラーインスタンスを作成."""
    docs_path = tmp_path / "docs"
    docs_path.mkdir()
    url_config_path = temp_config_dir / "url_config.json"
    return APICrawler(docs_path=str(docs_path), url_config_path=str(url_config_path))


class TestURLResolution:
    """URL解決機能のテスト."""
    
    def test_resolve_url_with_keyword_exact_match(self, crawler):
        """キーワード（完全一致）からURLを解決できることを確認."""
        url = crawler.resolve_url("Arduino Docs")
        assert url == "https://docs.arduino.cc/"
    
    def test_resolve_url_with_keyword_case_insensitive(self, crawler):
        """キーワード（大文字小文字を無視）からURLを解決できることを確認."""
        url = crawler.resolve_url("ARDUINO DOCS")
        assert url == "https://docs.arduino.cc/"
        
        url = crawler.resolve_url("m5 docs")
        assert url == "https://docs.m5stack.com/ja/start"
    
    def test_resolve_url_with_keyword_partial_match(self, crawler):
        """キーワード（部分一致）からURLを解決できることを確認."""
        url = crawler.resolve_url("arduino")
        assert url == "https://docs.arduino.cc/"
    
    def test_resolve_url_with_direct_url(self, crawler):
        """直接URLを渡した場合、そのまま返されることを確認."""
        url = "https://example.com/docs"
        assert crawler.resolve_url(url) == url
        
        url = "http://example.com/api"
        assert crawler.resolve_url(url) == url
    
    def test_resolve_url_with_invalid_keyword(self, crawler):
        """存在しないキーワードの場合、エラーが発生することを確認."""
        with pytest.raises(CrawlerError) as exc_info:
            crawler.resolve_url("nonexistent")
        
        assert "not found in URL config" in str(exc_info.value)
        assert "Available keywords" in str(exc_info.value)
    
    def test_resolve_url_with_empty_string(self, crawler):
        """空文字列の場合、エラーが発生することを確認."""
        with pytest.raises(CrawlerError) as exc_info:
            crawler.resolve_url("")
        
        assert "cannot be empty" in str(exc_info.value)
    
    def test_resolve_url_with_ambiguous_keyword(self, temp_config_dir, tmp_path):
        """曖昧なキーワード（複数マッチ）の場合、エラーが発生することを確認."""
        # 複数マッチするような設定を作成
        url_config = {
            "apis": {
                "test-api-1": {
                    "name": "Test API 1",
                    "url": "https://example.com/test1",
                    "description": "Test API 1"
                },
                "test-api-2": {
                    "name": "Test API 2",
                    "url": "https://example.com/test2",
                    "description": "Test API 2"
                }
            }
        }
        
        url_config_path = temp_config_dir / "url_config_ambiguous.json"
        with open(url_config_path, 'w', encoding='utf-8') as f:
            json.dump(url_config, f)
        
        docs_path = tmp_path / "docs"
        crawler = APICrawler(docs_path=str(docs_path), url_config_path=str(url_config_path))
        
        with pytest.raises(CrawlerError) as exc_info:
            crawler.resolve_url("test")
        
        assert "matches multiple APIs" in str(exc_info.value)


class TestURLConfigLoading:
    """URL設定ファイル読み込みのテスト."""
    
    def test_load_url_config_success(self, crawler):
        """URL設定ファイルが正常に読み込まれることを確認."""
        assert "Arduino Docs" in crawler.url_config
        assert "M5 Docs" in crawler.url_config
        assert crawler.url_config["Arduino Docs"]["url"] == "https://docs.arduino.cc/"
    
    def test_load_url_config_file_not_found(self, tmp_path):
        """URL設定ファイルが存在しない場合、エラーが発生することを確認."""
        docs_path = tmp_path / "docs"
        docs_path.mkdir()
        nonexistent_path = tmp_path / "nonexistent.json"
        
        with pytest.raises(CrawlerError) as exc_info:
            APICrawler(docs_path=str(docs_path), url_config_path=str(nonexistent_path))
        
        assert "not found" in str(exc_info.value)
    
    def test_load_url_config_invalid_json(self, tmp_path):
        """不正なJSON形式の場合、エラーが発生することを確認."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        docs_path = tmp_path / "docs"
        docs_path.mkdir()
        
        url_config_path = config_dir / "invalid.json"
        with open(url_config_path, 'w') as f:
            f.write("{ invalid json }")
        
        with pytest.raises(CrawlerError) as exc_info:
            APICrawler(docs_path=str(docs_path), url_config_path=str(url_config_path))
        
        assert "Failed to parse" in str(exc_info.value)
    
    def test_load_url_config_missing_apis_key(self, tmp_path):
        """'apis'キーが存在しない場合、エラーが発生することを確認."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        docs_path = tmp_path / "docs"
        docs_path.mkdir()
        
        url_config_path = config_dir / "no_apis.json"
        with open(url_config_path, 'w') as f:
            json.dump({"other_key": {}}, f)
        
        with pytest.raises(CrawlerError) as exc_info:
            APICrawler(docs_path=str(docs_path), url_config_path=str(url_config_path))
        
        assert "'apis' key not found" in str(exc_info.value)


class TestListAvailableAPIs:
    """API一覧取得のテスト."""
    
    def test_list_available_apis(self, crawler):
        """登録されているAPI一覧を取得できることを確認."""
        apis = crawler.list_available_apis()
        
        assert "Arduino Docs" in apis
        assert "M5 Docs" in apis
        assert apis["Arduino Docs"]["name"] == "Arduino Docs"
        assert apis["Arduino Docs"]["url"] == "https://docs.arduino.cc/"
        assert apis["M5 Docs"]["name"] == "M5 Docs"
        assert apis["M5 Docs"]["url"] == "https://docs.m5stack.com/ja/start"



class TestFetchPage:
    """Webページ取得機能のテスト."""
    
    @pytest.mark.asyncio
    async def test_fetch_page_success(self, crawler):
        """正常にページを取得できることを確認."""
        test_url = "https://example.com/test"
        test_html = "<html><body><h1>Test Page</h1></body></html>"
        
        # aiohttpのモックを作成
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=test_html)
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # ページを取得
        html = await crawler._fetch_page(test_url, mock_session)
        
        assert html == test_html
        mock_session.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_page_404_error(self, crawler):
        """404エラーの場合、適切なエラーが発生することを確認."""
        test_url = "https://example.com/notfound"
        
        # 404レスポンスのモックを作成
        mock_response = AsyncMock()
        mock_response.status = 404
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # 404エラーが発生することを確認
        with pytest.raises(CrawlerError) as exc_info:
            await crawler._fetch_page(test_url, mock_session)
        
        assert "404" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_fetch_page_403_error(self, crawler):
        """403エラーの場合、適切なエラーが発生することを確認."""
        test_url = "https://example.com/forbidden"
        
        # 403レスポンスのモックを作成
        mock_response = AsyncMock()
        mock_response.status = 403
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # 403エラーが発生することを確認
        with pytest.raises(CrawlerError) as exc_info:
            await crawler._fetch_page(test_url, mock_session)
        
        assert "403" in str(exc_info.value)
        assert "forbidden" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_fetch_page_429_rate_limit_error(self, crawler):
        """429エラー（レート制限）の場合、適切なエラーが発生することを確認."""
        test_url = "https://example.com/ratelimit"
        
        # 429レスポンスのモックを作成
        mock_response = AsyncMock()
        mock_response.status = 429
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # 429エラーが発生することを確認
        with pytest.raises(CrawlerError) as exc_info:
            await crawler._fetch_page(test_url, mock_session)
        
        assert "429" in str(exc_info.value)
        assert "rate limit" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_fetch_page_500_server_error(self, crawler):
        """500エラー（サーバーエラー）の場合、適切なエラーが発生することを確認."""
        test_url = "https://example.com/servererror"
        
        # 500レスポンスのモックを作成
        mock_response = AsyncMock()
        mock_response.status = 500
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # 500エラーが発生することを確認
        with pytest.raises(CrawlerError) as exc_info:
            await crawler._fetch_page(test_url, mock_session)
        
        assert "500" in str(exc_info.value)
        assert "server error" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_fetch_page_network_error(self, crawler):
        """ネットワークエラーの場合、適切なエラーが発生することを確認."""
        test_url = "https://example.com/networkerror"
        
        # ネットワークエラーを発生させるモックを作成
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=aiohttp.ClientError("Connection failed"))
        
        # ネットワークエラーが発生することを確認
        with pytest.raises(CrawlerError) as exc_info:
            await crawler._fetch_page(test_url, mock_session)
        
        assert "network error" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_fetch_page_timeout_error(self, crawler):
        """タイムアウトエラーの場合、適切なエラーが発生することを確認."""
        test_url = "https://example.com/timeout"
        
        # タイムアウトエラーを発生させるモックを作成
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())
        
        # タイムアウトエラーが発生することを確認
        with pytest.raises(CrawlerError) as exc_info:
            await crawler._fetch_page(test_url, mock_session)
        
        assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_fetch_page_rate_limiting(self, crawler):
        """レート制限（1秒間隔）が適用されることを確認."""
        import time
        
        test_url = "https://example.com/test"
        test_html = "<html><body>Test</body></html>"
        
        # aiohttpのモックを作成
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=test_html)
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # レート制限を短く設定してテスト
        crawler.rate_limit_delay = 0.1
        
        # 2回連続でページを取得
        start_time = time.time()
        await crawler._fetch_page(test_url, mock_session)
        await crawler._fetch_page(test_url, mock_session)
        elapsed_time = time.time() - start_time
        
        # 少なくとも0.1秒（レート制限の遅延）×2回分の時間が経過していることを確認
        assert elapsed_time >= 0.2



class TestConvertToText:
    """HTML→テキスト変換機能のテスト."""
    
    def test_convert_to_text_basic_html(self, crawler):
        """基本的なHTMLをテキストに変換できることを確認."""
        html = "<html><body><h1>Test Title</h1><p>Test paragraph.</p></body></html>"
        url = "https://example.com/test"
        
        text = crawler._convert_to_text(html, url)
        
        assert "Test Title" in text
        assert "Test paragraph" in text
    
    def test_convert_to_text_removes_scripts_and_styles(self, crawler):
        """スクリプトとスタイルタグが削除されることを確認."""
        html = """
        <html>
        <head>
            <style>body { color: red; }</style>
            <script>console.log('test');</script>
        </head>
        <body>
            <h1>Content</h1>
            <script>alert('test');</script>
        </body>
        </html>
        """
        url = "https://example.com/test"
        
        text = crawler._convert_to_text(html, url)
        
        assert "Content" in text
        assert "console.log" not in text
        assert "alert" not in text
        assert "color: red" not in text
    
    def test_convert_to_text_preserves_links(self, crawler):
        """リンクが保持されることを確認."""
        html = '<html><body><a href="https://example.com">Link Text</a></body></html>'
        url = "https://example.com/test"
        
        text = crawler._convert_to_text(html, url)
        
        assert "Link Text" in text
    
    def test_convert_to_text_complex_html(self, crawler):
        """複雑なHTMLをテキストに変換できることを確認."""
        html = """
        <html>
        <body>
            <h1>Main Title</h1>
            <h2>Subtitle</h2>
            <p>First paragraph with <strong>bold text</strong> and <em>italic text</em>.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
            <code>code snippet</code>
        </body>
        </html>
        """
        url = "https://example.com/test"
        
        text = crawler._convert_to_text(html, url)
        
        assert "Main Title" in text
        assert "Subtitle" in text
        assert "First paragraph" in text
        assert "Item 1" in text
        assert "Item 2" in text
        assert "code snippet" in text
    
    def test_convert_to_text_empty_html(self, crawler):
        """空のHTMLを変換できることを確認."""
        html = "<html><body></body></html>"
        url = "https://example.com/test"
        
        text = crawler._convert_to_text(html, url)
        
        # 空文字列または空白のみになることを確認
        assert text == "" or text.isspace()


class TestSaveDocument:
    """ドキュメント保存機能のテスト."""
    
    def test_save_document_basic(self, crawler):
        """基本的なドキュメント保存が正常に動作することを確認."""
        url = "https://example.com/test"
        text = "Test content"
        doc_type = "test_api"
        
        file_path = crawler._save_document(url, text, doc_type)
        
        # ファイルが作成されたことを確認
        assert Path(file_path).exists()
        
        # ファイル内容を確認
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "---" in content
        assert f"url: {url}" in content
        assert "crawled_at:" in content
        assert f"doc_type: {doc_type}" in content
        assert "Test content" in content
    
    def test_save_document_with_doc_type(self, crawler):
        """doc_typeを指定してドキュメントを保存できることを確認."""
        url = "https://example.com/test"
        text = "Test content"
        doc_type = "gemini"
        
        file_path = crawler._save_document(url, text, doc_type)
        
        # ファイル名がdoc_typeになっていることを確認
        assert Path(file_path).name == f"{doc_type}.txt"
        
        # ファイル内容を確認
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert f"doc_type: {doc_type}" in content
    
    def test_save_document_metadata_format(self, crawler):
        """メタデータが正しいフォーマットで保存されることを確認."""
        url = "https://example.com/test"
        text = "Test content"
        doc_type = "test"
        
        file_path = crawler._save_document(url, text, doc_type)
        
        # ファイル内容を確認
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # メタデータセクションの確認
        lines = content.split('\n')
        assert lines[0] == "---"
        assert any(line.startswith("url:") for line in lines)
        assert any(line.startswith("crawled_at:") for line in lines)
        assert any(line.startswith("doc_type:") for line in lines)
        
        # メタデータの終了マーカーを確認
        assert "---" in lines[1:5]  # 最初の数行内に終了マーカーがあることを確認
    
    def test_save_document_creates_directory(self, tmp_path):
        """ドキュメントストアのディレクトリが存在しない場合、作成されることを確認."""
        # 存在しないディレクトリを指定
        docs_path = tmp_path / "new_docs" / "subdirectory"
        url_config_path = tmp_path / "config" / "url_config.json"
        
        # URL設定ファイルを作成
        url_config_path.parent.mkdir(parents=True)
        with open(url_config_path, 'w') as f:
            json.dump({"apis": {}}, f)
        
        crawler = APICrawler(docs_path=str(docs_path), url_config_path=str(url_config_path))
        
        url = "https://example.com/test"
        text = "Test content"
        doc_type = "test_api"
        
        file_path = crawler._save_document(url, text, doc_type)
        
        # ディレクトリとファイルが作成されたことを確認
        assert docs_path.exists()
        assert Path(file_path).exists()
    
    def test_save_document_unique_filenames(self, crawler):
        """異なるdoc_typeに対して一意のファイル名が生成されることを確認."""
        url1 = "https://example.com/page1"
        url2 = "https://example.com/page2"
        text = "Test content"
        doc_type1 = "api1"
        doc_type2 = "api2"
        
        file_path1 = crawler._save_document(url1, text, doc_type1)
        file_path2 = crawler._save_document(url2, text, doc_type2)
        
        # ファイル名が異なることを確認
        assert file_path1 != file_path2
        assert Path(file_path1).exists()
        assert Path(file_path2).exists()
    
    def test_save_document_same_doc_type_overwrites(self, crawler):
        """同じdoc_typeに対して保存すると上書きされることを確認."""
        url1 = "https://example.com/test1"
        url2 = "https://example.com/test2"
        text1 = "First content"
        text2 = "Second content"
        doc_type = "test_api"
        
        file_path1 = crawler._save_document(url1, text1, doc_type)
        file_path2 = crawler._save_document(url2, text2, doc_type)
        
        # ファイルパスが同じことを確認（同じdoc_typeなので）
        assert file_path1 == file_path2
        
        # 最新の内容が保存されていることを確認
        with open(file_path2, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "Second content" in content
        assert "First content" not in content
        # URLも更新されていることを確認
        assert url2 in content
        assert url1 not in content


class TestExtractLinks:
    """リンク抽出機能のテスト."""
    
    def test_extract_links_basic(self, crawler):
        """基本的なリンク抽出が正常に動作することを確認."""
        html = """
        <html>
        <body>
            <a href="https://example.com/page1">Page 1</a>
            <a href="https://example.com/page2">Page 2</a>
        </body>
        </html>
        """
        base_url = "https://example.com/"
        
        links = crawler._extract_links(html, base_url)
        
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links
        assert len(links) == 2
    
    def test_extract_links_relative_urls(self, crawler):
        """相対URLが絶対URLに変換されることを確認."""
        html = """
        <html>
        <body>
            <a href="/docs/page1">Page 1</a>
            <a href="page2">Page 2</a>
            <a href="../other/page3">Page 3</a>
        </body>
        </html>
        """
        base_url = "https://example.com/docs/"
        
        links = crawler._extract_links(html, base_url)
        
        assert "https://example.com/docs/page1" in links
        assert "https://example.com/docs/page2" in links
        assert "https://example.com/other/page3" in links
    
    def test_extract_links_removes_fragments(self, crawler):
        """URLのフラグメント（#以降）が除去されることを確認."""
        html = """
        <html>
        <body>
            <a href="https://example.com/page1#section1">Page 1</a>
            <a href="https://example.com/page1#section2">Page 1 Section 2</a>
        </body>
        </html>
        """
        base_url = "https://example.com/"
        
        links = crawler._extract_links(html, base_url)
        
        # フラグメントが除去され、重複が削除されることを確認
        assert "https://example.com/page1" in links
        assert len(links) == 1
    
    def test_extract_links_same_domain_only(self, crawler):
        """同じドメインのリンクのみが抽出されることを確認."""
        html = """
        <html>
        <body>
            <a href="https://example.com/page1">Internal Page</a>
            <a href="https://other-domain.com/page2">External Page</a>
            <a href="https://example.com/page3">Another Internal Page</a>
        </body>
        </html>
        """
        base_url = "https://example.com/"
        
        links = crawler._extract_links(html, base_url)
        
        assert "https://example.com/page1" in links
        assert "https://example.com/page3" in links
        assert "https://other-domain.com/page2" not in links
        assert len(links) == 2
    
    def test_extract_links_empty_href(self, crawler):
        """空のhrefがスキップされることを確認."""
        html = """
        <html>
        <body>
            <a href="">Empty</a>
            <a href="https://example.com/page1">Valid Page</a>
            <a href="#">Fragment Only</a>
        </body>
        </html>
        """
        base_url = "https://example.com/"
        
        links = crawler._extract_links(html, base_url)
        
        assert "https://example.com/page1" in links
        assert len(links) == 1
    
    def test_extract_links_no_links(self, crawler):
        """リンクがない場合、空のリストが返されることを確認."""
        html = "<html><body><p>No links here</p></body></html>"
        base_url = "https://example.com/"
        
        links = crawler._extract_links(html, base_url)
        
        assert links == []
    
    def test_extract_links_duplicate_removal(self, crawler):
        """重複するリンクが除去されることを確認."""
        html = """
        <html>
        <body>
            <a href="https://example.com/page1">Page 1</a>
            <a href="https://example.com/page1">Page 1 Again</a>
            <a href="https://example.com/page2">Page 2</a>
        </body>
        </html>
        """
        base_url = "https://example.com/"
        
        links = crawler._extract_links(html, base_url)
        
        assert len(links) == 2
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links


class TestRecursiveCrawl:
    """再帰的クロール機能のテスト."""
    
    @pytest.mark.asyncio
    async def test_crawl_single_page(self, crawler):
        """単一ページのクロールが正常に動作することを確認."""
        test_url = "https://example.com/docs"
        test_html = "<html><body><h1>Test Page</h1></body></html>"
        
        # aiohttpのモックを作成
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=test_html)
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            # クロールを実行（max_depth=0で単一ページのみ）
            file_paths = await crawler.crawl(test_url, max_depth=0, doc_type="test")
            
            assert len(file_paths) == 1
            assert Path(file_paths[0]).exists()
    
    @pytest.mark.asyncio
    async def test_crawl_with_links(self, crawler):
        """リンクを含むページの再帰的クロールが正常に動作することを確認."""
        base_url = "https://example.com/docs"
        page1_html = """
        <html>
        <body>
            <h1>Page 1</h1>
            <a href="https://example.com/docs/page2">Page 2</a>
        </body>
        </html>
        """
        page2_html = "<html><body><h1>Page 2</h1></body></html>"
        
        # 複数のレスポンスをモック
        def create_mock_response(html):
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=html)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            return mock_response
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            
            def mock_get(url, **kwargs):
                if "page2" in url:
                    return create_mock_response(page2_html)
                else:
                    return create_mock_response(page1_html)
            
            mock_session.get = mock_get
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            # クロールを実行（max_depth=1でリンク先も取得）
            file_paths = await crawler.crawl(base_url, max_depth=1, doc_type="test")
            
            # 2ページがクロールされることを確認
            assert len(file_paths) == 2
    
    @pytest.mark.asyncio
    async def test_crawl_respects_max_depth(self, crawler):
        """最大深度が正しく適用されることを確認."""
        base_url = "https://example.com/docs"
        
        # 深い階層のリンク構造を作成
        page1_html = '<html><body><a href="https://example.com/docs/page2">Page 2</a></body></html>'
        page2_html = '<html><body><a href="https://example.com/docs/page3">Page 3</a></body></html>'
        page3_html = '<html><body><h1>Page 3</h1></body></html>'
        
        def create_mock_response(html):
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=html)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            return mock_response
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            
            def mock_get(url, **kwargs):
                if "page3" in url:
                    return create_mock_response(page3_html)
                elif "page2" in url:
                    return create_mock_response(page2_html)
                else:
                    return create_mock_response(page1_html)
            
            mock_session.get = mock_get
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            # max_depth=1でクロール（page1とpage2のみ）
            file_paths = await crawler.crawl(base_url, max_depth=1, doc_type="test")
            
            # page3は深度2なので取得されない
            assert len(file_paths) == 2
    
    @pytest.mark.asyncio
    async def test_crawl_avoids_duplicate_visits(self, crawler):
        """同じURLが複数回訪問されないことを確認."""
        base_url = "https://example.com/docs"
        
        # 循環参照を含むHTML
        page1_html = """
        <html><body>
            <a href="https://example.com/docs/page2">Page 2</a>
            <a href="https://example.com/docs/page3">Page 3</a>
        </body></html>
        """
        page2_html = '<html><body><a href="https://example.com/docs/page3">Page 3</a></body></html>'
        page3_html = '<html><body><a href="https://example.com/docs">Back to Page 1</a></body></html>'
        
        call_count = {"page1": 0, "page2": 0, "page3": 0}
        
        def create_mock_response(html, url):
            if "page3" in url:
                call_count["page3"] += 1
            elif "page2" in url:
                call_count["page2"] += 1
            else:
                call_count["page1"] += 1
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=html)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            return mock_response
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            
            def mock_get(url, **kwargs):
                if "page3" in url:
                    return create_mock_response(page3_html, url)
                elif "page2" in url:
                    return create_mock_response(page2_html, url)
                else:
                    return create_mock_response(page1_html, url)
            
            mock_session.get = mock_get
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            # クロールを実行
            file_paths = await crawler.crawl(base_url, max_depth=2, doc_type="test")
            
            # 各ページが1回だけ訪問されることを確認
            assert call_count["page1"] == 1
            assert call_count["page2"] == 1
            assert call_count["page3"] == 1
            assert len(file_paths) == 3
    
    @pytest.mark.asyncio
    async def test_crawl_continues_on_error(self, crawler):
        """エラーが発生しても他のページのクロールが継続されることを確認."""
        base_url = "https://example.com/docs"
        
        page1_html = """
        <html><body>
            <a href="https://example.com/docs/page2">Page 2</a>
            <a href="https://example.com/docs/page3">Page 3</a>
        </body></html>
        """
        page3_html = '<html><body><h1>Page 3</h1></body></html>'
        
        def create_mock_response(html, status=200):
            mock_response = AsyncMock()
            mock_response.status = status
            if status == 200:
                mock_response.text = AsyncMock(return_value=html)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            return mock_response
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            
            def mock_get(url, **kwargs):
                if "page2" in url:
                    # page2でエラーを発生させる
                    return create_mock_response("", status=404)
                elif "page3" in url:
                    return create_mock_response(page3_html)
                else:
                    return create_mock_response(page1_html)
            
            mock_session.get = mock_get
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            # クロールを実行
            file_paths = await crawler.crawl(base_url, max_depth=1, doc_type="test")
            
            # page2はエラーだが、page1とpage3は正常に取得される
            assert len(file_paths) == 2
    
    @pytest.mark.asyncio
    async def test_crawl_infers_doc_type_from_url_config(self, crawler):
        """URL設定からdoc_typeが推測されることを確認."""
        test_url = "https://docs.arduino.cc/"
        test_html = "<html><body><h1>Arduino Docs</h1></body></html>"
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=test_html)
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            # doc_typeを指定せずにクロール
            file_paths = await crawler.crawl(test_url, max_depth=0)
            
            # ファイルが作成されることを確認
            assert len(file_paths) == 1
            
            # ファイル内容を確認してdoc_typeが設定されていることを確認
            with open(file_paths[0], 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert "doc_type:" in content
