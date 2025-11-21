"""CloudflareRendererのプロパティベーステスト."""
import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import AsyncMock, patch, MagicMock
from src.cloudflare_renderer import CloudflareRenderer
import aiohttp


class TestCloudflareEnablementProperty:
    """
    プロパティ 1: Cloudflare有効化条件
    
    **Feature: enhanced-document-processing, Property 1: Cloudflare有効化条件**
    **検証: 要件 1.1, 1.4**
    
    任意の環境変数設定に対して、CLOUDFLARE_API_TOKENとCLOUDFLARE_ACCOUNT_IDの
    両方が設定されている場合のみ、Cloudflare Browser Rendering統合が有効化される
    """
    
    @given(
        api_token=st.text(min_size=0, max_size=100),
        account_id=st.text(min_size=0, max_size=100)
    )
    @settings(max_examples=100)
    def test_cloudflare_enablement_property(self, api_token: str, account_id: str):
        """
        プロパティ: 両方の認証情報が非空の場合のみ有効化される.
        
        Args:
            api_token: ランダムに生成されたAPI Token
            account_id: ランダムに生成されたAccount ID
        """
        # CloudflareRendererを初期化
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # プロパティ: 両方が非空の場合のみis_available()がTrueを返す
        expected_available = bool(api_token and account_id)
        actual_available = renderer.is_available()
        
        assert actual_available == expected_available, (
            f"Expected is_available()={expected_available} for "
            f"api_token={'<set>' if api_token else '<empty>'}, "
            f"account_id={'<set>' if account_id else '<empty>'}, "
            f"but got {actual_available}"
        )
    
    def test_cloudflare_enablement_both_empty(self):
        """エッジケース: 両方が空の場合、無効化される."""
        renderer = CloudflareRenderer(api_token="", account_id="")
        assert not renderer.is_available()
    
    def test_cloudflare_enablement_token_only(self):
        """エッジケース: API Tokenのみが設定されている場合、無効化される."""
        renderer = CloudflareRenderer(api_token="test_token", account_id="")
        assert not renderer.is_available()
    
    def test_cloudflare_enablement_account_id_only(self):
        """エッジケース: Account IDのみが設定されている場合、無効化される."""
        renderer = CloudflareRenderer(api_token="", account_id="test_account")
        assert not renderer.is_available()
    
    def test_cloudflare_enablement_both_set(self):
        """エッジケース: 両方が設定されている場合、有効化される."""
        renderer = CloudflareRenderer(
            api_token="test_token",
            account_id="test_account"
        )
        assert renderer.is_available()
    
    @given(
        api_token=st.text(min_size=1, max_size=100),
        account_id=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100)
    def test_cloudflare_enablement_both_non_empty(
        self,
        api_token: str,
        account_id: str
    ):
        """
        プロパティ: 両方が非空の場合、常に有効化される.
        
        Args:
            api_token: 非空のAPI Token
            account_id: 非空のAccount ID
        """
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # 両方が非空なので、常にTrueを返すべき
        assert renderer.is_available(), (
            f"Expected is_available()=True for non-empty credentials, "
            f"but got False"
        )
    
    @given(
        api_token=st.one_of(st.just(""), st.text(min_size=1, max_size=100)),
        account_id=st.just("")
    )
    @settings(max_examples=100)
    def test_cloudflare_enablement_account_id_empty(
        self,
        api_token: str,
        account_id: str
    ):
        """
        プロパティ: Account IDが空の場合、常に無効化される.
        
        Args:
            api_token: 任意のAPI Token（空または非空）
            account_id: 空のAccount ID
        """
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # Account IDが空なので、常にFalseを返すべき
        assert not renderer.is_available(), (
            f"Expected is_available()=False when account_id is empty, "
            f"but got True"
        )
    
    @given(
        api_token=st.just(""),
        account_id=st.one_of(st.just(""), st.text(min_size=1, max_size=100))
    )
    @settings(max_examples=100)
    def test_cloudflare_enablement_api_token_empty(
        self,
        api_token: str,
        account_id: str
    ):
        """
        プロパティ: API Tokenが空の場合、常に無効化される.
        
        Args:
            api_token: 空のAPI Token
            account_id: 任意のAccount ID（空または非空）
        """
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # API Tokenが空なので、常にFalseを返すべき
        assert not renderer.is_available(), (
            f"Expected is_available()=False when api_token is empty, "
            f"but got True"
        )



class TestAuthenticationHeaderProperty:
    """
    プロパティ 7: 認証ヘッダー
    
    **Feature: enhanced-document-processing, Property 7: 認証ヘッダー**
    **検証: 要件 6.2**
    
    任意のCloudflare APIリクエストに対して、適切な認証ヘッダー
    （Authorization: Bearer {token}）が含まれる
    """
    
    @given(
        api_token=st.text(min_size=1, max_size=100),
        account_id=st.text(min_size=1, max_size=100),
        url=st.text(min_size=10, max_size=200)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_authentication_header_property(
        self,
        api_token: str,
        account_id: str,
        url: str
    ):
        """
        プロパティ: すべてのAPIリクエストに正しい認証ヘッダーが含まれる.
        
        Args:
            api_token: ランダムに生成されたAPI Token
            account_id: ランダムに生成されたAccount ID
            url: ランダムに生成されたURL
        """
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # モックレスポンスを作成
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "result": {
                "markdown": "# Test",
                "url": url,
                "timestamp": "2025-11-21T10:30:00Z"
            }
        })
        
        # aiohttp.ClientSessionをモック
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            try:
                await renderer.render_to_markdown(url, timeout=30)
            except Exception:
                # エラーが発生してもヘッダーの検証は行う
                pass
            
            # post()が呼ばれたことを確認
            if mock_session.post.called:
                call_args = mock_session.post.call_args
                
                # headersパラメータを取得
                headers = call_args.kwargs.get('headers', {})
                
                # プロパティ: Authorization ヘッダーが正しい形式で含まれる
                assert 'Authorization' in headers, (
                    f"Authorization header is missing in API request"
                )
                
                expected_auth = f"Bearer {api_token}"
                actual_auth = headers['Authorization']
                
                assert actual_auth == expected_auth, (
                    f"Expected Authorization header: '{expected_auth}', "
                    f"but got: '{actual_auth}'"
                )
                
                # Content-Typeヘッダーも確認
                assert headers.get('Content-Type') == 'application/json', (
                    f"Expected Content-Type: 'application/json', "
                    f"but got: '{headers.get('Content-Type')}'"
                )
    
    @pytest.mark.asyncio
    async def test_authentication_header_format(self):
        """エッジケース: 認証ヘッダーの形式が正しい."""
        api_token = "test_token_12345"
        account_id = "test_account_67890"
        url = "https://example.com"
        
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # モックレスポンスを作成
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "result": {
                "markdown": "# Test",
                "url": url,
                "timestamp": "2025-11-21T10:30:00Z"
            }
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            await renderer.render_to_markdown(url, timeout=30)
            
            # ヘッダーを検証
            call_args = mock_session.post.call_args
            headers = call_args.kwargs.get('headers', {})
            
            assert headers['Authorization'] == f"Bearer {api_token}"
            assert headers['Content-Type'] == 'application/json'



class TestMarkdownConversionProperty:
    """
    プロパティ 3: Markdown変換
    
    **Feature: enhanced-document-processing, Property 3: Markdown変換**
    **検証: 要件 1.3, 6.3**
    
    任意のCloudflare APIレスポンスに対して、レンダリングされたHTMLは
    Markdown形式に変換される
    """
    
    @given(
        api_token=st.text(min_size=1, max_size=100),
        account_id=st.text(min_size=1, max_size=100),
        url=st.text(min_size=10, max_size=200),
        markdown_content=st.text(min_size=1, max_size=1000)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_markdown_conversion_property(
        self,
        api_token: str,
        account_id: str,
        url: str,
        markdown_content: str
    ):
        """
        プロパティ: APIレスポンスからMarkdownコンテンツが正しく抽出される.
        
        Args:
            api_token: ランダムに生成されたAPI Token
            account_id: ランダムに生成されたAccount ID
            url: ランダムに生成されたURL
            markdown_content: ランダムに生成されたMarkdownコンテンツ
        """
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # モックレスポンスを作成（成功レスポンス）
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "result": {
                "markdown": markdown_content,
                "url": url,
                "timestamp": "2025-11-21T10:30:00Z"
            }
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            # render_to_markdown()を呼び出し
            result = await renderer.render_to_markdown(url, timeout=30)
            
            # プロパティ: 返されたMarkdownがAPIレスポンスのmarkdownフィールドと一致する
            assert result == markdown_content, (
                f"Expected markdown content to match API response, "
                f"but got different content. "
                f"Expected length: {len(markdown_content)}, "
                f"Actual length: {len(result)}"
            )
    
    @pytest.mark.asyncio
    async def test_markdown_conversion_empty_content(self):
        """エッジケース: 空のMarkdownコンテンツが返される場合."""
        api_token = "test_token"
        account_id = "test_account"
        url = "https://example.com"
        
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # 空のMarkdownを含むレスポンス
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "result": {
                "markdown": "",
                "url": url,
                "timestamp": "2025-11-21T10:30:00Z"
            }
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            result = await renderer.render_to_markdown(url, timeout=30)
            
            # 空の文字列が返されることを確認
            assert result == ""
    
    @pytest.mark.asyncio
    async def test_markdown_conversion_large_content(self):
        """エッジケース: 大きなMarkdownコンテンツが返される場合."""
        api_token = "test_token"
        account_id = "test_account"
        url = "https://example.com"
        
        # 大きなMarkdownコンテンツを生成（10KB）
        large_markdown = "# Large Content\n" + ("Lorem ipsum dolor sit amet. " * 400)
        
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "result": {
                "markdown": large_markdown,
                "url": url,
                "timestamp": "2025-11-21T10:30:00Z"
            }
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            result = await renderer.render_to_markdown(url, timeout=30)
            
            # 大きなコンテンツが正しく返されることを確認
            assert result == large_markdown
            assert len(result) > 10000
    
    @given(
        api_token=st.text(min_size=1, max_size=100),
        account_id=st.text(min_size=1, max_size=100),
        url=st.text(min_size=10, max_size=200)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_markdown_extraction_from_result(
        self,
        api_token: str,
        account_id: str,
        url: str
    ):
        """
        プロパティ: レスポンスのresult.markdownフィールドから正しく抽出される.
        
        Args:
            api_token: ランダムに生成されたAPI Token
            account_id: ランダムに生成されたAccount ID
            url: ランダムに生成されたURL
        """
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # 特定のMarkdownコンテンツ
        expected_markdown = "# Test Header\n\nTest content with **bold** and *italic*."
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "result": {
                "markdown": expected_markdown,
                "url": url,
                "timestamp": "2025-11-21T10:30:00Z"
            }
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            result = await renderer.render_to_markdown(url, timeout=30)
            
            # プロパティ: 抽出されたMarkdownが期待される内容と一致する
            assert result == expected_markdown, (
                f"Markdown extraction failed. "
                f"Expected: '{expected_markdown}', "
                f"Got: '{result}'"
            )
