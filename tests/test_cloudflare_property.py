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



class TestRateLimitWaitingProperty:
    """
    プロパティ 9: レート制限待機
    
    **Feature: enhanced-document-processing, Property 9: レート制限待機**
    **検証: 要件 5.1**
    
    任意のCloudflare APIレート制限エラーに対して、システムは再試行前に待機する
    """
    
    @given(
        api_token=st.text(min_size=1, max_size=100),
        account_id=st.text(min_size=1, max_size=100),
        url=st.text(min_size=10, max_size=200)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_rate_limit_waiting_property(
        self,
        api_token: str,
        account_id: str,
        url: str
    ):
        """
        プロパティ: レート制限エラー時に再試行前に待機する.
        
        Args:
            api_token: ランダムに生成されたAPI Token
            account_id: ランダムに生成されたAccount ID
            url: ランダムに生成されたURL
        """
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # レート制限エラーを返すモックレスポンスを作成
        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.json = AsyncMock(return_value={
            "success": False,
            "errors": [{"message": "Rate limit exceeded"}]
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            # asyncio.sleepをモックして待機時間を記録
            sleep_times = []
            
            async def mock_sleep(duration):
                sleep_times.append(duration)
            
            with patch('asyncio.sleep', side_effect=mock_sleep):
                try:
                    await renderer.render_to_markdown(url, timeout=30)
                except Exception:
                    # エラーは期待される
                    pass
                
                # プロパティ: レート制限エラー時に少なくとも1回は待機する
                assert len(sleep_times) > 0, (
                    f"Expected at least one sleep call for rate limit error, "
                    f"but got {len(sleep_times)} calls"
                )
                
                # プロパティ: 各待機時間は正の値である
                for i, sleep_time in enumerate(sleep_times):
                    assert sleep_time > 0, (
                        f"Expected positive sleep time at index {i}, "
                        f"but got {sleep_time}"
                    )
    
    @pytest.mark.asyncio
    async def test_rate_limit_waiting_first_retry(self):
        """エッジケース: 最初のリトライ前に待機する."""
        api_token = "test_token"
        account_id = "test_account"
        url = "https://example.com"
        
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # レート制限エラーを返す
        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.json = AsyncMock(return_value={
            "success": False,
            "errors": [{"message": "Rate limit exceeded"}]
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            sleep_times = []
            
            async def mock_sleep(duration):
                sleep_times.append(duration)
            
            with patch('asyncio.sleep', side_effect=mock_sleep):
                try:
                    await renderer.render_to_markdown(url, timeout=30)
                except Exception:
                    pass
                
                # 最初のリトライ前に待機することを確認
                assert len(sleep_times) >= 1
                # 最初の待機時間は1秒（INITIAL_BACKOFF）
                assert sleep_times[0] == 1.0
    
    @pytest.mark.asyncio
    async def test_rate_limit_waiting_multiple_retries(self):
        """エッジケース: 複数回のリトライで待機する."""
        api_token = "test_token"
        account_id = "test_account"
        url = "https://example.com"
        
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # 常にレート制限エラーを返す
        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.json = AsyncMock(return_value={
            "success": False,
            "errors": [{"message": "Rate limit exceeded"}]
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            sleep_times = []
            
            async def mock_sleep(duration):
                sleep_times.append(duration)
            
            with patch('asyncio.sleep', side_effect=mock_sleep):
                try:
                    await renderer.render_to_markdown(url, timeout=30)
                except Exception:
                    pass
                
                # MAX_RETRIES - 1回の待機が発生する（最後のリトライ後は待機しない）
                expected_sleep_count = renderer.MAX_RETRIES - 1
                assert len(sleep_times) == expected_sleep_count, (
                    f"Expected {expected_sleep_count} sleep calls, "
                    f"but got {len(sleep_times)}"
                )
    
    @given(
        api_token=st.text(min_size=1, max_size=100),
        account_id=st.text(min_size=1, max_size=100),
        url=st.text(min_size=10, max_size=200),
        retry_count=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_rate_limit_waiting_before_each_retry(
        self,
        api_token: str,
        account_id: str,
        url: str,
        retry_count: int
    ):
        """
        プロパティ: 各リトライの前に待機する.
        
        Args:
            api_token: ランダムに生成されたAPI Token
            account_id: ランダムに生成されたAccount ID
            url: ランダムに生成されたURL
            retry_count: リトライ回数
        """
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # retry_count回失敗した後、成功するモックを作成
        call_count = [0]
        
        def mock_post(*args, **kwargs):
            call_count[0] += 1
            mock_response = MagicMock()
            
            if call_count[0] <= retry_count:
                # レート制限エラー
                mock_response.status = 429
                mock_response.json = AsyncMock(return_value={
                    "success": False,
                    "errors": [{"message": "Rate limit exceeded"}]
                })
            else:
                # 成功
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={
                    "success": True,
                    "result": {
                        "markdown": "# Success",
                        "url": url,
                        "timestamp": "2025-11-21T10:30:00Z"
                    }
                })
            
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_response)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            return mock_ctx
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post = mock_post
            
            sleep_times = []
            
            async def mock_sleep(duration):
                sleep_times.append(duration)
            
            with patch('asyncio.sleep', side_effect=mock_sleep):
                try:
                    await renderer.render_to_markdown(url, timeout=30)
                except Exception:
                    pass
                
                # プロパティ: retry_count回のリトライ前に待機する
                # （最後のリトライが成功した場合、その後は待機しない）
                if call_count[0] <= renderer.MAX_RETRIES:
                    expected_sleep_count = min(retry_count, renderer.MAX_RETRIES - 1)
                    assert len(sleep_times) >= expected_sleep_count, (
                        f"Expected at least {expected_sleep_count} sleep calls "
                        f"for {retry_count} retries, but got {len(sleep_times)}"
                    )


class TestExponentialBackoffProperty:
    """
    プロパティ 10: 指数バックオフ
    
    **Feature: enhanced-document-processing, Property 10: 指数バックオフ**
    **検証: 要件 5.2**
    
    任意のレート制限後の再試行に対して、システムは指数バックオフ戦略を使用する
    （1秒、2秒、4秒...）
    """
    
    @given(
        api_token=st.text(min_size=1, max_size=100),
        account_id=st.text(min_size=1, max_size=100),
        url=st.text(min_size=10, max_size=200)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_exponential_backoff_property(
        self,
        api_token: str,
        account_id: str,
        url: str
    ):
        """
        プロパティ: レート制限エラー時に指数バックオフを使用する.
        
        Args:
            api_token: ランダムに生成されたAPI Token
            account_id: ランダムに生成されたAccount ID
            url: ランダムに生成されたURL
        """
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # 常にレート制限エラーを返す
        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.json = AsyncMock(return_value={
            "success": False,
            "errors": [{"message": "Rate limit exceeded"}]
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            sleep_times = []
            
            async def mock_sleep(duration):
                sleep_times.append(duration)
            
            with patch('asyncio.sleep', side_effect=mock_sleep):
                try:
                    await renderer.render_to_markdown(url, timeout=30)
                except Exception:
                    pass
                
                # プロパティ: 待機時間が指数的に増加する
                if len(sleep_times) >= 2:
                    for i in range(len(sleep_times) - 1):
                        # 次の待機時間は前の待機時間の2倍である
                        expected_ratio = 2.0
                        actual_ratio = sleep_times[i + 1] / sleep_times[i]
                        
                        assert abs(actual_ratio - expected_ratio) < 0.01, (
                            f"Expected exponential backoff with ratio ~{expected_ratio}, "
                            f"but got ratio {actual_ratio} between "
                            f"sleep_times[{i}]={sleep_times[i]} and "
                            f"sleep_times[{i+1}]={sleep_times[i+1]}"
                        )
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_sequence(self):
        """エッジケース: 指数バックオフのシーケンスが正しい（1秒、2秒、4秒）."""
        api_token = "test_token"
        account_id = "test_account"
        url = "https://example.com"
        
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # 常にレート制限エラーを返す
        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.json = AsyncMock(return_value={
            "success": False,
            "errors": [{"message": "Rate limit exceeded"}]
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            sleep_times = []
            
            async def mock_sleep(duration):
                sleep_times.append(duration)
            
            with patch('asyncio.sleep', side_effect=mock_sleep):
                try:
                    await renderer.render_to_markdown(url, timeout=30)
                except Exception:
                    pass
                
                # 期待される指数バックオフシーケンス: 1.0, 2.0
                # （MAX_RETRIES=3なので、2回の待機が発生）
                expected_sequence = [1.0, 2.0]
                
                assert len(sleep_times) == len(expected_sequence), (
                    f"Expected {len(expected_sequence)} sleep calls, "
                    f"but got {len(sleep_times)}"
                )
                
                for i, (expected, actual) in enumerate(zip(expected_sequence, sleep_times)):
                    assert actual == expected, (
                        f"Expected sleep_times[{i}]={expected}, "
                        f"but got {actual}"
                    )
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_initial_value(self):
        """エッジケース: 最初の待機時間はINITIAL_BACKOFF（1秒）."""
        api_token = "test_token"
        account_id = "test_account"
        url = "https://example.com"
        
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # レート制限エラーを返す
        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.json = AsyncMock(return_value={
            "success": False,
            "errors": [{"message": "Rate limit exceeded"}]
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            sleep_times = []
            
            async def mock_sleep(duration):
                sleep_times.append(duration)
            
            with patch('asyncio.sleep', side_effect=mock_sleep):
                try:
                    await renderer.render_to_markdown(url, timeout=30)
                except Exception:
                    pass
                
                # 最初の待機時間はINITIAL_BACKOFF
                assert sleep_times[0] == renderer.INITIAL_BACKOFF, (
                    f"Expected first sleep time to be {renderer.INITIAL_BACKOFF}, "
                    f"but got {sleep_times[0]}"
                )
    
    @given(
        api_token=st.text(min_size=1, max_size=100),
        account_id=st.text(min_size=1, max_size=100),
        url=st.text(min_size=10, max_size=200),
        initial_backoff=st.floats(min_value=0.1, max_value=5.0)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_exponential_backoff_formula(
        self,
        api_token: str,
        account_id: str,
        url: str,
        initial_backoff: float
    ):
        """
        プロパティ: 指数バックオフの計算式が正しい（backoff = initial * 2^attempt）.
        
        Args:
            api_token: ランダムに生成されたAPI Token
            account_id: ランダムに生成されたAccount ID
            url: ランダムに生成されたURL
            initial_backoff: 初期バックオフ時間
        """
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # INITIAL_BACKOFFを一時的に変更
        original_backoff = renderer.INITIAL_BACKOFF
        renderer.INITIAL_BACKOFF = initial_backoff
        
        try:
            # 常にレート制限エラーを返す
            mock_response = MagicMock()
            mock_response.status = 429
            mock_response.json = AsyncMock(return_value={
                "success": False,
                "errors": [{"message": "Rate limit exceeded"}]
            })
            
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = MagicMock()
                mock_session_class.return_value.__aenter__.return_value = mock_session
                mock_session.post.return_value.__aenter__.return_value = mock_response
                
                sleep_times = []
                
                async def mock_sleep(duration):
                    sleep_times.append(duration)
                
                with patch('asyncio.sleep', side_effect=mock_sleep):
                    try:
                        await renderer.render_to_markdown(url, timeout=30)
                    except Exception:
                        pass
                    
                    # プロパティ: 各待機時間が指数バックオフの計算式に従う
                    for i, sleep_time in enumerate(sleep_times):
                        expected_time = initial_backoff * (2 ** i)
                        
                        # 浮動小数点の比較には許容誤差を使用
                        assert abs(sleep_time - expected_time) < 0.01, (
                            f"Expected sleep_times[{i}]={expected_time} "
                            f"(initial_backoff * 2^{i}), but got {sleep_time}"
                        )
        finally:
            # INITIAL_BACKOFFを元に戻す
            renderer.INITIAL_BACKOFF = original_backoff
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_max_retries(self):
        """エッジケース: MAX_RETRIES回のリトライ後は待機しない."""
        api_token = "test_token"
        account_id = "test_account"
        url = "https://example.com"
        
        renderer = CloudflareRenderer(api_token=api_token, account_id=account_id)
        
        # 常にレート制限エラーを返す
        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.json = AsyncMock(return_value={
            "success": False,
            "errors": [{"message": "Rate limit exceeded"}]
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            sleep_times = []
            
            async def mock_sleep(duration):
                sleep_times.append(duration)
            
            with patch('asyncio.sleep', side_effect=mock_sleep):
                try:
                    await renderer.render_to_markdown(url, timeout=30)
                except Exception:
                    pass
                
                # MAX_RETRIES - 1回の待機が発生する
                expected_sleep_count = renderer.MAX_RETRIES - 1
                assert len(sleep_times) == expected_sleep_count, (
                    f"Expected {expected_sleep_count} sleep calls "
                    f"(MAX_RETRIES - 1), but got {len(sleep_times)}"
                )
