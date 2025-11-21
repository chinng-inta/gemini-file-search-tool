"""ファイル検証機能のプロパティベーステスト."""
import pytest
from pathlib import Path
from hypothesis import given, strategies as st, settings, HealthCheck
from src.rag_manager import GeminiRAGManager, RAGError


def create_rag_manager(tmp_path):
    """テスト用のRAGマネージャーインスタンスを作成するヘルパー関数."""
    config_path = tmp_path / "rag_config.json"
    return GeminiRAGManager(
        str(config_path),
        file_search_api_key="test_file_search_key",
        code_gen_api_key="test_code_gen_key"
    )


# カスタムストラテジー: サポートされている拡張子
supported_extensions = st.sampled_from([".txt", ".md", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp"])

# カスタムストラテジー: サポートされていない拡張子
unsupported_extensions = st.sampled_from([".exe", ".dll", ".so", ".bin", ".zip", ".tar", ".gz", ".rar", ".7z", ".doc", ".docx", ".xls", ".xlsx"])


class TestFileExistenceValidation:
    """ファイル存在検証のプロパティテスト."""
    
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    @given(filename=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122)))
    def test_property_11_file_existence_validation_existing_files(self, tmp_path, filename):
        """
        Feature: enhanced-document-processing, Property 11: ファイル存在検証
        
        任意のファイルパスに対して、アップロード前にファイルの存在が検証される
        Validates: 要件 3.1
        
        このテストでは、存在するファイルに対して検証が成功することを確認します。
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        # 有効なファイル名を生成（英数字のみ）
        safe_filename = ''.join(c for c in filename if c.isalnum())
        if not safe_filename:
            safe_filename = "testfile"
        
        # テスト用のファイルを作成
        test_file = tmp_path / f"{safe_filename}.txt"
        test_file.write_text("Test content")
        
        # ファイル検証を実行
        result = rag_manager._validate_file(str(test_file))
        
        # 存在するファイルは検証に成功する
        assert result["valid"] is True
        assert result["error"] is None
        assert result["size"] > 0
        assert result["extension"] == ".txt"
    
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    @given(path_parts=st.lists(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122)), min_size=1, max_size=5))
    def test_property_11_file_existence_validation_nonexistent_files(self, tmp_path, path_parts):
        """
        Feature: enhanced-document-processing, Property 11: ファイル存在検証
        
        任意の存在しないファイルパスに対して、検証が失敗することを確認
        Validates: 要件 3.1
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        # 存在しないファイルパスを生成
        safe_parts = [''.join(c for c in part if c.isalnum()) or "dir" for part in path_parts]
        nonexistent_path = tmp_path / Path(*safe_parts) / "nonexistent.txt"
        
        # ファイル検証を実行
        result = rag_manager._validate_file(str(nonexistent_path))
        
        # 存在しないファイルは検証に失敗する
        assert result["valid"] is False
        assert result["error"] is not None
        assert "File not found" in result["error"]


class TestUnsupportedExtensionRejection:
    """サポートされていない拡張子拒否のプロパティテスト."""
    
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        filename=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122)),
        extension=unsupported_extensions
    )
    def test_property_19_unsupported_extension_rejection(self, tmp_path, filename, extension):
        """
        Feature: enhanced-document-processing, Property 19: サポートされていない拡張子の拒否
        
        任意のサポートされていない拡張子（.txt、.md、.pdf、.png、.jpg、.jpeg、.gif、.webp以外）を持つファイルに対して、
        システムは明確なエラーメッセージで拒否する
        Validates: 要件 7.5
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        # 有効なファイル名を生成
        safe_filename = ''.join(c for c in filename if c.isalnum())
        if not safe_filename:
            safe_filename = "testfile"
        
        # サポートされていない拡張子のファイルを作成
        test_file = tmp_path / f"{safe_filename}{extension}"
        test_file.write_bytes(b"Test content")
        
        # ファイル検証を実行
        result = rag_manager._validate_file(str(test_file))
        
        # サポートされていない拡張子は拒否される
        assert result["valid"] is False
        assert result["error"] is not None
        assert "Unsupported file extension" in result["error"]
        assert extension in result["error"]
        assert result["extension"] == extension
    
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        filename=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122)),
        extension=supported_extensions
    )
    def test_property_19_supported_extension_acceptance(self, tmp_path, filename, extension):
        """
        Feature: enhanced-document-processing, Property 19: サポートされている拡張子の受け入れ
        
        任意のサポートされている拡張子を持つファイルに対して、
        システムは拡張子の検証をパスする
        Validates: 要件 7.1, 7.2, 7.3, 7.4
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        # 有効なファイル名を生成
        safe_filename = ''.join(c for c in filename if c.isalnum())
        if not safe_filename:
            safe_filename = "testfile"
        
        # サポートされている拡張子のファイルを作成
        test_file = tmp_path / f"{safe_filename}{extension}"
        
        # 拡張子に応じて適切なコンテンツを書き込む
        if extension in [".txt", ".md"]:
            test_file.write_text("Test content")
        else:
            # バイナリファイル（画像、PDF）
            test_file.write_bytes(b"Test binary content")
        
        # ファイル検証を実行
        result = rag_manager._validate_file(str(test_file))
        
        # サポートされている拡張子は受け入れられる（サイズ制限内の場合）
        if result["size"] <= 50 * 1024 * 1024:  # 50MB以下
            assert result["valid"] is True
            assert result["error"] is None
            assert result["extension"] == extension


class TestEncodingPreservation:
    """エンコーディング保持のプロパティテスト."""
    
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        content=st.text(min_size=1, max_size=1000),
        filename=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122))
    )
    def test_property_20_encoding_preservation_utf8(self, tmp_path, content, filename):
        """
        Feature: enhanced-document-processing, Property 20: エンコーディング保持
        
        任意のUTF-8テキストファイルに対して、元のファイルエンコーディングが保持される
        Validates: 要件 7.6
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        # 有効なファイル名を生成
        safe_filename = ''.join(c for c in filename if c.isalnum())
        if not safe_filename:
            safe_filename = "testfile"
        
        # UTF-8でテキストファイルを作成
        test_file = tmp_path / f"{safe_filename}.txt"
        test_file.write_text(content, encoding='utf-8')
        
        # ファイル検証を実行
        result = rag_manager._validate_file(str(test_file))
        
        # UTF-8エンコーディングのファイルは検証に成功する
        assert result["valid"] is True
        assert result["error"] is None
        
        # ファイルを読み戻して内容が保持されていることを確認
        read_content = test_file.read_text(encoding='utf-8')
        assert read_content == content
    
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        filename=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122))
    )
    def test_property_20_encoding_preservation_invalid_encoding(self, tmp_path, filename):
        """
        Feature: enhanced-document-processing, Property 20: エンコーディング保持
        
        任意の不正なエンコーディングのファイルに対して、検証が失敗することを確認
        Validates: 要件 7.6
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        # 有効なファイル名を生成
        safe_filename = ''.join(c for c in filename if c.isalnum())
        if not safe_filename:
            safe_filename = "testfile"
        
        # 不正なUTF-8バイトシーケンスを含むファイルを作成
        test_file = tmp_path / f"{safe_filename}.txt"
        # 不正なUTF-8バイトシーケンス
        invalid_utf8 = b'\xff\xfe\xfd'
        test_file.write_bytes(invalid_utf8)
        
        # ファイル検証を実行
        result = rag_manager._validate_file(str(test_file))
        
        # 不正なエンコーディングのファイルは検証に失敗する
        assert result["valid"] is False
        assert result["error"] is not None
        assert "Failed to read file encoding" in result["error"]


class TestFileSizeValidation:
    """ファイルサイズ検証のプロパティテスト."""
    
    @settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        size_kb=st.integers(min_value=100, max_value=1000),
        filename=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122))
    )
    def test_file_size_within_limit(self, tmp_path, size_kb, filename):
        """
        任意の50MB以下のファイルに対して、サイズ検証が成功することを確認
        Validates: 要件 7.7
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        # 有効なファイル名を生成
        safe_filename = ''.join(c for c in filename if c.isalnum())
        if not safe_filename:
            safe_filename = "testfile"
        
        # 指定されたサイズのファイルを作成（KB単位）
        test_file = tmp_path / f"{safe_filename}.txt"
        content = "x" * (size_kb * 1024)  # size_kb KB
        test_file.write_text(content)
        
        # ファイル検証を実行
        result = rag_manager._validate_file(str(test_file))
        
        # 50MB以下のファイルは検証に成功する
        assert result["valid"] is True
        assert result["error"] is None
        assert result["size"] == size_kb * 1024
    
    def test_file_size_exceeds_limit(self, tmp_path):
        """
        任意の50MBを超えるファイルに対して、サイズ検証が失敗することを確認
        Validates: 要件 7.7
        
        注: このテストは事前に作成された51MBのファイルを使用します
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        # 事前に作成された51MBのファイルを使用
        large_file = Path("tests/test_large_file_51mb.txt")
        
        # ファイルが存在しない場合はスキップ
        if not large_file.exists():
            pytest.skip("Large test file not found. Run: python -c \"with open('tests/test_large_file_51mb.txt', 'w') as f: f.write('x' * (51 * 1024 * 1024))\"")
        
        # ファイル検証を実行
        result = rag_manager._validate_file(str(large_file))
        
        # 50MBを超えるファイルは検証に失敗する
        assert result["valid"] is False
        assert result["error"] is not None
        assert "File too large" in result["error"]
        assert "50MB" in result["error"]
