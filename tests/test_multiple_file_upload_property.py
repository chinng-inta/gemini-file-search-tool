"""複数ファイルアップロード機能のプロパティベーステスト."""
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


class TestMultipleFilesSameStoreUpload:
    """複数ファイル同一ストアアップロードのプロパティテスト."""
    
    @pytest.mark.asyncio
    async def test_property_13_multiple_files_same_store(self, tmp_path):
        """
        Feature: enhanced-document-processing, Property 13: 複数ファイルの同一ストアアップロード
        
        任意の複数ファイルのセットに対して、すべてのファイルが同じRAGストアにアップロードされる
        Validates: 要件 3.3
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        try:
            # テスト用の複数ファイルを作成
            test_files = []
            for i in range(3):
                test_file = tmp_path / f"testfile{i}.txt"
                test_file.write_text(f"Test content {i}")
                test_files.append(str(test_file))
            
            # Gemini APIの呼び出しをモック
            mock_store_id = "fileSearchStores/test123"
            
            with patch.object(rag_manager, '_create_file_search_store_with_retry', new_callable=AsyncMock) as mock_create:
                with patch.object(rag_manager, '_upload_file_to_store_with_retry', new_callable=AsyncMock) as mock_upload:
                    mock_create.return_value = mock_store_id
                    mock_upload.return_value = "files/test_file_uri"
                    
                    # 複数ファイルを直接アップロード
                    result = await rag_manager.upload_files_directly(
                        file_paths=test_files,
                        doc_type="test_doc"
                    )
                    
                    # すべてのファイルが同じストアにアップロードされる
                    assert result["store_id"] == mock_store_id
                    assert len(result["uploaded_files"]) == 3
                    assert len(result["failed_files"]) == 0
                    
                    # File Search Storeが1回だけ作成される
                    mock_create.assert_called_once_with("test_doc")
                    
                    # すべてのファイルが同じストアにアップロードされる
                    assert mock_upload.call_count == 3
                    for call_args in mock_upload.call_args_list:
                        assert call_args[0][0] == mock_store_id  # 同じstore_idが使用される
                    
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
    
    @pytest.mark.asyncio
    async def test_property_13_multiple_files_with_different_extensions(self, tmp_path):
        """
        Feature: enhanced-document-processing, Property 13: 複数ファイルの同一ストアアップロード
        
        異なる拡張子のファイルも同じストアにアップロードされる
        Validates: 要件 3.3
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        try:
            # テスト用の複数ファイルを作成（異なる拡張子）
            test_files = []
            
            txt_file = tmp_path / "file1.txt"
            txt_file.write_text("Text content")
            test_files.append(str(txt_file))
            
            md_file = tmp_path / "file2.md"
            md_file.write_text("# Markdown content")
            test_files.append(str(md_file))
            
            # Gemini APIの呼び出しをモック
            mock_store_id = "fileSearchStores/test456"
            
            with patch.object(rag_manager, '_create_file_search_store_with_retry', new_callable=AsyncMock) as mock_create:
                with patch.object(rag_manager, '_upload_file_to_store_with_retry', new_callable=AsyncMock) as mock_upload:
                    mock_create.return_value = mock_store_id
                    mock_upload.return_value = "files/test_file_uri"
                    
                    # 複数ファイルを直接アップロード
                    result = await rag_manager.upload_files_directly(
                        file_paths=test_files,
                        doc_type="mixed_doc"
                    )
                    
                    # すべてのファイルが同じストアにアップロードされる
                    assert result["store_id"] == mock_store_id
                    assert len(result["uploaded_files"]) == 2
                    assert len(result["failed_files"]) == 0
                    
                    # File Search Storeが1回だけ作成される
                    mock_create.assert_called_once_with("mixed_doc")
                    
                    # すべてのファイルが同じストアにアップロードされる
                    assert mock_upload.call_count == 2
                    for call_args in mock_upload.call_args_list:
                        assert call_args[0][0] == mock_store_id
        finally:
            # APIクライアントを適切にクローズ
            if hasattr(rag_manager.file_search_client, 'aclose'):
                await rag_manager.file_search_client.aclose()
            if hasattr(rag_manager.code_gen_client, 'aclose'):
                await rag_manager.code_gen_client.aclose()


class TestUploadFailureContinuation:
    """アップロード失敗時継続処理のプロパティテスト."""
    
    @pytest.mark.asyncio
    async def test_property_14_upload_failure_continuation(self, tmp_path):
        """
        Feature: enhanced-document-processing, Property 14: アップロード失敗時の継続処理
        
        任意のファイルセットに対して、1つのファイルのアップロードが失敗しても、
        システムはエラーを報告し、残りのファイルの処理を続行する
        Validates: 要件 3.4
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        try:
            # テスト用の複数ファイルを作成
            test_files = []
            for i in range(3):
                test_file = tmp_path / f"testfile{i}.txt"
                test_file.write_text(f"Test content {i}")
                test_files.append(str(test_file))
            
            # Gemini APIの呼び出しをモック
            mock_store_id = "fileSearchStores/test789"
            
            with patch.object(rag_manager, '_create_file_search_store_with_retry', new_callable=AsyncMock) as mock_create:
                with patch.object(rag_manager, '_upload_file_to_store_with_retry', new_callable=AsyncMock) as mock_upload:
                    mock_create.return_value = mock_store_id
                    
                    # 2番目のファイルのアップロードを失敗させる
                    def upload_side_effect(store_id, file_path):
                        if "testfile1" in file_path:
                            raise Exception("Upload failed for testfile1")
                        return "files/test_file_uri"
                    
                    mock_upload.side_effect = upload_side_effect
                    
                    # 複数ファイルを直接アップロード
                    result = await rag_manager.upload_files_directly(
                        file_paths=test_files,
                        doc_type="test_doc"
                    )
                    
                    # 一部のファイルがアップロードされる
                    assert result["store_id"] == mock_store_id
                    assert len(result["uploaded_files"]) == 2  # testfile0とtestfile2
                    assert len(result["failed_files"]) == 1  # testfile1
                    
                    # 失敗したファイルの情報が記録される
                    failed_file = result["failed_files"][0]
                    assert "testfile1" in failed_file["file_path"]
                    assert "error" in failed_file
                    
                    # File Search Storeが1回だけ作成される
                    mock_create.assert_called_once_with("test_doc")
                    
                    # すべてのファイルに対してアップロードが試行される
                    assert mock_upload.call_count == 3
                    
                    # RAG設定ファイルに追加される（成功したファイルがあるため）
                    rags = rag_manager.get_rags_by_type("test_doc")
                    assert len(rags) == 1
                    assert rags[0]["rag_id"] == mock_store_id
        finally:
            # APIクライアントを適切にクローズ
            if hasattr(rag_manager.file_search_client, 'aclose'):
                await rag_manager.file_search_client.aclose()
            if hasattr(rag_manager.code_gen_client, 'aclose'):
                await rag_manager.code_gen_client.aclose()
    
    @pytest.mark.asyncio
    async def test_property_14_all_files_fail(self, tmp_path):
        """
        Feature: enhanced-document-processing, Property 14: アップロード失敗時の継続処理
        
        すべてのファイルのアップロードが失敗した場合、エラーが発生する
        Validates: 要件 3.4
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        try:
            # テスト用の複数ファイルを作成
            test_files = []
            for i in range(2):
                test_file = tmp_path / f"testfile{i}.txt"
                test_file.write_text(f"Test content {i}")
                test_files.append(str(test_file))
            
            # Gemini APIの呼び出しをモック
            mock_store_id = "fileSearchStores/test999"
            
            with patch.object(rag_manager, '_create_file_search_store_with_retry', new_callable=AsyncMock) as mock_create:
                with patch.object(rag_manager, '_upload_file_to_store_with_retry', new_callable=AsyncMock) as mock_upload:
                    mock_create.return_value = mock_store_id
                    
                    # すべてのファイルのアップロードを失敗させる
                    mock_upload.side_effect = Exception("Upload failed")
                    
                    # 複数ファイルを直接アップロード（エラーが発生するはず）
                    with pytest.raises(RAGError) as exc_info:
                        await rag_manager.upload_files_directly(
                            file_paths=test_files,
                            doc_type="test_doc"
                        )
                    
                    # エラーメッセージに失敗情報が含まれる
                    assert "すべてのファイルのアップロードに失敗しました" in str(exc_info.value)
        finally:
            # APIクライアントを適切にクローズ
            if hasattr(rag_manager.file_search_client, 'aclose'):
                await rag_manager.file_search_client.aclose()
            if hasattr(rag_manager.code_gen_client, 'aclose'):
                await rag_manager.code_gen_client.aclose()


class TestConfigUpdate:
    """設定更新のプロパティテスト."""
    
    @pytest.mark.asyncio
    async def test_property_15_config_update_after_upload(self, tmp_path):
        """
        Feature: enhanced-document-processing, Property 15: アップロード完了後の設定更新
        
        任意のファイルアップロード完了に対して、RAG設定ファイルが更新される
        Validates: 要件 3.5
        """
        # RAGマネージャーを作成
        rag_manager = create_rag_manager(tmp_path)
        
        try:
            # テスト用の複数ファイルを作成
            test_files = []
            for i in range(2):
                test_file = tmp_path / f"testfile{i}.txt"
                test_file.write_text(f"Test content {i}")
                test_files.append(str(test_file))
            
            # Gemini APIの呼び出しをモック
            mock_store_id = "fileSearchStores/test111"
            
            with patch.object(rag_manager, '_create_file_search_store_with_retry', new_callable=AsyncMock) as mock_create:
                with patch.object(rag_manager, '_upload_file_to_store_with_retry', new_callable=AsyncMock) as mock_upload:
                    mock_create.return_value = mock_store_id
                    mock_upload.return_value = "files/test_file_uri"
                    
                    # アップロード前の設定を確認
                    rags_before = rag_manager.get_rags_by_type("test_doc")
                    assert len(rags_before) == 0
                    
                    # 複数ファイルを直接アップロード
                    result = await rag_manager.upload_files_directly(
                        file_paths=test_files,
                        doc_type="test_doc",
                        description="Test description"
                    )
                    
                    # アップロード後の設定を確認
                    rags_after = rag_manager.get_rags_by_type("test_doc")
                    assert len(rags_after) == 1
                    
                    # RAG設定が正しく更新される
                    rag_entry = rags_after[0]
                    assert rag_entry["rag_id"] == mock_store_id
                    assert rag_entry["doc_type"] == "test_doc"
                    assert rag_entry["description"] == "Test description"
                    assert "created_at" in rag_entry
                    
                    # タイムスタンプの形式を検証（JST形式: YYYY/MM/DD HH:MM:SS）
                    import re
                    timestamp_pattern = r'^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}$'
                    assert re.match(timestamp_pattern, rag_entry["created_at"])
        finally:
            # APIクライアントを適切にクローズ
            if hasattr(rag_manager.file_search_client, 'aclose'):
                await rag_manager.file_search_client.aclose()
            if hasattr(rag_manager.code_gen_client, 'aclose'):
                await rag_manager.code_gen_client.aclose()
    
    @pytest.mark.asyncio
    async def test_property_15_config_persists_across_instances(self, tmp_path):
        """
        Feature: enhanced-document-processing, Property 15: アップロード完了後の設定更新
        
        RAG設定ファイルの更新が永続化され、新しいインスタンスでも読み込める
        Validates: 要件 3.5
        """
        # 最初のRAGマネージャーインスタンスを作成
        config_path = tmp_path / "rag_config.json"
        rag_manager1 = GeminiRAGManager(
            str(config_path),
            file_search_api_key="test_file_search_key",
            code_gen_api_key="test_code_gen_key"
        )
        
        # APIクライアントにacloseメソッドを追加
        if not hasattr(rag_manager1.file_search_client, 'aclose'):
            rag_manager1.file_search_client.aclose = AsyncMock()
        if not hasattr(rag_manager1.code_gen_client, 'aclose'):
            rag_manager1.code_gen_client.aclose = AsyncMock()
        
        try:
            # テスト用のファイルを作成
            test_file = tmp_path / "testfile.txt"
            test_file.write_text("Test content")
            
            # Gemini APIの呼び出しをモック
            mock_store_id = "fileSearchStores/test222"
            
            with patch.object(rag_manager1, '_create_file_search_store_with_retry', new_callable=AsyncMock) as mock_create:
                with patch.object(rag_manager1, '_upload_file_to_store_with_retry', new_callable=AsyncMock) as mock_upload:
                    mock_create.return_value = mock_store_id
                    mock_upload.return_value = "files/test_file_uri"
                    
                    # ファイルをアップロード
                    await rag_manager1.upload_files_directly(
                        file_paths=[str(test_file)],
                        doc_type="test_doc"
                    )
            
            # 最初のインスタンスをクローズ
            await rag_manager1.file_search_client.aclose()
            await rag_manager1.code_gen_client.aclose()
            
            # 新しいRAGマネージャーインスタンスを作成
            rag_manager2 = GeminiRAGManager(
                str(config_path),
                file_search_api_key="test_file_search_key",
                code_gen_api_key="test_code_gen_key"
            )
            
            # APIクライアントにacloseメソッドを追加
            if not hasattr(rag_manager2.file_search_client, 'aclose'):
                rag_manager2.file_search_client.aclose = AsyncMock()
            if not hasattr(rag_manager2.code_gen_client, 'aclose'):
                rag_manager2.code_gen_client.aclose = AsyncMock()
            
            try:
                # 新しいインスタンスで設定を読み込む
                rags = rag_manager2.get_rags_by_type("test_doc")
                assert len(rags) == 1
                assert rags[0]["rag_id"] == mock_store_id
            finally:
                # 2番目のインスタンスをクローズ
                await rag_manager2.file_search_client.aclose()
                await rag_manager2.code_gen_client.aclose()
                
        except Exception:
            # エラーが発生した場合もクリーンアップ
            if hasattr(rag_manager1.file_search_client, 'aclose'):
                await rag_manager1.file_search_client.aclose()
            if hasattr(rag_manager1.code_gen_client, 'aclose'):
                await rag_manager1.code_gen_client.aclose()
            raise
