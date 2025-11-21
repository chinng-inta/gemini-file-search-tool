"""PageClassifierのプロパティベーステスト."""
import pytest
from hypothesis import given, strategies as st, settings, assume
from src.page_classifier import PageClassifier


class TestDynamicPageDetectionProperty:
    """
    プロパティ 2: 動的ページ検出とレンダリング
    
    **Feature: enhanced-document-processing, Property 2: 動的ページ検出とレンダリング**
    **検証: 要件 1.2, 2.2**
    
    任意のHTMLコンテンツに対して、JavaScriptフレームワークを含み最小限の
    テキストコンテンツしか持たないページは動的として分類される
    """
    
    @given(
        framework=st.sampled_from(['React', 'Vue', 'Angular', 'Next.js', 'Nuxt']),
        text_length=st.integers(min_value=0, max_value=50),
        script_length=st.integers(min_value=500, max_value=1000)
    )
    @settings(max_examples=100)
    def test_dynamic_page_detection_property(
        self,
        framework: str,
        text_length: int,
        script_length: int
    ):
        """
        プロパティ: フレームワークを含み、テキストが少ないページは動的として分類される.
        
        Args:
            framework: JavaScriptフレームワーク名
            text_length: テキストコンテンツの長さ
            script_length: スクリプトコンテンツの長さ
        """
        # フレームワーク固有のマーカーを生成
        framework_markers = {
            'React': '<div id="root"></div>',
            'Vue': '<div id="app" v-cloak></div>',
            'Angular': '<div ng-app="myApp"></div>',
            'Next.js': '<script id="__NEXT_DATA__">{}</script>',
            'Nuxt': '<script>window.__NUXT__={}</script>'
        }
        
        marker = framework_markers[framework]
        text_content = "a" * text_length
        script_content = "x" * script_length
        
        html = f"""
        <html>
        <head>
            <script>{script_content}</script>
        </head>
        <body>
            {marker}
            <p>{text_content}</p>
        </body>
        </html>
        """
        
        # PageClassifierで判定
        is_dynamic = PageClassifier.is_dynamic_page(html)
        
        # フレームワークを検出
        frameworks = PageClassifier._detect_js_frameworks(html)
        
        # テキスト比率を計算
        text_ratio = PageClassifier._calculate_text_ratio(html)
        
        # プロパティ: フレームワークがあり、テキスト比率が閾値未満の場合、動的と判定される
        if frameworks and text_ratio < PageClassifier.TEXT_RATIO_THRESHOLD:
            assert is_dynamic, (
                f"Expected dynamic page detection for HTML with "
                f"frameworks={frameworks} and text_ratio={text_ratio:.2%}, "
                f"but got is_dynamic={is_dynamic}"
            )
    
    def test_dynamic_page_react(self):
        """エッジケース: Reactアプリケーションは動的として検出される."""
        html = """
        <html>
        <head>
            <script src="react.js"></script>
            <script src="app.js"></script>
        </head>
        <body>
            <div id="root"></div>
        </body>
        </html>
        """
        
        assert PageClassifier.is_dynamic_page(html)
    
    def test_dynamic_page_vue(self):
        """エッジケース: Vueアプリケーションは動的として検出される."""
        html = """
        <html>
        <head>
            <script src="vue.js"></script>
        </head>
        <body>
            <div id="app" v-cloak>
                <p v-if="show">{{ message }}</p>
            </div>
        </body>
        </html>
        """
        
        assert PageClassifier.is_dynamic_page(html)
    
    def test_dynamic_page_angular(self):
        """エッジケース: Angularアプリケーションは動的として検出される."""
        html = """
        <html>
        <head>
            <script src="angular.js"></script>
        </head>
        <body>
            <div ng-app="myApp" ng-controller="myCtrl">
                <p>{{ message }}</p>
            </div>
        </body>
        </html>
        """
        
        assert PageClassifier.is_dynamic_page(html)
    
    def test_dynamic_page_nextjs(self):
        """エッジケース: Next.jsアプリケーションは動的として検出される."""
        html = """
        <html>
        <head>
            <script src="_next/static/chunks/main.js"></script>
        </head>
        <body>
            <div id="__next"></div>
            <script id="__NEXT_DATA__" type="application/json">
                {"props": {}}
            </script>
        </body>
        </html>
        """
        
        assert PageClassifier.is_dynamic_page(html)
    
    def test_dynamic_page_nuxt(self):
        """エッジケース: Nuxtアプリケーションは動的として検出される."""
        html = """
        <html>
        <head>
            <script src="_nuxt/app.js"></script>
        </head>
        <body>
            <div id="__nuxt"></div>
            <script>window.__NUXT__={}</script>
        </body>
        </html>
        """
        
        assert PageClassifier.is_dynamic_page(html)
    
    @given(
        framework=st.sampled_from(['React', 'Vue', 'Angular', 'Next.js', 'Nuxt']),
        text_length=st.integers(min_value=0, max_value=100),
        script_length=st.integers(min_value=1000, max_value=5000)
    )
    @settings(max_examples=100)
    def test_dynamic_page_with_framework_and_low_text_ratio(
        self,
        framework: str,
        text_length: int,
        script_length: int
    ):
        """
        プロパティ: フレームワークがあり、テキスト比率が低い場合、動的と判定される.
        
        Args:
            framework: JavaScriptフレームワーク名
            text_length: テキストコンテンツの長さ
            script_length: スクリプトコンテンツの長さ
        """
        # フレームワーク固有のマーカーを生成
        framework_markers = {
            'React': '<div id="root"></div>',
            'Vue': '<div id="app" v-cloak></div>',
            'Angular': '<div ng-app="myApp"></div>',
            'Next.js': '<script id="__NEXT_DATA__">{}</script>',
            'Nuxt': '<script>window.__NUXT__={}</script>'
        }
        
        marker = framework_markers[framework]
        text_content = "a" * text_length
        script_content = "x" * script_length
        
        html = f"""
        <html>
        <head>
            <script>{script_content}</script>
        </head>
        <body>
            {marker}
            <p>{text_content}</p>
        </body>
        </html>
        """
        
        # テキスト比率を計算
        text_ratio = PageClassifier._calculate_text_ratio(html)
        
        # プロパティ: テキスト比率が閾値未満の場合、動的と判定される
        if text_ratio < PageClassifier.TEXT_RATIO_THRESHOLD:
            assert PageClassifier.is_dynamic_page(html), (
                f"Expected dynamic page for {framework} with text_ratio={text_ratio:.2%}"
            )


class TestStaticPageClassificationProperty:
    """
    プロパティ 5: 静的ページ分類
    
    **Feature: enhanced-document-processing, Property 5: 静的ページ分類**
    **検証: 要件 2.3**
    
    任意のHTMLコンテンツに対して、実質的なテキストコンテンツを含むページは
    静的として分類される
    """
    
    @given(
        num_paragraphs=st.integers(min_value=5, max_value=15),
        paragraph_length=st.integers(min_value=100, max_value=300)
    )
    @settings(max_examples=100)
    def test_static_page_classification_property(
        self,
        num_paragraphs: int,
        paragraph_length: int
    ):
        """
        プロパティ: 実質的なテキストコンテンツを含むページは静的として分類される.
        
        Args:
            num_paragraphs: 段落の数
            paragraph_length: 各段落の長さ
        """
        # テキストコンテンツを生成
        paragraphs = [("Lorem ipsum dolor sit amet " * (paragraph_length // 27))[:paragraph_length] 
                     for _ in range(num_paragraphs)]
        content = "\n".join([f"<p>{p}</p>" for p in paragraphs])
        
        html = f"""
        <html>
        <head>
            <title>Static Page</title>
        </head>
        <body>
            <h1>Content</h1>
            {content}
        </body>
        </html>
        """
        
        # PageClassifierで判定
        is_dynamic = PageClassifier.is_dynamic_page(html)
        
        # テキスト比率を計算
        text_ratio = PageClassifier._calculate_text_ratio(html)
        
        # プロパティ: テキスト比率が閾値以上の場合、静的と判定される（is_dynamic=False）
        if text_ratio >= PageClassifier.TEXT_RATIO_THRESHOLD:
            assert not is_dynamic, (
                f"Expected static page classification for HTML with "
                f"text_ratio={text_ratio:.2%}, but got is_dynamic={is_dynamic}"
            )
    
    def test_static_page_with_substantial_text(self):
        """エッジケース: 実質的なテキストコンテンツを持つページは静的として検出される."""
        html = """
        <html>
        <head>
            <title>Documentation</title>
        </head>
        <body>
            <h1>API Documentation</h1>
            <p>This is a comprehensive guide to using our API.</p>
            <h2>Getting Started</h2>
            <p>To get started, you need to create an account and obtain an API key.</p>
            <h2>Authentication</h2>
            <p>All API requests must include your API key in the Authorization header.</p>
            <h2>Endpoints</h2>
            <p>The following endpoints are available:</p>
            <ul>
                <li>/users - Manage users</li>
                <li>/posts - Manage posts</li>
                <li>/comments - Manage comments</li>
            </ul>
        </body>
        </html>
        """
        
        assert not PageClassifier.is_dynamic_page(html)
    
    def test_static_page_with_minimal_scripts(self):
        """エッジケース: 最小限のスクリプトを含む静的ページ."""
        html = """
        <html>
        <head>
            <script>
                // Simple analytics
                console.log('Page loaded');
            </script>
        </head>
        <body>
            <h1>Welcome</h1>
            <p>This is a static page with lots of text content.</p>
            <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
            <p>Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
            <p>Ut enim ad minim veniam, quis nostrud exercitation ullamco.</p>
        </body>
        </html>
        """
        
        assert not PageClassifier.is_dynamic_page(html)
    
    @given(
        text_paragraphs=st.lists(
            st.text(min_size=50, max_size=200),
            min_size=5,
            max_size=20
        )
    )
    @settings(max_examples=100)
    def test_static_page_with_high_text_ratio(self, text_paragraphs: list):
        """
        プロパティ: テキスト比率が高いページは静的として分類される.
        
        Args:
            text_paragraphs: ランダムに生成されたテキスト段落のリスト
        """
        # HTMLを構築
        content = "\n".join([f"<p>{p}</p>" for p in text_paragraphs])
        html = f"""
        <html>
        <head>
            <title>Static Page</title>
        </head>
        <body>
            <h1>Content</h1>
            {content}
        </body>
        </html>
        """
        
        # テキスト比率を計算
        text_ratio = PageClassifier._calculate_text_ratio(html)
        
        # プロパティ: テキスト比率が閾値以上の場合、静的と判定される
        if text_ratio >= PageClassifier.TEXT_RATIO_THRESHOLD:
            assert not PageClassifier.is_dynamic_page(html), (
                f"Expected static page for text_ratio={text_ratio:.2%}"
            )


class TestDefaultStaticProcessingProperty:
    """
    プロパティ 6: デフォルト静的処理
    
    **Feature: enhanced-document-processing, Property 6: デフォルト静的処理**
    **検証: 要件 2.4**
    
    任意の分類が不確実なページに対して、システムはデフォルトで静的処理を選択する
    """
    
    @given(html=st.text(min_size=0, max_size=1000))
    @settings(max_examples=100)
    def test_default_static_processing_property(self, html: str):
        """
        プロパティ: フレームワークがない場合、デフォルトで静的として分類される.
        
        Args:
            html: ランダムに生成されたHTML（フレームワークマーカーを含まない可能性が高い）
        """
        # フレームワークを検出
        frameworks = PageClassifier._detect_js_frameworks(html)
        
        # PageClassifierで判定
        is_dynamic = PageClassifier.is_dynamic_page(html)
        
        # プロパティ: フレームワークがない場合、静的と判定される（is_dynamic=False）
        if not frameworks:
            assert not is_dynamic, (
                f"Expected static (default) classification for HTML without frameworks, "
                f"but got is_dynamic={is_dynamic}"
            )
    
    def test_default_static_empty_html(self):
        """エッジケース: 空のHTMLはデフォルトで静的として扱われる."""
        html = ""
        assert not PageClassifier.is_dynamic_page(html)
    
    def test_default_static_minimal_html(self):
        """エッジケース: 最小限のHTMLはデフォルトで静的として扱われる."""
        html = "<html><body></body></html>"
        assert not PageClassifier.is_dynamic_page(html)
    
    def test_default_static_no_framework_markers(self):
        """エッジケース: フレームワークマーカーがないページは静的として扱われる."""
        html = """
        <html>
        <head>
            <script>
                // Some custom JavaScript
                function myFunction() {
                    console.log('Hello');
                }
            </script>
        </head>
        <body>
            <div id="content">
                <p>Some content</p>
            </div>
        </body>
        </html>
        """
        
        assert not PageClassifier.is_dynamic_page(html)
    
    def test_default_static_framework_with_high_text_ratio(self):
        """エッジケース: フレームワークがあってもテキスト比率が高い場合は静的."""
        html = """
        <html>
        <head>
            <script src="react.js"></script>
        </head>
        <body>
            <div id="root"></div>
            <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.</p>
            <p>Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
            <p>Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.</p>
        </body>
        </html>
        """
        
        # テキスト比率が高いため、フレームワークがあっても静的と判定される
        assert not PageClassifier.is_dynamic_page(html)
    
    @given(
        html_without_framework=st.text(min_size=10, max_size=500).filter(
            lambda x: 'id="root"' not in x and 
                     'id="app"' not in x and 
                     'ng-app' not in x and 
                     '__NEXT_DATA__' not in x and 
                     '__NUXT__' not in x
        )
    )
    @settings(max_examples=100)
    def test_default_static_no_framework_detected(self, html_without_framework: str):
        """
        プロパティ: フレームワークが検出されない場合、常に静的と判定される.
        
        Args:
            html_without_framework: フレームワークマーカーを含まないHTML
        """
        # フレームワークが検出されないことを確認
        frameworks = PageClassifier._detect_js_frameworks(html_without_framework)
        assume(len(frameworks) == 0)
        
        # PageClassifierで判定
        is_dynamic = PageClassifier.is_dynamic_page(html_without_framework)
        
        # プロパティ: フレームワークがない場合、常に静的と判定される
        assert not is_dynamic, (
            f"Expected static classification for HTML without frameworks, "
            f"but got is_dynamic={is_dynamic}"
        )
