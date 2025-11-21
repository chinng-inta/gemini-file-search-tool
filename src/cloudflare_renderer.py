"""Cloudflare Browser Renderingを使用してWebページをレンダリングするモジュール."""
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass

import aiohttp

from src.errors import CrawlerError
from src.logging_config import get_logger

# ロガーの設定
logger = get_logger(__name__)


@dataclass
class CloudflareResponse:
    """Cloudflare APIレスポンス."""
    success: bool
    markdown: str
    url: str
    timestamp: str
    error: Optional[str] = None


class CloudflareRenderer:
    """Cloudflare Browser Rendering APIとの通信を担当するクラス."""
    
    # Cloudflare API エンドポイント
    API_ENDPOINT_TEMPLATE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering/markdown"
    
    # リトライ設定
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0  # 秒
    
    def __init__(self, api_token: str, account_id: str):
        """
        Cloudflare Rendererを初期化.
        
        Args:
            api_token: Cloudflare API Token
            account_id: Cloudflare Account ID
        """
        self.api_token = api_token
        self.account_id = account_id
        self.api_endpoint = self.API_ENDPOINT_TEMPLATE.format(account_id=account_id)
        
        logger.info(f"CloudflareRenderer initialized with account_id: {account_id}")
    
    def is_available(self) -> bool:
        """
        Cloudflare統合が利用可能かチェック.
        
        Returns:
            bool: 利用可能な場合True
        """
        return bool(self.api_token and self.account_id)

    async def render_to_markdown(
        self, 
        url: str, 
        timeout: int = 30
    ) -> str:
        """
        URLをレンダリングしてMarkdownを取得.
        
        Args:
            url: レンダリングするURL
            timeout: タイムアウト時間（秒）
            
        Returns:
            str: レンダリングされたMarkdown
            
        Raises:
            CrawlerError: レンダリングに失敗した場合
        """
        if not self.is_available():
            raise CrawlerError("Cloudflare Browser Rendering is not available")
        
        logger.info(f"Rendering URL with Cloudflare: {url}")
        
        # リトライロジック
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self._make_api_request(url, timeout)
                
                if response.success:
                    logger.info(f"Successfully rendered URL: {url} ({len(response.markdown)} bytes)")
                    return response.markdown
                else:
                    error_msg = response.error or "Unknown error"
                    logger.error(f"Cloudflare API returned error: {error_msg}")
                    raise CrawlerError(f"Cloudflare API error: {error_msg}")
                    
            except aiohttp.ClientError as e:
                logger.warning(f"Network error on attempt {attempt + 1}/{self.MAX_RETRIES}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.INITIAL_BACKOFF * (2 ** attempt)
                    logger.info(f"Retrying in {backoff} seconds...")
                    await asyncio.sleep(backoff)
                else:
                    raise CrawlerError(f"Network error after {self.MAX_RETRIES} attempts: {e}")
                    
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.MAX_RETRIES}")
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.INITIAL_BACKOFF * (2 ** attempt)
                    logger.info(f"Retrying in {backoff} seconds...")
                    await asyncio.sleep(backoff)
                else:
                    raise CrawlerError(f"Timeout after {self.MAX_RETRIES} attempts")
    
    async def _make_api_request(
        self, 
        url: str, 
        timeout: int
    ) -> CloudflareResponse:
        """
        Cloudflare APIにリクエストを送信.
        
        Args:
            url: レンダリングするURL
            timeout: タイムアウト時間（秒）
            
        Returns:
            CloudflareResponse: APIレスポンス
            
        Raises:
            aiohttp.ClientError: ネットワークエラー
            asyncio.TimeoutError: タイムアウト
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": url
        }
        
        logger.debug(f"Making Cloudflare API request to: {self.api_endpoint}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_endpoint,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                status = response.status
                logger.info(f"Cloudflare API response status: {status}")
                
                # レート制限エラー
                if status == 429:
                    logger.warning("Rate limit exceeded (429)")
                    raise CrawlerError("Cloudflare rate limit exceeded")
                
                # 認証エラー
                if status == 401 or status == 403:
                    logger.error(f"Authentication error ({status})")
                    raise CrawlerError(f"Cloudflare authentication failed ({status})")
                
                # レスポンスをJSON形式で取得
                response_data = await response.json()
                
                # 成功レスポンス
                if status == 200 and response_data.get("success"):
                    result = response_data.get("result", {})
                    return CloudflareResponse(
                        success=True,
                        markdown=result.get("markdown", ""),
                        url=result.get("url", url),
                        timestamp=result.get("timestamp", ""),
                        error=None
                    )
                
                # エラーレスポンス
                errors = response_data.get("errors", [])
                error_msg = errors[0].get("message", "Unknown error") if errors else "Unknown error"
                
                return CloudflareResponse(
                    success=False,
                    markdown="",
                    url=url,
                    timestamp="",
                    error=error_msg
                )
