"""RAGマネージャーのテスト."""
import json
import pytest
from pathlib import Path
from datetime import datetime
from src.rag_manager import GeminiRAGManager, RAGError


@pytest.fixture
def temp_config_path(tmp_path):
    """一時的なRAG設定ファイルのパスを作成."""
    config_path = tmp_path / "rag_config.json"
    return str(config_path)


@pytest.fixture
def rag_manager(temp_config_path):
    """テスト用のRAGマネージャーインスタンスを作成."""
    # テスト用のダミーAPI Keyを渡す（実際のAPIは呼び出さない）
    return GeminiRAGManager(
        temp_config_path,
        file_search_api_key="test_file_search_key",
        code_gen_api_key="test_code_gen_key"
    )


class TestLoadConfig:
    """RAG設定ファイル読み込みのテスト."""
    
    def test_load_empty_config_creates_default(self, rag_manager, temp_config_path):
        """空の設定ファイルが存在しない場合、デフォルト設定が作成されることを確認."""
        assert rag_manager.config == {"rags": {}}
        
        # ファイルが作成されたことを確認
        assert Path(temp_config_path).exists()
    
    def test_load_existing_config(self, tmp_path):
        """既存の設定ファイルが正常に読み込まれることを確認."""
        config_path = tmp_path / "rag_config.json"
        
        # 既存の設定ファイルを作成
        existing_config = {
            "rags": {
                "gemini": [
                    {
                        "rag_id": "fileSearchStores/test123",
                        "created_at": "2025-11-16T10:00:00Z",
                        "doc_type": "gemini",
                        "description": "Test RAG"
                    }
                ]
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(existing_config, f)
        
        # RAGマネージャーを初期化（テスト用のダミーAPI Key）
        manager = GeminiRAGManager(
            str(config_path),
            file_search_api_key="test_file_search_key",
            code_gen_api_key="test_code_gen_key"
        )
        
        assert "gemini" in manager.config["rags"]
        assert len(manager.config["rags"]["gemini"]) == 1
        assert manager.config["rags"]["gemini"][0]["rag_id"] == "fileSearchStores/test123"
    
    def test_load_config_invalid_json(self, tmp_path):
        """不正なJSON形式の場合、エラーが発生することを確認."""
        config_path = tmp_path / "invalid.json"
        
        with open(config_path, 'w') as f:
            f.write("{ invalid json }")
        
        with pytest.raises(RAGError) as exc_info:
            GeminiRAGManager(
                str(config_path),
                file_search_api_key="test_file_search_key",
                code_gen_api_key="test_code_gen_key"
            )
        
        assert "JSONパース" in str(exc_info.value)
    
    def test_load_config_missing_rags_key(self, tmp_path):
        """'rags'キーが存在しない場合、自動的に追加されることを確認."""
        config_path = tmp_path / "no_rags.json"
        
        with open(config_path, 'w') as f:
            json.dump({"other_key": "value"}, f)
        
        manager = GeminiRAGManager(
            str(config_path),
            file_search_api_key="test_file_search_key",
            code_gen_api_key="test_code_gen_key"
        )
        
        assert "rags" in manager.config
        assert manager.config["rags"] == {}
    
    def test_load_config_invalid_structure(self, tmp_path):
        """設定ファイルの構造が不正な場合、エラーが発生することを確認."""
        config_path = tmp_path / "invalid_structure.json"
        
        # ルートが配列の場合
        with open(config_path, 'w') as f:
            json.dump([], f)
        
        with pytest.raises(RAGError) as exc_info:
            GeminiRAGManager(
                str(config_path),
                file_search_api_key="test_file_search_key",
                code_gen_api_key="test_code_gen_key"
            )
        
        assert "形式が不正" in str(exc_info.value)


class TestSaveConfig:
    """RAG設定ファイル保存のテスト."""
    
    def test_save_config_creates_file(self, rag_manager, temp_config_path):
        """設定ファイルが正常に保存されることを確認."""
        rag_manager.config["rags"]["test"] = [{"rag_id": "test123"}]
        rag_manager._save_config()
        
        # ファイルが作成されたことを確認
        assert Path(temp_config_path).exists()
        
        # ファイル内容を確認
        with open(temp_config_path, 'r', encoding='utf-8') as f:
            saved_config = json.load(f)
        
        assert "test" in saved_config["rags"]
        assert saved_config["rags"]["test"][0]["rag_id"] == "test123"
    
    def test_save_config_creates_parent_directory(self, tmp_path):
        """親ディレクトリが存在しない場合、作成されることを確認."""
        config_path = tmp_path / "subdir" / "nested" / "rag_config.json"
        
        manager = GeminiRAGManager(
            str(config_path),
            file_search_api_key="test_file_search_key",
            code_gen_api_key="test_code_gen_key"
        )
        manager.config["rags"]["test"] = [{"rag_id": "test123"}]
        manager._save_config()
        
        # ディレクトリとファイルが作成されたことを確認
        assert config_path.parent.exists()
        assert config_path.exists()


class TestAddRAG:
    """RAG追加機能のテスト."""
    
    def test_add_rag_basic(self, rag_manager):
        """基本的なRAG追加が正常に動作することを確認."""
        rag_entry = rag_manager.add_rag(
            doc_type="gemini",
            rag_id="fileSearchStores/abc123",
            description="Gemini API Documentation"
        )
        
        assert rag_entry["rag_id"] == "fileSearchStores/abc123"
        assert rag_entry["doc_type"] == "gemini"
        assert rag_entry["description"] == "Gemini API Documentation"
        assert "created_at" in rag_entry
        
        # 設定に追加されたことを確認
        assert "gemini" in rag_manager.config["rags"]
        assert len(rag_manager.config["rags"]["gemini"]) == 1
    
    def test_add_rag_without_description(self, rag_manager):
        """説明なしでRAGを追加できることを確認."""
        rag_entry = rag_manager.add_rag(
            doc_type="gas",
            rag_id="fileSearchStores/def456"
        )
        
        assert rag_entry["rag_id"] == "fileSearchStores/def456"
        assert rag_entry["doc_type"] == "gas"
        assert "description" not in rag_entry
    
    def test_add_rag_multiple_same_type(self, rag_manager):
        """同じdoc_typeに複数のRAGを追加できることを確認."""
        rag_manager.add_rag("gemini", "fileSearchStores/abc123")
        rag_manager.add_rag("gemini", "fileSearchStores/abc456")
        
        assert len(rag_manager.config["rags"]["gemini"]) == 2
        assert rag_manager.config["rags"]["gemini"][0]["rag_id"] == "fileSearchStores/abc123"
        assert rag_manager.config["rags"]["gemini"][1]["rag_id"] == "fileSearchStores/abc456"
    
    def test_add_rag_different_types(self, rag_manager):
        """異なるdoc_typeのRAGを追加できることを確認."""
        rag_manager.add_rag("gemini", "fileSearchStores/abc123")
        rag_manager.add_rag("gas", "fileSearchStores/def456")
        
        assert "gemini" in rag_manager.config["rags"]
        assert "gas" in rag_manager.config["rags"]
        assert len(rag_manager.config["rags"]["gemini"]) == 1
        assert len(rag_manager.config["rags"]["gas"]) == 1
    
    def test_add_rag_empty_doc_type(self, rag_manager):
        """doc_typeが空の場合、エラーが発生することを確認."""
        with pytest.raises(RAGError) as exc_info:
            rag_manager.add_rag("", "fileSearchStores/abc123")
        
        assert "doc_typeは必須" in str(exc_info.value)
    
    def test_add_rag_empty_rag_id(self, rag_manager):
        """rag_idが空の場合、エラーが発生することを確認."""
        with pytest.raises(RAGError) as exc_info:
            rag_manager.add_rag("gemini", "")
        
        assert "rag_idは必須" in str(exc_info.value)
    
    def test_add_rag_created_at_format(self, rag_manager):
        """created_atがYYYY/MM/DD hh:mm:ss形式（JST）で保存されることを確認."""
        rag_entry = rag_manager.add_rag("gemini", "fileSearchStores/abc123")
        
        # YYYY/MM/DD hh:mm:ss形式であることを確認
        created_at = rag_entry["created_at"]
        assert '/' in created_at
        assert ':' in created_at
        
        # パース可能であることを確認
        datetime.strptime(created_at, '%Y/%m/%d %H:%M:%S')
    
    def test_add_rag_persists_to_file(self, rag_manager, temp_config_path):
        """RAG追加が設定ファイルに永続化されることを確認."""
        rag_manager.add_rag("gemini", "fileSearchStores/abc123")
        
        # ファイルから直接読み込んで確認
        with open(temp_config_path, 'r', encoding='utf-8') as f:
            saved_config = json.load(f)
        
        assert "gemini" in saved_config["rags"]
        assert len(saved_config["rags"]["gemini"]) == 1
        assert saved_config["rags"]["gemini"][0]["rag_id"] == "fileSearchStores/abc123"


class TestGetRAGsByType:
    """ドキュメント種類別RAG取得のテスト."""
    
    def test_get_rags_by_type_existing(self, rag_manager):
        """存在するdoc_typeのRAGを取得できることを確認."""
        rag_manager.add_rag("gemini", "fileSearchStores/abc123")
        rag_manager.add_rag("gemini", "fileSearchStores/abc456")
        
        rags = rag_manager.get_rags_by_type("gemini")
        
        assert len(rags) == 2
        assert rags[0]["rag_id"] == "fileSearchStores/abc123"
        assert rags[1]["rag_id"] == "fileSearchStores/abc456"
    
    def test_get_rags_by_type_nonexistent(self, rag_manager):
        """存在しないdoc_typeの場合、空リストが返されることを確認."""
        rags = rag_manager.get_rags_by_type("nonexistent")
        
        assert rags == []
    
    def test_get_rags_by_type_converts_non_list(self, tmp_path):
        """配列でない古い形式の設定を配列に変換することを確認."""
        config_path = tmp_path / "rag_config.json"
        
        # 古い形式の設定（配列でない）
        old_config = {
            "rags": {
                "gemini": {
                    "rag_id": "fileSearchStores/abc123",
                    "created_at": "2025-11-16T10:00:00Z",
                    "doc_type": "gemini"
                }
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(old_config, f)
        
        manager = GeminiRAGManager(
            str(config_path),
            file_search_api_key="test_file_search_key",
            code_gen_api_key="test_code_gen_key"
        )
        rags = manager.get_rags_by_type("gemini")
        
        # 配列に変換されることを確認
        assert isinstance(rags, list)
        assert len(rags) == 1
        assert rags[0]["rag_id"] == "fileSearchStores/abc123"


class TestGetAllRAGs:
    """全RAG取得のテスト."""
    
    def test_get_all_rags_empty(self, rag_manager):
        """RAGが存在しない場合、空の辞書が返されることを確認."""
        all_rags = rag_manager.get_all_rags()
        
        assert all_rags == {}
    
    def test_get_all_rags_multiple_types(self, rag_manager):
        """複数のdoc_typeのRAGを取得できることを確認."""
        rag_manager.add_rag("gemini", "fileSearchStores/abc123")
        rag_manager.add_rag("gemini", "fileSearchStores/abc456")
        rag_manager.add_rag("gas", "fileSearchStores/def789")
        
        all_rags = rag_manager.get_all_rags()
        
        assert "gemini" in all_rags
        assert "gas" in all_rags
        assert len(all_rags["gemini"]) == 2
        assert len(all_rags["gas"]) == 1
    
    def test_get_all_rags_converts_non_list(self, tmp_path):
        """配列でない古い形式の設定を配列に変換することを確認."""
        config_path = tmp_path / "rag_config.json"
        
        # 古い形式の設定（配列でない）
        old_config = {
            "rags": {
                "gemini": {
                    "rag_id": "fileSearchStores/abc123",
                    "created_at": "2025-11-16T10:00:00Z",
                    "doc_type": "gemini"
                },
                "gas": [
                    {
                        "rag_id": "fileSearchStores/def456",
                        "created_at": "2025-11-16T11:00:00Z",
                        "doc_type": "gas"
                    }
                ]
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(old_config, f)
        
        manager = GeminiRAGManager(
            str(config_path),
            file_search_api_key="test_file_search_key",
            code_gen_api_key="test_code_gen_key"
        )
        all_rags = manager.get_all_rags()
        
        # すべて配列に変換されることを確認
        assert isinstance(all_rags["gemini"], list)
        assert isinstance(all_rags["gas"], list)
        assert len(all_rags["gemini"]) == 1
        assert len(all_rags["gas"]) == 1



class TestGetLatestRAGID:
    """最新RAG ID取得のテスト."""
    
    def test_get_latest_rag_id_single(self, rag_manager):
        """単一のRAGが存在する場合、そのRAG IDが返されることを確認."""
        rag_manager.add_rag("gemini", "fileSearchStores/abc123")
        
        latest_rag_id = rag_manager.get_latest_rag_id("gemini")
        
        assert latest_rag_id == "fileSearchStores/abc123"
    
    def test_get_latest_rag_id_multiple(self, rag_manager):
        """複数のRAGが存在する場合、最新のRAG IDが返されることを確認."""
        import time
        
        # 古いRAGを追加
        rag_manager.add_rag("gemini", "fileSearchStores/old123")
        
        # 少し待機して時刻を変える
        time.sleep(1)
        
        # 新しいRAGを追加
        rag_manager.add_rag("gemini", "fileSearchStores/new456")
        
        latest_rag_id = rag_manager.get_latest_rag_id("gemini")
        
        # 最新のRAG IDが返されることを確認
        assert latest_rag_id == "fileSearchStores/new456"
    
    def test_get_latest_rag_id_nonexistent(self, rag_manager):
        """存在しないdoc_typeの場合、Noneが返されることを確認."""
        latest_rag_id = rag_manager.get_latest_rag_id("nonexistent")
        
        assert latest_rag_id is None
    
    def test_get_latest_rag_id_empty_list(self, rag_manager):
        """RAGリストが空の場合、Noneが返されることを確認."""
        # 空のリストを設定
        rag_manager.config["rags"]["gemini"] = []
        
        latest_rag_id = rag_manager.get_latest_rag_id("gemini")
        
        assert latest_rag_id is None
    
    def test_get_latest_rag_id_sorting(self, tmp_path):
        """created_atで正しくソートされることを確認."""
        config_path = tmp_path / "rag_config.json"
        
        # 異なる日時のRAGを作成（順不同）
        config = {
            "rags": {
                "gemini": [
                    {
                        "rag_id": "fileSearchStores/middle",
                        "created_at": "2025/11/15 12:00:00",
                        "doc_type": "gemini"
                    },
                    {
                        "rag_id": "fileSearchStores/latest",
                        "created_at": "2025/11/16 18:30:00",
                        "doc_type": "gemini"
                    },
                    {
                        "rag_id": "fileSearchStores/oldest",
                        "created_at": "2025/11/10 08:00:00",
                        "doc_type": "gemini"
                    }
                ]
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        manager = GeminiRAGManager(
            str(config_path),
            file_search_api_key="test_file_search_key",
            code_gen_api_key="test_code_gen_key"
        )
        latest_rag_id = manager.get_latest_rag_id("gemini")
        
        # 最新の日時のRAG IDが返されることを確認
        assert latest_rag_id == "fileSearchStores/latest"
    
    def test_get_latest_rag_id_missing_created_at(self, tmp_path):
        """created_atが欠落しているRAGがある場合の動作を確認."""
        config_path = tmp_path / "rag_config.json"
        
        config = {
            "rags": {
                "gemini": [
                    {
                        "rag_id": "fileSearchStores/no_date",
                        "doc_type": "gemini"
                        # created_atなし
                    },
                    {
                        "rag_id": "fileSearchStores/with_date",
                        "created_at": "2025/11/16 10:00:00",
                        "doc_type": "gemini"
                    }
                ]
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        manager = GeminiRAGManager(
            str(config_path),
            file_search_api_key="test_file_search_key",
            code_gen_api_key="test_code_gen_key"
        )
        latest_rag_id = manager.get_latest_rag_id("gemini")
        
        # created_atがあるRAGが返されることを確認
        assert latest_rag_id == "fileSearchStores/with_date"


class TestUploadDocuments:
    """ドキュメントアップロード機能のテスト."""
    
    @pytest.mark.asyncio
    async def test_upload_documents_basic(self, rag_manager, tmp_path, monkeypatch):
        """基本的なドキュメントアップロードが正常に動作することを確認."""
        # テスト用のファイルを作成
        test_file1 = tmp_path / "doc1.txt"
        test_file2 = tmp_path / "doc2.txt"
        test_file1.write_text("Test document 1")
        test_file2.write_text("Test document 2")
        
        # Gemini APIのモック
        class MockFile:
            def __init__(self, name):
                self.name = name
        
        class MockStore:
            def __init__(self, name):
                self.name = name
        
        class MockFiles:
            def upload(self, path):
                return MockFile(f"files/{Path(path).name}")
        
        class MockFileSearchStores:
            def create(self, display_name, file_ids):
                return MockStore("fileSearchStores/test123")
        
        class MockClient:
            def __init__(self, api_key):
                self.files = MockFiles()
                self.file_search_stores = MockFileSearchStores()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成（モックされたクライアントを使用）
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        
        # ドキュメントをアップロード
        rag_id = await manager.upload_documents(
            doc_type="test",
            file_paths=[str(test_file1), str(test_file2)],
            description="Test Documentation"
        )
        
        # RAG IDが返されることを確認
        assert rag_id == "fileSearchStores/test123"
        
        # RAG設定ファイルに追加されたことを確認
        rags = manager.get_rags_by_type("test")
        assert len(rags) == 1
        assert rags[0]["rag_id"] == "fileSearchStores/test123"
        assert rags[0]["description"] == "Test Documentation"
    
    @pytest.mark.asyncio
    async def test_upload_documents_empty_file_list(self, rag_manager):
        """ファイルリストが空の場合、エラーが発生することを確認."""
        with pytest.raises(RAGError) as exc_info:
            await rag_manager.upload_documents(
                doc_type="test",
                file_paths=[]
            )
        
        assert "ファイルが指定されていません" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_upload_documents_nonexistent_file(self, rag_manager):
        """存在しないファイルを指定した場合、エラーが発生することを確認."""
        with pytest.raises(RAGError) as exc_info:
            await rag_manager.upload_documents(
                doc_type="test",
                file_paths=["/nonexistent/file.txt"]
            )
        
        assert "ファイルが存在しません" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_upload_documents_with_retry(self, rag_manager, tmp_path, monkeypatch):
        """リトライ機能が正常に動作することを確認."""
        # テスト用のファイルを作成
        test_file = tmp_path / "doc.txt"
        test_file.write_text("Test document")
        
        # 最初の2回は失敗し、3回目で成功するモック
        upload_attempts = []
        
        class MockFile:
            def __init__(self, name):
                self.name = name
        
        class MockStore:
            def __init__(self, name):
                self.name = name
        
        class MockFiles:
            def upload(self, path):
                upload_attempts.append(1)
                if len(upload_attempts) < 3:
                    raise Exception("Upload failed")
                return MockFile(f"files/{Path(path).name}")
        
        class MockFileSearchStores:
            def create(self, display_name, file_ids):
                return MockStore("fileSearchStores/test123")
        
        class MockClient:
            def __init__(self, api_key):
                self.files = MockFiles()
                self.file_search_stores = MockFileSearchStores()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        
        # ドキュメントをアップロード
        rag_id = await manager.upload_documents(
            doc_type="test",
            file_paths=[str(test_file)]
        )
        
        # 3回試行されたことを確認
        assert len(upload_attempts) == 3
        assert rag_id == "fileSearchStores/test123"
    
    @pytest.mark.asyncio
    async def test_upload_documents_retry_exhausted(self, rag_manager, tmp_path, monkeypatch):
        """リトライが尽きた場合、エラーが発生することを確認."""
        # テスト用のファイルを作成
        test_file = tmp_path / "doc.txt"
        test_file.write_text("Test document")
        
        # 常に失敗するモック
        class MockFiles:
            def upload(self, path):
                raise Exception("Upload always fails")
        
        class MockClient:
            def __init__(self, api_key):
                self.files = MockFiles()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        
        # ドキュメントをアップロード（失敗するはず）
        with pytest.raises(RAGError) as exc_info:
            await manager.upload_documents(
                doc_type="test",
                file_paths=[str(test_file)]
            )
        
        assert "アップロードに失敗しました" in str(exc_info.value)
        assert "3回試行" in str(exc_info.value)


class TestFileLocking:
    """ファイルロック機能のテスト."""
    
    def test_concurrent_write_with_lock(self, temp_config_path):
        """複数のプロセスからの同時書き込みがロックで保護されることを確認."""
        import threading
        import time
        
        manager1 = GeminiRAGManager(
            temp_config_path,
            file_search_api_key="test_file_search_key",
            code_gen_api_key="test_code_gen_key"
        )
        manager2 = GeminiRAGManager(
            temp_config_path,
            file_search_api_key="test_file_search_key",
            code_gen_api_key="test_code_gen_key"
        )
        
        results = []
        errors = []
        
        def add_rag_thread(manager, doc_type, rag_id):
            try:
                result = manager.add_rag(doc_type, rag_id)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # 2つのスレッドで同時にRAGを追加
        thread1 = threading.Thread(target=add_rag_thread, args=(manager1, "gemini", "fileSearchStores/thread1"))
        thread2 = threading.Thread(target=add_rag_thread, args=(manager2, "gemini", "fileSearchStores/thread2"))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # エラーが発生していないことを確認
        assert len(errors) == 0
        
        # 両方のRAGが正常に追加されたことを確認
        assert len(results) == 2
        
        # 設定ファイルを再読み込みして確認
        final_manager = GeminiRAGManager(
            temp_config_path,
            file_search_api_key="test_file_search_key",
            code_gen_api_key="test_code_gen_key"
        )
        rags = final_manager.get_rags_by_type("gemini")
        
        # 2つのRAGが保存されていることを確認
        assert len(rags) == 2
        rag_ids = [rag["rag_id"] for rag in rags]
        assert "fileSearchStores/thread1" in rag_ids
        assert "fileSearchStores/thread2" in rag_ids
    
    def test_lock_timeout(self, temp_config_path, monkeypatch):
        """ロック取得がタイムアウトすることを確認."""
        import fcntl
        
        manager = GeminiRAGManager(
            temp_config_path,
            file_search_api_key="test_file_search_key",
            code_gen_api_key="test_code_gen_key"
        )
        
        # ロックを保持したままにするモック
        original_flock = fcntl.flock
        
        def mock_flock(fd, operation):
            if operation & fcntl.LOCK_NB:
                raise IOError("Resource temporarily unavailable")
            return original_flock(fd, operation)
        
        monkeypatch.setattr(fcntl, 'flock', mock_flock)
        
        # タイムアウトを短く設定してテスト
        with pytest.raises(RAGError) as exc_info:
            # _acquire_lockを直接テストするため、ファイルを開く
            with open(temp_config_path, 'r') as f:
                manager._acquire_lock(f, timeout=1)
        
        assert "タイムアウト" in str(exc_info.value)


class TestGenerateCode:
    """コード生成機能のテスト."""
    
    @pytest.mark.asyncio
    async def test_query_api_docs_basic(self, rag_manager, monkeypatch):
        """基本的なAPI問い合わせが正常に動作することを確認."""
        # RAGを追加
        rag_manager.add_rag("gemini", "fileSearchStores/test123")
        
        # Gemini APIのモック
        class MockResponse:
            def __init__(self):
                self.text = "def hello():\n    print('Hello, World!')"
        
        class MockModels:
            def generate_content(self, model, contents, config):
                return MockResponse()
        
        class MockClient:
            def __init__(self, api_key):
                self.models = MockModels()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        manager.config = rag_manager.config
        
        # APIドキュメントに問い合わせ
        code = await manager.query_api_docs(
            prompt="Create a hello world function",
            doc_type="gemini"
        )
        
        # コードが返されることを確認
        assert "hello" in code
        assert "print" in code
    
    @pytest.mark.asyncio
    async def test_query_api_docs_empty_prompt(self, rag_manager):
        """プロンプトが空の場合、エラーが発生することを確認."""
        with pytest.raises(RAGError) as exc_info:
            await rag_manager.query_api_docs(
                prompt="",
                doc_type="gemini"
            )
        
        assert "プロンプトは必須" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_query_api_docs_empty_doc_type(self, rag_manager):
        """doc_typeが空の場合、エラーが発生することを確認."""
        with pytest.raises(RAGError) as exc_info:
            await rag_manager.query_api_docs(
                prompt="Create a function",
                doc_type=""
            )
        
        assert "doc_typeは必須" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_query_api_docs_no_rag_exists(self, rag_manager):
        """RAGが存在しない場合、エラーが発生することを確認."""
        with pytest.raises(RAGError) as exc_info:
            await rag_manager.query_api_docs(
                prompt="Create a function",
                doc_type="nonexistent"
            )
        
        assert "RAGが見つかりません" in str(exc_info.value)
        assert "upload_documents" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_query_api_docs_uses_latest_rag(self, rag_manager, monkeypatch):
        """最新のRAG IDが使用されることを確認."""
        import time
        
        # 古いRAGを追加
        rag_manager.add_rag("gemini", "fileSearchStores/old123")
        time.sleep(1)
        
        # 新しいRAGを追加
        rag_manager.add_rag("gemini", "fileSearchStores/new456")
        
        # 使用されたRAG IDを記録
        used_rag_id = None
        
        class MockResponse:
            def __init__(self):
                self.text = "generated code"
        
        class MockModels:
            def generate_content(self, model, contents, config):
                nonlocal used_rag_id
                # configからRAG IDを取得
                used_rag_id = config["tools"][0]["file_search"]["file_search_store_ids"][0]
                return MockResponse()
        
        class MockClient:
            def __init__(self, api_key):
                self.models = MockModels()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        manager.config = rag_manager.config
        
        # APIドキュメントに問い合わせ
        await manager.query_api_docs(
            prompt="Create a function",
            doc_type="gemini"
        )
        
        # 最新のRAG IDが使用されたことを確認
        assert used_rag_id == "fileSearchStores/new456"
    
    @pytest.mark.asyncio
    async def test_query_api_docs_api_error(self, rag_manager, monkeypatch):
        """Gemini APIがエラーを返した場合、適切なエラーメッセージが返されることを確認."""
        # RAGを追加
        rag_manager.add_rag("gemini", "fileSearchStores/test123")
        
        # エラーを返すモック
        class MockModels:
            def generate_content(self, model, contents, config):
                raise Exception("API Error: Rate limit exceeded")
        
        class MockClient:
            def __init__(self, api_key):
                self.models = MockModels()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        manager.config = rag_manager.config
        
        # API問い合わせ（失敗するはず）
        with pytest.raises(RAGError) as exc_info:
            await manager.query_api_docs(
                prompt="Create a function",
                doc_type="gemini"
            )
        
        error_message = str(exc_info.value)
        assert "API問い合わせに失敗しました" in error_message
        assert "gemini" in error_message
        assert "fileSearchStores/test123" in error_message
    
    @pytest.mark.asyncio
    async def test_query_api_docs_empty_response(self, rag_manager, monkeypatch):
        """Gemini APIが空のレスポンスを返した場合、エラーが発生することを確認."""
        # RAGを追加
        rag_manager.add_rag("gemini", "fileSearchStores/test123")
        
        # 空のレスポンスを返すモック
        class MockResponse:
            def __init__(self):
                self.text = None
        
        class MockModels:
            def generate_content(self, model, contents, config):
                return MockResponse()
        
        class MockClient:
            def __init__(self, api_key):
                self.models = MockModels()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        manager.config = rag_manager.config
        
        # API問い合わせ（失敗するはず）
        with pytest.raises(RAGError) as exc_info:
            await manager.query_api_docs(
                prompt="Create a function",
                doc_type="gemini"
            )
        
        assert "応答が空です" in str(exc_info.value)



class TestCleanupOldRAGs:
    """古いRAG削除機能のテスト."""
    
    @pytest.mark.asyncio
    async def test_cleanup_old_rags_basic(self, rag_manager, monkeypatch):
        """基本的な古いRAG削除が正常に動作することを確認."""
        from datetime import timedelta
        
        # 現在時刻から100日前のRAGを追加
        old_date = (datetime.now(rag_manager.JST) - timedelta(days=100)).strftime('%Y/%m/%d %H:%M:%S')
        rag_manager.config["rags"]["gemini"] = [
            {
                "rag_id": "fileSearchStores/old123",
                "created_at": old_date,
                "doc_type": "gemini"
            }
        ]
        rag_manager._save_config()
        
        # Gemini APIのモック
        deleted_stores = []
        
        class MockFileSearchStores:
            def delete(self, name):
                deleted_stores.append(name)
        
        class MockClient:
            def __init__(self, api_key):
                self.file_search_stores = MockFileSearchStores()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        manager.config = rag_manager.config
        
        # 古いRAGを削除（90日以上）
        result = await manager.cleanup_old_rags(max_age_days=90)
        
        # 削除されたことを確認
        assert result["deleted_count"] == 1
        assert len(result["deleted_rags"]) == 1
        assert result["deleted_rags"][0]["rag_id"] == "fileSearchStores/old123"
        assert result["deleted_rags"][0]["age_days"] > 90
        assert len(result["errors"]) == 0
        
        # Gemini APIが呼び出されたことを確認
        assert "fileSearchStores/old123" in deleted_stores
        
        # 設定ファイルから削除されたことを確認
        assert "gemini" not in manager.config["rags"]
    
    @pytest.mark.asyncio
    async def test_cleanup_old_rags_multiple(self, rag_manager, monkeypatch):
        """複数の古いRAGを削除できることを確認."""
        from datetime import timedelta
        
        now = datetime.now(rag_manager.JST)
        
        # 異なる日付のRAGを追加
        rag_manager.config["rags"]["gemini"] = [
            {
                "rag_id": "fileSearchStores/old1",
                "created_at": (now - timedelta(days=100)).strftime('%Y/%m/%d %H:%M:%S'),
                "doc_type": "gemini"
            },
            {
                "rag_id": "fileSearchStores/old2",
                "created_at": (now - timedelta(days=95)).strftime('%Y/%m/%d %H:%M:%S'),
                "doc_type": "gemini"
            },
            {
                "rag_id": "fileSearchStores/recent",
                "created_at": (now - timedelta(days=30)).strftime('%Y/%m/%d %H:%M:%S'),
                "doc_type": "gemini"
            }
        ]
        rag_manager._save_config()
        
        # Gemini APIのモック
        deleted_stores = []
        
        class MockFileSearchStores:
            def delete(self, name):
                deleted_stores.append(name)
        
        class MockClient:
            def __init__(self, api_key):
                self.file_search_stores = MockFileSearchStores()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        manager.config = rag_manager.config
        
        # 古いRAGを削除
        result = await manager.cleanup_old_rags(max_age_days=90)
        
        # 2つのRAGが削除されたことを確認
        assert result["deleted_count"] == 2
        assert len(result["deleted_rags"]) == 2
        
        deleted_rag_ids = [rag["rag_id"] for rag in result["deleted_rags"]]
        assert "fileSearchStores/old1" in deleted_rag_ids
        assert "fileSearchStores/old2" in deleted_rag_ids
        
        # 最近のRAGは残っていることを確認
        remaining_rags = manager.get_rags_by_type("gemini")
        assert len(remaining_rags) == 1
        assert remaining_rags[0]["rag_id"] == "fileSearchStores/recent"
    
    @pytest.mark.asyncio
    async def test_cleanup_old_rags_different_doc_types(self, rag_manager, monkeypatch):
        """異なるdoc_typeの古いRAGを削除できることを確認."""
        from datetime import timedelta
        
        now = datetime.now(rag_manager.JST)
        
        # 異なるdoc_typeのRAGを追加
        rag_manager.config["rags"]["gemini"] = [
            {
                "rag_id": "fileSearchStores/gemini_old",
                "created_at": (now - timedelta(days=100)).strftime('%Y/%m/%d %H:%M:%S'),
                "doc_type": "gemini"
            }
        ]
        rag_manager.config["rags"]["gas"] = [
            {
                "rag_id": "fileSearchStores/gas_old",
                "created_at": (now - timedelta(days=95)).strftime('%Y/%m/%d %H:%M:%S'),
                "doc_type": "gas"
            }
        ]
        rag_manager._save_config()
        
        # Gemini APIのモック
        deleted_stores = []
        
        class MockFileSearchStores:
            def delete(self, name):
                deleted_stores.append(name)
        
        class MockClient:
            def __init__(self, api_key):
                self.file_search_stores = MockFileSearchStores()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        manager.config = rag_manager.config
        
        # 古いRAGを削除
        result = await manager.cleanup_old_rags(max_age_days=90)
        
        # 両方のdoc_typeのRAGが削除されたことを確認
        assert result["deleted_count"] == 2
        
        deleted_rag_ids = [rag["rag_id"] for rag in result["deleted_rags"]]
        assert "fileSearchStores/gemini_old" in deleted_rag_ids
        assert "fileSearchStores/gas_old" in deleted_rag_ids
        
        # 設定ファイルから削除されたことを確認
        assert "gemini" not in manager.config["rags"]
        assert "gas" not in manager.config["rags"]
    
    @pytest.mark.asyncio
    async def test_cleanup_old_rags_no_old_rags(self, rag_manager, monkeypatch):
        """古いRAGが存在しない場合、何も削除されないことを確認."""
        from datetime import timedelta
        
        now = datetime.now(rag_manager.JST)
        
        # 最近のRAGのみ追加
        rag_manager.config["rags"]["gemini"] = [
            {
                "rag_id": "fileSearchStores/recent",
                "created_at": (now - timedelta(days=30)).strftime('%Y/%m/%d %H:%M:%S'),
                "doc_type": "gemini"
            }
        ]
        rag_manager._save_config()
        
        # Gemini APIのモック
        deleted_stores = []
        
        class MockFileSearchStores:
            def delete(self, name):
                deleted_stores.append(name)
        
        class MockClient:
            def __init__(self, api_key):
                self.file_search_stores = MockFileSearchStores()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        manager.config = rag_manager.config
        
        # 古いRAGを削除
        result = await manager.cleanup_old_rags(max_age_days=90)
        
        # 何も削除されていないことを確認
        assert result["deleted_count"] == 0
        assert len(result["deleted_rags"]) == 0
        assert len(deleted_stores) == 0
        
        # RAGが残っていることを確認
        remaining_rags = manager.get_rags_by_type("gemini")
        assert len(remaining_rags) == 1
    
    @pytest.mark.asyncio
    async def test_cleanup_old_rags_missing_created_at(self, rag_manager, monkeypatch):
        """created_atが欠落しているRAGはスキップされることを確認."""
        from datetime import timedelta
        
        now = datetime.now(rag_manager.JST)
        
        # created_atが欠落しているRAGを追加
        rag_manager.config["rags"]["gemini"] = [
            {
                "rag_id": "fileSearchStores/no_date",
                "doc_type": "gemini"
                # created_atなし
            },
            {
                "rag_id": "fileSearchStores/old",
                "created_at": (now - timedelta(days=100)).strftime('%Y/%m/%d %H:%M:%S'),
                "doc_type": "gemini"
            }
        ]
        rag_manager._save_config()
        
        # Gemini APIのモック
        deleted_stores = []
        
        class MockFileSearchStores:
            def delete(self, name):
                deleted_stores.append(name)
        
        class MockClient:
            def __init__(self, api_key):
                self.file_search_stores = MockFileSearchStores()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        manager.config = rag_manager.config
        
        # 古いRAGを削除
        result = await manager.cleanup_old_rags(max_age_days=90)
        
        # created_atがあるRAGのみ削除されることを確認
        assert result["deleted_count"] == 1
        assert result["deleted_rags"][0]["rag_id"] == "fileSearchStores/old"
        
        # created_atがないRAGは残っていることを確認
        remaining_rags = manager.get_rags_by_type("gemini")
        assert len(remaining_rags) == 1
        assert remaining_rags[0]["rag_id"] == "fileSearchStores/no_date"
    
    @pytest.mark.asyncio
    async def test_cleanup_old_rags_invalid_date_format(self, rag_manager, monkeypatch):
        """不正な日付形式のRAGはスキップされることを確認."""
        from datetime import timedelta
        
        now = datetime.now(rag_manager.JST)
        
        # 不正な日付形式のRAGを追加
        rag_manager.config["rags"]["gemini"] = [
            {
                "rag_id": "fileSearchStores/invalid_date",
                "created_at": "invalid-date-format",
                "doc_type": "gemini"
            },
            {
                "rag_id": "fileSearchStores/old",
                "created_at": (now - timedelta(days=100)).strftime('%Y/%m/%d %H:%M:%S'),
                "doc_type": "gemini"
            }
        ]
        rag_manager._save_config()
        
        # Gemini APIのモック
        deleted_stores = []
        
        class MockFileSearchStores:
            def delete(self, name):
                deleted_stores.append(name)
        
        class MockClient:
            def __init__(self, api_key):
                self.file_search_stores = MockFileSearchStores()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        manager.config = rag_manager.config
        
        # 古いRAGを削除
        result = await manager.cleanup_old_rags(max_age_days=90)
        
        # 正しい日付形式のRAGのみ削除されることを確認
        assert result["deleted_count"] == 1
        assert result["deleted_rags"][0]["rag_id"] == "fileSearchStores/old"
        
        # 不正な日付形式のRAGは残っていることを確認
        remaining_rags = manager.get_rags_by_type("gemini")
        assert len(remaining_rags) == 1
        assert remaining_rags[0]["rag_id"] == "fileSearchStores/invalid_date"
    
    @pytest.mark.asyncio
    async def test_cleanup_old_rags_api_error(self, rag_manager, monkeypatch):
        """Gemini APIがエラーを返した場合、エラー情報が記録されることを確認."""
        from datetime import timedelta
        
        now = datetime.now(rag_manager.JST)
        
        # 古いRAGを追加
        rag_manager.config["rags"]["gemini"] = [
            {
                "rag_id": "fileSearchStores/old1",
                "created_at": (now - timedelta(days=100)).strftime('%Y/%m/%d %H:%M:%S'),
                "doc_type": "gemini"
            },
            {
                "rag_id": "fileSearchStores/old2",
                "created_at": (now - timedelta(days=95)).strftime('%Y/%m/%d %H:%M:%S'),
                "doc_type": "gemini"
            }
        ]
        rag_manager._save_config()
        
        # 最初のRAGの削除は失敗し、2番目は成功するモック
        delete_count = [0]
        
        class MockFileSearchStores:
            def delete(self, name):
                delete_count[0] += 1
                if delete_count[0] == 1:
                    raise Exception("API Error: Permission denied")
        
        class MockClient:
            def __init__(self, api_key):
                self.file_search_stores = MockFileSearchStores()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        manager.config = rag_manager.config
        
        # 古いRAGを削除
        result = await manager.cleanup_old_rags(max_age_days=90)
        
        # 1つは削除成功、1つは失敗したことを確認
        assert result["deleted_count"] == 1
        assert len(result["errors"]) == 1
        
        # エラー情報が記録されていることを確認
        error = result["errors"][0]
        assert "rag_id" in error
        assert "error" in error
        assert "Permission denied" in error["error"]
    
    @pytest.mark.asyncio
    async def test_cleanup_old_rags_custom_max_age(self, rag_manager, monkeypatch):
        """カスタムのmax_age_daysが正しく動作することを確認."""
        from datetime import timedelta
        
        now = datetime.now(rag_manager.JST)
        
        # 60日前のRAGを追加
        rag_manager.config["rags"]["gemini"] = [
            {
                "rag_id": "fileSearchStores/old",
                "created_at": (now - timedelta(days=60)).strftime('%Y/%m/%d %H:%M:%S'),
                "doc_type": "gemini"
            }
        ]
        rag_manager._save_config()
        
        # Gemini APIのモック
        deleted_stores = []
        
        class MockFileSearchStores:
            def delete(self, name):
                deleted_stores.append(name)
        
        class MockClient:
            def __init__(self, api_key):
                self.file_search_stores = MockFileSearchStores()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        manager.config = rag_manager.config
        
        # max_age_days=30で削除（60日前のRAGは削除される）
        result = await manager.cleanup_old_rags(max_age_days=30)
        
        # 削除されたことを確認
        assert result["deleted_count"] == 1
        assert result["deleted_rags"][0]["rag_id"] == "fileSearchStores/old"
    
    @pytest.mark.asyncio
    async def test_cleanup_old_rags_invalid_max_age(self, rag_manager):
        """max_age_daysが不正な値の場合、エラーが発生することを確認."""
        with pytest.raises(RAGError) as exc_info:
            await rag_manager.cleanup_old_rags(max_age_days=0)
        
        assert "正の整数" in str(exc_info.value)
        
        with pytest.raises(RAGError) as exc_info:
            await rag_manager.cleanup_old_rags(max_age_days=-10)
        
        assert "正の整数" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_cleanup_old_rags_removes_empty_doc_type(self, rag_manager, monkeypatch):
        """doc_typeのRAGがすべて削除された場合、doc_typeごと削除されることを確認."""
        from datetime import timedelta
        
        now = datetime.now(rag_manager.JST)
        
        # 古いRAGのみ追加
        rag_manager.config["rags"]["gemini"] = [
            {
                "rag_id": "fileSearchStores/old",
                "created_at": (now - timedelta(days=100)).strftime('%Y/%m/%d %H:%M:%S'),
                "doc_type": "gemini"
            }
        ]
        rag_manager._save_config()
        
        # Gemini APIのモック
        class MockFileSearchStores:
            def delete(self, name):
                pass
        
        class MockClient:
            def __init__(self, api_key):
                self.file_search_stores = MockFileSearchStores()
        
        monkeypatch.setattr("src.rag_manager.genai.Client", MockClient)
        
        # 新しいマネージャーを作成
        manager = GeminiRAGManager(
            rag_manager.config_path,
            file_search_api_key="test_key",
            code_gen_api_key="test_key"
        )
        manager.config = rag_manager.config
        
        # 古いRAGを削除
        result = await manager.cleanup_old_rags(max_age_days=90)
        
        # 削除されたことを確認
        assert result["deleted_count"] == 1
        
        # doc_typeごと削除されたことを確認
        assert "gemini" not in manager.config["rags"]
