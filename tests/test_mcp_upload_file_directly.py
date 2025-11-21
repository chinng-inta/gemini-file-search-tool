"""upload_file_directlyツールのMCP統合テスト."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from mcp_server import GeminiRAGMCPServer
from src.errors import MCPError
from src.rag_manager import RAGError


@pytest.fixture
def temp_files(tmp_path):
    """テスト用の一時ファイルを作成."""
    # 有効なファイルを作成
    valid_file = tmp_path / "test_doc.txt"
    valid_file.write_text("Test document content", encoding='utf-8')
    
    # 大きなファイルを作成（50MB超）
    large_file = tmp_path / "large_doc.txt"
    large_file.write_text("x" * (51 * 1024 * 1024), encoding='utf-8')
    
    return {
        "valid": str(valid_file),
        "large": str(large_file),
        "nonexistent": str(tmp_path / "nonexistent.txt")
    }


@pytest.fixture
def mock_rag_manager():
    """モックされたRAGマネージャーを作成."""
    manager = MagicMock()
    manager.upload_file_directly = AsyncMock()
    return manager


class TestUploadFileDirectlyToolCall:
    """upload_file_directlyツールの呼び出しテスト."""
    
    @pytest.mark.asyncio
    async def test_upload_file_directly_basic(self, temp_files, mock_rag_manager, monkeypatch):
        """基本的なファイルアップロードが正常に動作することを確認."""
        # RAGマネージャーのモック設定
        mock_rag_manager.upload_file_directly.return_value = "fileSearchStores/test123"
        
        # MCPサーバーを初期化（設定とクローラーをモック）
        with patch('mcp_server.get_config') as mock_config, \
             patch('mcp_server.APICrawler') as mock_crawler, \
             patch('mcp_server.GeminiRAGManager', return_value=mock_rag_manager):
            
            # 設定のモック
            mock_config_instance = MagicMock()
            mock_config_instance.get_docs_store_path.return_value = "/tmp/docs"
            mock_config_instance.get_url_config_path.return_value = "/tmp/url_config.json"
            mock_config_instance.get_rag_config_path.return_value = "/tmp/rag_config.json"
            mock_config_instance.get_gemini_file_search_api_key.return_value = "test_key"
            mock_config_instance.get_gemini_code_gen_api_key.return_value = "test_key"
            mock_config.return_value = mock_config_instance
            
            # MCPサーバーを初期化
            server = GeminiRAGMCPServer()
            
            # ツールを呼び出し
            result = await server.handle_upload_file_directly(
                file_path=temp_files["valid"],
                doc_type="test",
                description="Test documentation"
            )
            
            # 結果を検証
            assert result["success"] is True
            assert result["message"] == "File uploaded successfully"
            assert result["file_path"] == temp_files["valid"]
            assert result["doc_type"] == "test"
            assert result["rag_id"] == "fileSearchStores/test123"
            
            # RAGマネージャーが正しく呼び出されたことを確認
            mock_rag_manager.upload_file_directly.assert_called_once_with(
                file_path=temp_files["valid"],
                doc_type="test",
                description="Test documentation"
            )
    
    @pytest.mark.asyncio
    async def test_upload_file_directly_without_doc_type(self, temp_files, mock_rag_manager):
        """doc_typeなしでファイルアップロードが動作することを確認."""
        # RAGマネージャーのモック設定
        mock_rag_manager.upload_file_directly.return_value = "fileSearchStores/test456"
        
        with patch('mcp_server.get_config') as mock_config, \
             patch('mcp_server.APICrawler'), \
             patch('mcp_server.GeminiRAGManager', return_value=mock_rag_manager):
            
            # 設定のモック
            mock_config_instance = MagicMock()
            mock_config_instance.get_docs_store_path.return_value = "/tmp/docs"
            mock_config_instance.get_url_config_path.return_value = "/tmp/url_config.json"
            mock_config_instance.get_rag_config_path.return_value = "/tmp/rag_config.json"
            mock_config_instance.get_gemini_file_search_api_key.return_value = "test_key"
            mock_config_instance.get_gemini_code_gen_api_key.return_value = "test_key"
            mock_config.return_value = mock_config_instance
            
            server = GeminiRAGMCPServer()
            
            # doc_typeなしで呼び出し
            result = await server.handle_upload_file_directly(
                file_path=temp_files["valid"],
                doc_type=None,
                description="Test documentation"
            )
            
            # 結果を検証
            assert result["success"] is True
            assert result["doc_type"] is None
            
            # RAGマネージャーが正しく呼び出されたことを確認
            mock_rag_manager.upload_file_directly.assert_called_once_with(
                file_path=temp_files["valid"],
                doc_type=None,
                description="Test documentation"
            )
    
    @pytest.mark.asyncio
    async def test_upload_file_directly_without_description(self, temp_files, mock_rag_manager):
        """descriptionなしでファイルアップロードが動作することを確認."""
        # RAGマネージャーのモック設定
        mock_rag_manager.upload_file_directly.return_value = "fileSearchStores/test789"
        
        with patch('mcp_server.get_config') as mock_config, \
             patch('mcp_server.APICrawler'), \
             patch('mcp_server.GeminiRAGManager', return_value=mock_rag_manager):
            
            # 設定のモック
            mock_config_instance = MagicMock()
            mock_config_instance.get_docs_store_path.return_value = "/tmp/docs"
            mock_config_instance.get_url_config_path.return_value = "/tmp/url_config.json"
            mock_config_instance.get_rag_config_path.return_value = "/tmp/rag_config.json"
            mock_config_instance.get_gemini_file_search_api_key.return_value = "test_key"
            mock_config_instance.get_gemini_code_gen_api_key.return_value = "test_key"
            mock_config.return_value = mock_config_instance
            
            server = GeminiRAGMCPServer()
            
            # descriptionなしで呼び出し
            result = await server.handle_upload_file_directly(
                file_path=temp_files["valid"],
                doc_type="test",
                description=None
            )
            
            # 結果を検証
            assert result["success"] is True
            
            # RAGマネージャーが正しく呼び出されたことを確認
            mock_rag_manager.upload_file_directly.assert_called_once_with(
                file_path=temp_files["valid"],
                doc_type="test",
                description=None
            )


class TestUploadFileDirectlyParameterValidation:
    """upload_file_directlyツールのパラメータ検証テスト."""
    
    @pytest.mark.asyncio
    async def test_upload_file_directly_empty_file_path(self, mock_rag_manager):
        """file_pathが空の場合、エラーが返されることを確認."""
        with patch('mcp_server.get_config') as mock_config, \
             patch('mcp_server.APICrawler'), \
             patch('mcp_server.GeminiRAGManager', return_value=mock_rag_manager):
            
            # 設定のモック
            mock_config_instance = MagicMock()
            mock_config_instance.get_docs_store_path.return_value = "/tmp/docs"
            mock_config_instance.get_url_config_path.return_value = "/tmp/url_config.json"
            mock_config_instance.get_rag_config_path.return_value = "/tmp/rag_config.json"
            mock_config_instance.get_gemini_file_search_api_key.return_value = "test_key"
            mock_config_instance.get_gemini_code_gen_api_key.return_value = "test_key"
            mock_config.return_value = mock_config_instance
            
            server = GeminiRAGMCPServer()
            
            # 空のfile_pathで呼び出し
            result = await server.handle_upload_file_directly(
                file_path="",
                doc_type="test",
                description="Test"
            )
            
            # エラーが返されることを確認
            assert result["success"] is False
            assert "file_path is required" in result["error"]
            
            # RAGマネージャーが呼び出されていないことを確認
            mock_rag_manager.upload_file_directly.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_upload_file_directly_none_file_path(self, mock_rag_manager):
        """file_pathがNoneの場合、エラーが返されることを確認."""
        with patch('mcp_server.get_config') as mock_config, \
             patch('mcp_server.APICrawler'), \
             patch('mcp_server.GeminiRAGManager', return_value=mock_rag_manager):
            
            # 設定のモック
            mock_config_instance = MagicMock()
            mock_config_instance.get_docs_store_path.return_value = "/tmp/docs"
            mock_config_instance.get_url_config_path.return_value = "/tmp/url_config.json"
            mock_config_instance.get_rag_config_path.return_value = "/tmp/rag_config.json"
            mock_config_instance.get_gemini_file_search_api_key.return_value = "test_key"
            mock_config_instance.get_gemini_code_gen_api_key.return_value = "test_key"
            mock_config.return_value = mock_config_instance
            
            server = GeminiRAGMCPServer()
            
            # Noneのfile_pathで呼び出し
            result = await server.handle_upload_file_directly(
                file_path=None,
                doc_type="test",
                description="Test"
            )
            
            # エラーが返されることを確認
            assert result["success"] is False
            assert "file_path is required" in result["error"]
            
            # RAGマネージャーが呼び出されていないことを確認
            mock_rag_manager.upload_file_directly.assert_not_called()


class TestUploadFileDirectlyErrorResponse:
    """upload_file_directlyツールのエラーレスポンステスト."""
    
    @pytest.mark.asyncio
    async def test_upload_file_directly_rag_error(self, temp_files, mock_rag_manager):
        """RAGErrorが発生した場合、適切なエラーレスポンスが返されることを確認."""
        # RAGマネージャーがエラーを返すように設定
        mock_rag_manager.upload_file_directly.side_effect = RAGError("File not found: /path/to/file.txt")
        
        with patch('mcp_server.get_config') as mock_config, \
             patch('mcp_server.APICrawler'), \
             patch('mcp_server.GeminiRAGManager', return_value=mock_rag_manager):
            
            # 設定のモック
            mock_config_instance = MagicMock()
            mock_config_instance.get_docs_store_path.return_value = "/tmp/docs"
            mock_config_instance.get_url_config_path.return_value = "/tmp/url_config.json"
            mock_config_instance.get_rag_config_path.return_value = "/tmp/rag_config.json"
            mock_config_instance.get_gemini_file_search_api_key.return_value = "test_key"
            mock_config_instance.get_gemini_code_gen_api_key.return_value = "test_key"
            mock_config.return_value = mock_config_instance
            
            server = GeminiRAGMCPServer()
            
            # ツールを呼び出し
            result = await server.handle_upload_file_directly(
                file_path=temp_files["nonexistent"],
                doc_type="test",
                description="Test"
            )
            
            # エラーレスポンスを検証
            assert result["success"] is False
            assert "File not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_upload_file_directly_unexpected_error(self, temp_files, mock_rag_manager):
        """予期しないエラーが発生した場合、適切なエラーレスポンスが返されることを確認."""
        # RAGマネージャーが予期しないエラーを返すように設定
        mock_rag_manager.upload_file_directly.side_effect = Exception("Unexpected error occurred")
        
        with patch('mcp_server.get_config') as mock_config, \
             patch('mcp_server.APICrawler'), \
             patch('mcp_server.GeminiRAGManager', return_value=mock_rag_manager):
            
            # 設定のモック
            mock_config_instance = MagicMock()
            mock_config_instance.get_docs_store_path.return_value = "/tmp/docs"
            mock_config_instance.get_url_config_path.return_value = "/tmp/url_config.json"
            mock_config_instance.get_rag_config_path.return_value = "/tmp/rag_config.json"
            mock_config_instance.get_gemini_file_search_api_key.return_value = "test_key"
            mock_config_instance.get_gemini_code_gen_api_key.return_value = "test_key"
            mock_config.return_value = mock_config_instance
            
            server = GeminiRAGMCPServer()
            
            # ツールを呼び出し
            result = await server.handle_upload_file_directly(
                file_path=temp_files["valid"],
                doc_type="test",
                description="Test"
            )
            
            # エラーレスポンスを検証
            assert result["success"] is False
            assert "Unexpected error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_upload_file_directly_unsupported_extension(self, tmp_path, mock_rag_manager):
        """サポートされていない拡張子の場合、エラーが返されることを確認."""
        # サポートされていない拡張子のファイルを作成
        unsupported_file = tmp_path / "test.exe"
        unsupported_file.write_text("test content")
        
        # RAGマネージャーがエラーを返すように設定
        mock_rag_manager.upload_file_directly.side_effect = RAGError(
            "Unsupported file extension: .exe. Supported: .txt, .md, .pdf, .png, .jpg, .jpeg, .gif, .webp"
        )
        
        with patch('mcp_server.get_config') as mock_config, \
             patch('mcp_server.APICrawler'), \
             patch('mcp_server.GeminiRAGManager', return_value=mock_rag_manager):
            
            # 設定のモック
            mock_config_instance = MagicMock()
            mock_config_instance.get_docs_store_path.return_value = "/tmp/docs"
            mock_config_instance.get_url_config_path.return_value = "/tmp/url_config.json"
            mock_config_instance.get_rag_config_path.return_value = "/tmp/rag_config.json"
            mock_config_instance.get_gemini_file_search_api_key.return_value = "test_key"
            mock_config_instance.get_gemini_code_gen_api_key.return_value = "test_key"
            mock_config.return_value = mock_config_instance
            
            server = GeminiRAGMCPServer()
            
            # ツールを呼び出し
            result = await server.handle_upload_file_directly(
                file_path=str(unsupported_file),
                doc_type="test",
                description="Test"
            )
            
            # エラーレスポンスを検証
            assert result["success"] is False
            assert "Unsupported file extension" in result["error"]
            assert ".exe" in result["error"]
    
    @pytest.mark.asyncio
    async def test_upload_file_directly_file_too_large(self, temp_files, mock_rag_manager):
        """ファイルが大きすぎる場合、エラーが返されることを確認."""
        # RAGマネージャーがエラーを返すように設定
        mock_rag_manager.upload_file_directly.side_effect = RAGError(
            "File too large: 51.00MB. Maximum: 50MB"
        )
        
        with patch('mcp_server.get_config') as mock_config, \
             patch('mcp_server.APICrawler'), \
             patch('mcp_server.GeminiRAGManager', return_value=mock_rag_manager):
            
            # 設定のモック
            mock_config_instance = MagicMock()
            mock_config_instance.get_docs_store_path.return_value = "/tmp/docs"
            mock_config_instance.get_url_config_path.return_value = "/tmp/url_config.json"
            mock_config_instance.get_rag_config_path.return_value = "/tmp/rag_config.json"
            mock_config_instance.get_gemini_file_search_api_key.return_value = "test_key"
            mock_config_instance.get_gemini_code_gen_api_key.return_value = "test_key"
            mock_config.return_value = mock_config_instance
            
            server = GeminiRAGMCPServer()
            
            # ツールを呼び出し
            result = await server.handle_upload_file_directly(
                file_path=temp_files["large"],
                doc_type="test",
                description="Test"
            )
            
            # エラーレスポンスを検証
            assert result["success"] is False
            assert "File too large" in result["error"]
            assert "50MB" in result["error"]
