"""Webページが動的か静的かを判定するモジュール."""
import re
from typing import List

from bs4 import BeautifulSoup

from src.logging_config import get_logger

# ロガーの設定
logger = get_logger(__name__)


class PageClassifier:
    """ページが動的か静的かを判定するユーティリティクラス."""
    
    # JavaScriptフレームワークの検出パターン
    FRAMEWORK_PATTERNS = {
        'React': [
            r'<div[^>]+id=["\']root["\']',
            r'data-reactroot',
            r'data-react-',
        ],
        'Vue': [
            r'<div[^>]+id=["\']app["\']',
            r'v-cloak',
            r'v-if',
            r'v-for',
        ],
        'Angular': [
            r'ng-app',
            r'ng-controller',
            r'ng-model',
        ],
        'Next.js': [
            r'__NEXT_DATA__',
            r'_next/static',
        ],
        'Nuxt': [
            r'__NUXT__',
        ],
    }
    
    # テキストコンテンツ比率の閾値
    TEXT_RATIO_THRESHOLD = 0.1
    
    @staticmethod
    def is_dynamic_page(html: str) -> bool:
        """
        ページが動的かどうかを判定.
        
        Args:
            html: HTMLコンテンツ
            
        Returns:
            bool: 動的ページの場合True
        """
        # JavaScriptフレームワークを検出
        frameworks = PageClassifier._detect_js_frameworks(html)
        
        # テキストコンテンツ比率を計算
        text_ratio = PageClassifier._calculate_text_ratio(html)
        
        # フレームワークがあり、テキストが少ない場合は動的
        if frameworks and text_ratio < PageClassifier.TEXT_RATIO_THRESHOLD:
            logger.info(
                f"Page classified as dynamic: frameworks={frameworks}, "
                f"text_ratio={text_ratio:.2%}"
            )
            return True
        
        # デフォルトは静的
        logger.info(
            f"Page classified as static: frameworks={frameworks}, "
            f"text_ratio={text_ratio:.2%}"
        )
        return False
    
    @staticmethod
    def _detect_js_frameworks(html: str) -> List[str]:
        """
        JavaScriptフレームワークを検出.
        
        Args:
            html: HTMLコンテンツ
            
        Returns:
            List[str]: 検出されたフレームワークのリスト
        """
        detected = []
        
        for framework, patterns in PageClassifier.FRAMEWORK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, html, re.IGNORECASE):
                    detected.append(framework)
                    break  # 1つでもマッチしたら次のフレームワークへ
        
        return detected
    
    @staticmethod
    def _calculate_text_ratio(html: str) -> float:
        """
        テキストコンテンツの割合を計算.
        
        Args:
            html: HTMLコンテンツ
            
        Returns:
            float: テキストコンテンツの割合（0.0〜1.0）
        """
        try:
            # BeautifulSoupでHTMLをパース
            soup = BeautifulSoup(html, 'html.parser')
            
            # スクリプトとスタイルタグを削除
            for script in soup(['script', 'style']):
                script.decompose()
            
            # テキストコンテンツを取得
            text = soup.get_text(strip=True)
            text_length = len(text)
            
            # HTMLサイズ
            html_length = len(html)
            
            # 比率を計算
            if html_length == 0:
                return 0.0
            
            ratio = text_length / html_length
            return ratio
            
        except Exception as e:
            logger.warning(f"Failed to calculate text ratio: {e}")
            # エラーの場合は安全側に倒して静的として扱う
            return 1.0
