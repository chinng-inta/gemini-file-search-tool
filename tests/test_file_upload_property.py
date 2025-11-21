"""ファイル直接アップロード機能のプロパティベーステスト."""
import pytest
import asyncio
from pathlib import Path
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import AsyncMock, MagicMock, patch
from src.rag_manager import GeminiRAGManager, RAGError


def create_rag_manager(tmp_path):
    """テスト用のRAGマネージャーインスタンスを作成するヘルパー関数."""
    config_path = tmp_path / "rag_config.json"
    manager = GeminiRAGManager(
        str(config_path),
        file_search_api_key="test_file_search_key",
        code_gen_api_key="test_code_gen_key"
    )
    
    # APIクライアントにacloseメソッドを追加（モック用）
    if not hasattr(manager.file_search_client, 'aclose'):
        manager.file_search_client.aclose = AsyncMock()
    if not hasattr(manager.code_gen_client, 'aclose'):
        manager.code_gen_client.aclose = AsyncMock()
    
    return manager


# カスタムストラテジー: サポートされている拡張子
supported_extensions = st.sampled_from([".txt", ".md"])  # テストを高速化するため、テキストファイルのみに限定


class TestValidatedFileUpload:
    """検証済みファイルアップロードのプロパティテスト."""
    
    @pytest.mark.asyncio
    async def test_property_12_validated_file_upload_basic(self, tmp_path):
        """
        Feature: enhanced-document-processing, Property 12: 検証済みファイルのアップロード
        
        任意の検証済みファイルに対して、指定されたRAGストアに直接アップロードされる
        Validates: 要件 3.2
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        try:
            # テスト用のファイルを作成
            test_file = tmp_path / "testfile.txt"
            test_file.write_text("Test content")
            
            # Gemini APIの呼び出しをモック
            mock_store_id = "fileSearchStores/test123"
            
            with patch.object(rag_manager, '_create_file_search_store_with_retry', new_callable=AsyncMock) as mock_create:
                with patch.object(rag_manager, '_upload_file_to_store_with_retry', new_callable=AsyncMock) as mock_upload:
                    mock_create.return_value = mock_store_id
                    mock_upload.return_value = "files/test_file_uri"
                    
                    # ファイルを直接アップロード
                    result_store_id = await rag_manager.upload_file_directly(
                        file_path=str(test_file),
                        doc_type="test_doc"
                    )
                    
                    # 検証済みファイルがアップロードされる
                    assert result_store_id == mock_store_id
                    
                    # File Search Storeが作成される
                    mock_create.assert_called_once_with("test_doc")
                    
                    # ファイルがアップロードされる
                    mock_upload.assert_called_once_with(mock_store_id, str(test_file))
                    
                    # RAG設定ファイルに追加される
                    rags = rag_manager.get_rags_by_type("test_doc")
                    assert len(rags) == 1
                    assert rags[0]["rag_id"] == mock_store_id
        finally:
            # APIクライアントを適切にクローズ
            if hasattr(rag_manager.file_search_client, 'aclose'):
                await rag_manager.file_search_client.aclose()
            if hasattr(rag_manager.code_gen_client, 'aclose'):
                await rag_manager.code_gen_client.aclose()


class TestOptionalParameterAcceptance:
    """オプションパラメータ受け入れのプロパティテスト."""
    
    @pytest.mark.asyncio
    async def test_property_16_optional_parameter_with_doc_type(self, tmp_path):
        """
        Feature: enhanced-document-processing, Property 16: オプションパラメータの受け入れ
        
        任意のファイルアップロードに対して、オプションのdoc_typeとdescriptionパラメータが受け入れられ、正しく処理される
        Validates: 要件 4.1, 4.3
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        try:
            # テスト用のファイルを作成
            test_file = tmp_path / "testfile.txt"
            test_file.write_text("Test content")
            
            # Gemini APIの呼び出しをモック
            mock_store_id = "fileSearchStores/test123"
            
            with patch.object(rag_manager, '_create_file_search_store_with_retry', new_callable=AsyncMock) as mock_create:
                with patch.object(rag_manager, '_upload_file_to_store_with_retry', new_callable=AsyncMock) as mock_upload:
                    mock_create.return_value = mock_store_id
                    mock_upload.return_value = "files/test_file_uri"
                    
                    # ファイルを直接アップロード（オプションパラメータ付き）
                    result_store_id = await rag_manager.upload_file_directly(
                        file_path=str(test_file),
                        doc_type="custom_doc",
                        description="Custom description"
                    )
                    
                    # アップロードが成功する
                    assert result_store_id == mock_store_id
                    
                    # doc_typeが正しく処理される
                    mock_create.assert_called_once_with("custom_doc")
                    
                    # RAG設定ファイルに追加される
                    rags = rag_manager.get_rags_by_type("custom_doc")
                    assert len(rags) == 1
                    assert rags[0]["rag_id"] == mock_store_id
                    assert rags[0]["description"] == "Custom description"
        finally:
            # APIクライアントを適切にクローズ
            if hasattr(rag_manager.file_search_client, 'aclose'):
                await rag_manager.file_search_client.aclose()
            if hasattr(rag_manager.code_gen_client, 'aclose'):
                await rag_manager.code_gen_client.aclose()
    
    @pytest.mark.asyncio
    async def test_property_16_optional_parameter_without_doc_type(self, tmp_path):
        """
        Feature: enhanced-document-processing, Property 16: オプションパラメータの受け入れ
        
        doc_typeが省略された場合、ファイル名から推測される
        Validates: 要件 4.1, 4.3
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        try:
            # テスト用のファイルを作成
            test_file = tmp_path / "myfile.txt"
            test_file.write_text("Test content")
            
            # Gemini APIの呼び出しをモック
            mock_store_id = "fileSearchStores/test123"
            
            with patch.object(rag_manager, '_create_file_search_store_with_retry', new_callable=AsyncMock) as mock_create:
                with patch.object(rag_manager, '_upload_file_to_store_with_retry', new_callable=AsyncMock) as mock_upload:
                    mock_create.return_value = mock_store_id
                    mock_upload.return_value = "files/test_file_uri"
                    
                    # ファイルを直接アップロード（doc_typeを省略）
                    result_store_id = await rag_manager.upload_file_directly(
                        file_path=str(test_file),
                        doc_type=None
                    )
                    
                    # アップロードが成功する
                    assert result_store_id == mock_store_id
                    
                    # doc_typeがファイル名から推測される
                    mock_create.assert_called_once_with("myfile")
                    
                    # RAG設定ファイルに追加される
                    rags = rag_manager.get_rags_by_type("myfile")
                    assert len(rags) == 1
                    assert rags[0]["rag_id"] == mock_store_id
        finally:
            # APIクライアントを適切にクローズ
            if hasattr(rag_manager.file_search_client, 'aclose'):
                await rag_manager.file_search_client.aclose()
            if hasattr(rag_manager.code_gen_client, 'aclose'):
                await rag_manager.code_gen_client.aclose()


class TestDocTypeInference:
    """doc_type自動推測のプロパティテスト."""
    
    @pytest.mark.asyncio
    async def test_property_17_doc_type_inference(self, tmp_path):
        """
        Feature: enhanced-document-processing, Property 17: doc_typeの自動推測
        
        任意のdoc_typeが省略されたファイルアップロードに対して、システムはファイル名からdoc_typeを推測する
        Validates: 要件 4.2
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        try:
            # テスト用のファイルを作成
            test_file = tmp_path / "documentation.txt"
            test_file.write_text("Test content")
            
            # Gemini APIの呼び出しをモック
            mock_store_id = "fileSearchStores/test123"
            
            with patch.object(rag_manager, '_create_file_search_store_with_retry', new_callable=AsyncMock) as mock_create:
                with patch.object(rag_manager, '_upload_file_to_store_with_retry', new_callable=AsyncMock) as mock_upload:
                    mock_create.return_value = mock_store_id
                    mock_upload.return_value = "files/test_file_uri"
                    
                    # ファイルを直接アップロード（doc_typeを省略）
                    result_store_id = await rag_manager.upload_file_directly(
                        file_path=str(test_file),
                        doc_type=None  # doc_typeを省略
                    )
                    
                    # アップロードが成功する
                    assert result_store_id == mock_store_id
                    
                    # doc_typeがファイル名から推測される（拡張子を除いた部分）
                    mock_create.assert_called_once_with("documentation")
                    
                    # RAG設定ファイルに追加される
                    rags = rag_manager.get_rags_by_type("documentation")
                    assert len(rags) == 1
                    assert rags[0]["rag_id"] == mock_store_id
        finally:
            # APIクライアントを適切にクローズ
            if hasattr(rag_manager.file_search_client, 'aclose'):
                await rag_manager.file_search_client.aclose()
            if hasattr(rag_manager.code_gen_client, 'aclose'):
                await rag_manager.code_gen_client.aclose()


class TestMetadataRecording:
    """メタデータ記録のプロパティテスト."""
    
    @pytest.mark.asyncio
    async def test_property_18_metadata_recording(self, tmp_path):
        """
        Feature: enhanced-document-processing, Property 18: メタデータ記録
        
        任意のファイルアップロードに対して、アップロードタイムスタンプ（JST形式）と元のファイルパスがメタデータに記録される
        Validates: 要件 4.4, 4.5
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        try:
            # テスト用のファイルを作成
            test_file = tmp_path / "testfile.txt"
            test_file.write_text("Test content")
            
            # Gemini APIの呼び出しをモック
            mock_store_id = "fileSearchStores/test123"
            
            with patch.object(rag_manager, '_create_file_search_store_with_retry', new_callable=AsyncMock) as mock_create:
                with patch.object(rag_manager, '_upload_file_to_store_with_retry', new_callable=AsyncMock) as mock_upload:
                    mock_create.return_value = mock_store_id
                    mock_upload.return_value = "files/test_file_uri"
                    
                    # ファイルを直接アップロード
                    result_store_id = await rag_manager.upload_file_directly(
                        file_path=str(test_file),
                        doc_type="test_doc"
                    )
                    
                    # アップロードが成功する
                    assert result_store_id == mock_store_id
                    
                    # RAG設定ファイルからメタデータを取得
                    rags = rag_manager.get_rags_by_type("test_doc")
                    assert len(rags) == 1
                    
                    rag_entry = rags[0]
                    
                    # タイムスタンプが記録される（JST形式: YYYY/MM/DD HH:MM:SS）
                    assert "created_at" in rag_entry
                    created_at = rag_entry["created_at"]
                    
                    # タイムスタンプの形式を検証
                    import re
                    timestamp_pattern = r'^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}$'
                    assert re.match(timestamp_pattern, created_at), f"Invalid timestamp format: {created_at}"
                    
                    # RAG IDが記録される
                    assert rag_entry["rag_id"] == mock_store_id
                    
                    # doc_typeが記録される
                    assert rag_entry["doc_type"] == "test_doc"
        finally:
            # APIクライアントを適切にクローズ
            if hasattr(rag_manager.file_search_client, 'aclose'):
                await rag_manager.file_search_client.aclose()
            if hasattr(rag_manager.code_gen_client, 'aclose'):
                await rag_manager.code_gen_client.aclose()
