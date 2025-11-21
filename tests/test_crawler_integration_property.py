"""APICrawlerのCloudflare統合に関するプロパティベーステスト."""
import asyncio
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from src.crawler import APICrawler, CrawlerError
from src.cloudflare_renderer import CloudflareRenderer
from src.page_classifier import PageClassifier
import aiohttp


# テスト用のストラテジー
@st.composite
def cloudflare_error_responses(draw):
    """Cloudflareエラーレスポンスを生成するストラテジー."""
    error_types = [
        ("timeout", asyncio.TimeoutError()),
        ("rate_limit", CrawlerError("Cloudflare rate limit exceeded")),
        ("auth_error", CrawlerError("Cloudflare authentication failed (401)")),
        ("api_error", CrawlerError("Cloudflare API error: Unknown error")),
    ]
    return draw(st.sampled_from(error_types))


@st.composite
def dynamic_html_content(draw):
    """動的ページのHTMLコンテンツを生成するストラテジー."""
    frameworks = ["React", "Vue", "Angular", "Next.js", "Nuxt"]
    framework = draw(st.sampled_from(frameworks))
    
    # フレームワーク固有のマーカーを含むHTMLを生成
    framework_markers = {
        "React": '<div id="root"></div>',
        "Vue": '<div id="app" v-cloak></div>',
        "Angular": '<div ng-app="myApp"></div>',
        "Next.js": '<script id="__NEXT_DATA__"></script>',
        "Nuxt": '<script>window.__NUXT__={}</script>',
    }
    
    # 最小限のテキストコンテンツ（10%未満）
    minimal_text = draw(st.text(min_size=1, max_size=50))
    marker = framework_markers[framework]
    
    # HTMLサイズに対してテキストが少ないHTMLを生成
    html = f"""
    <html>
    <head>
        <script src="framework.js"></script>
        <style>/* Large CSS content */{"a" * 1000}</style>
    </head>
    <body>
        {marker}
        <p>{minimal_text}</p>
    </body>
    </html>
    """
    
    return html


@st.composite
def static_html_content(draw):
    """静的ページのHTMLコンテンツを生成するストラテジー."""
    # 実質的なテキストコンテンツを含むHTML
    text_content = draw(st.text(min_size=100, max_size=500))
    
    html = f"""
    <html>
    <head><title>Static Page</title></head>
    <body>
        <h1>Static Content</h1>
        <p>{text_content}</p>
        <p>More content here</p>
    </body>
    </html>
    """
    
    return html


@pytest.fixture
def temp_config_dir(tmp_path):
    """一時的な設定ディレクトリを作成."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    url_config = {
        "apis": {
            "test_api": {
                "name": "Test API",
                "url": "https://example.com/",
                "description": "Test API"
            }
        }
    }
    
    url_config_path = config_dir / "url_config.json"
    with open(url_config_path, 'w', encoding='utf-8') as f:
        json.dump(url_config, f, ensure_ascii=False, indent=2)
    
    return config_dir


def create_crawler_with_cloudflare(tmp_path):
    """Cloudflare統合を有効にしたクローラーインスタンスを作成するヘルパー関数."""
    # 一時的な設定ディレクトリを作成
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    
    url_config = {
        "apis": {
            "test_api": {
                "name": "Test API",
                "url": "https://example.com/",
                "description": "Test API"
            }
        }
    }
    
    url_config_path = config_dir / "url_config.json"
    with open(url_config_path, 'w', encoding='utf-8') as f:
        json.dump(url_config, f, ensure_ascii=False, indent=2)
    
    docs_path = tmp_path / "docs"
    docs_path.mkdir(exist_ok=True)
    
    crawler = APICrawler(docs_path=str(docs_path), url_config_path=str(url_config_path))
    
    # Cloudflare Rendererをモックで設定
    crawler.cloudflare_renderer = CloudflareRenderer(
        api_token="test_token",
        account_id="test_account"
    )
    
    return crawler


class TestCloudflareIntegrationProperties:
    """Cloudflare統合のプロパティベーステスト."""
    
    @pytest.mark.asyncio
    async def test_property_4_error_fallback_timeout(self, tmp_path):
        """
        Feature: enhanced-document-processing, Property 4: エラー時のフォールバック（タイムアウト）
        
        Cloudflare APIがタイムアウトした場合、システムはBeautifulSoup処理にフォールバックする
        
        検証: 要件 1.5, 5.3, 6.4
        """
        # クローラーを作成
        crawler_with_cloudflare = create_crawler_with_cloudflare(tmp_path)
        
        url = "https://example.com/test"
        
        # 動的ページのHTMLを生成（Cloudflareが使用されるべき）
        dynamic_html = """
        <html>
        <head>
            <script src="react.js"></script>
            <style>/* CSS */{"a" * 1000}</style>
        </head>
        <body>
            <div id="root"></div>
            <p>Minimal text</p>
        </body>
        </html>
        """
        
        # Cloudflare Rendererがタイムアウトエラーを発生させるようにモック
        with patch.object(
            crawler_with_cloudflare.cloudflare_renderer,
            'render_to_markdown',
            side_effect=CrawlerError("Timeout after 3 attempts")
        ):
            # aiohttpのモックを作成（BeautifulSoupフォールバック用）
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=dynamic_html)
            
            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # ページを取得
            result = await crawler_with_cloudflare._fetch_page(url, mock_session)
            
            # プロパティ検証:
            # 1. エラーが発生してもCrawlerErrorが再スローされない（フォールバック成功）
            # 2. BeautifulSoupで処理されたHTML（元のHTML）が返される
            assert result == dynamic_html
            
            # Cloudflare Rendererが呼び出されたことを確認
            crawler_with_cloudflare.cloudflare_renderer.render_to_markdown.assert_called_once_with(url)
    
    @pytest.mark.asyncio
    async def test_property_4_error_fallback_rate_limit(self, tmp_path):
        """
        Feature: enhanced-document-processing, Property 4: エラー時のフォールバック（レート制限）
        
        Cloudflare APIがレート制限エラーを返した場合、システムはBeautifulSoup処理にフォールバックする
        
        検証: 要件 1.5, 5.3, 6.4
        """
        # クローラーを作成
        crawler_with_cloudflare = create_crawler_with_cloudflare(tmp_path)
        
        url = "https://example.com/test2"
        
        # 動的ページのHTMLを生成
        dynamic_html = """
        <html>
        <head>
            <script src="vue.js"></script>
            <style>/* CSS */{"a" * 1000}</style>
        </head>
        <body>
            <div id="app" v-cloak></div>
            <p>Text</p>
        </body>
        </html>
        """
        
        # Cloudflare Rendererがレート制限エラーを発生させるようにモック
        with patch.object(
            crawler_with_cloudflare.cloudflare_renderer,
            'render_to_markdown',
            side_effect=CrawlerError("Cloudflare rate limit exceeded")
        ):
            # aiohttpのモックを作成
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=dynamic_html)
            
            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # ページを取得
            result = await crawler_with_cloudflare._fetch_page(url, mock_session)
            
            # プロパティ検証: BeautifulSoupで処理されたHTMLが返される
            assert result == dynamic_html
            
            # Cloudflare Rendererが呼び出されたことを確認
            crawler_with_cloudflare.cloudflare_renderer.render_to_markdown.assert_called_once_with(url)
    
    @pytest.mark.asyncio
    async def test_property_8_rate_limit_respect(self, tmp_path):
        """
        Feature: enhanced-document-processing, Property 8: レート制限遵守
        
        Cloudflare Browser Rendering使用時に、既存のレート制限遅延設定が尊重される
        
        検証: 要件 6.5
        """
        # クローラーを作成
        crawler_with_cloudflare = create_crawler_with_cloudflare(tmp_path)
        
        # レート制限遅延を設定
        rate_limit_delay = 0.2
        crawler_with_cloudflare.rate_limit_delay = rate_limit_delay
        
        url = "https://example.com/test3"
        
        # 動的ページのHTMLを生成
        dynamic_html = """
        <html>
        <head>
            <script src="vue.js"></script>
            <style>/* CSS */{"a" * 1000}</style>
        </head>
        <body>
            <div id="app" v-cloak></div>
            <p>Text</p>
        </body>
        </html>
        """
        
        markdown_result = "# Rendered Content\n\nThis is rendered markdown."
        
        # Cloudflare Rendererをモック
        with patch.object(
            crawler_with_cloudflare.cloudflare_renderer,
            'render_to_markdown',
            return_value=markdown_result
        ):
            # aiohttpのモックを作成
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=dynamic_html)
            
            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # 時間計測
            import time
            start_time = time.time()
            
            # 2回連続でページを取得
            await crawler_with_cloudflare._fetch_page(url, mock_session)
            await crawler_with_cloudflare._fetch_page(url, mock_session)
            
            elapsed_time = time.time() - start_time
            
            # プロパティ検証:
            # レート制限遅延が尊重されている（2回分の遅延が適用されている）
            # 多少の誤差を許容（0.9倍）
            expected_min_time = rate_limit_delay * 2 * 0.9
            assert elapsed_time >= expected_min_time, (
                f"Rate limit delay not respected: "
                f"expected >= {expected_min_time}s, got {elapsed_time}s"
            )


class TestCloudflareIntegrationEdgeCases:
    """Cloudflare統合のエッジケースのテスト."""
    
    @pytest.mark.asyncio
    async def test_cloudflare_disabled_fallback(self, temp_config_dir, tmp_path):
        """Cloudflareが無効な場合、BeautifulSoupが使用されることを確認."""
        docs_path = tmp_path / "docs"
        docs_path.mkdir()
        url_config_path = temp_config_dir / "url_config.json"
        
        # Cloudflare Rendererなしのクローラー
        crawler = APICrawler(docs_path=str(docs_path), url_config_path=str(url_config_path))
        crawler.cloudflare_renderer = None
        
        url = "https://example.com/test"
        dynamic_html = """
        <html>
        <head><script src="react.js"></script></head>
        <body><div id="root"></div><p>Text</p></body>
        </html>
        """
        
        # aiohttpのモックを作成
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=dynamic_html)
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # ページを取得
        result = await crawler._fetch_page(url, mock_session)
        
        # BeautifulSoupで処理されたHTML（元のHTML）が返される
        assert result == dynamic_html
    
    @pytest.mark.asyncio
    async def test_static_page_skips_cloudflare(self, tmp_path):
        """静的ページの場合、Cloudflareがスキップされることを確認."""
        # クローラーを作成
        crawler_with_cloudflare = create_crawler_with_cloudflare(tmp_path)
        
        url = "https://example.com/static"
        static_html = """
        <html>
        <head><title>Static Page</title></head>
        <body>
            <h1>Static Content</h1>
            <p>This is a static page with lots of text content.</p>
            <p>More paragraphs here.</p>
            <p>Even more content to ensure high text ratio.</p>
        </body>
        </html>
        """
        
        # Cloudflare Rendererをモック（呼び出されないはず）
        with patch.object(
            crawler_with_cloudflare.cloudflare_renderer,
            'render_to_markdown',
            side_effect=Exception("Should not be called")
        ):
            # aiohttpのモックを作成
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=static_html)
            
            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # ページを取得
            result = await crawler_with_cloudflare._fetch_page(url, mock_session)
            
            # 静的ページなのでCloudflareは呼び出されず、元のHTMLが返される
            assert result == static_html
            
            # Cloudflare Rendererが呼び出されていないことを確認
            crawler_with_cloudflare.cloudflare_renderer.render_to_markdown.assert_not_called()
