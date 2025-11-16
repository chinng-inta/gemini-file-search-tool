"""Gemini RAGを管理するモジュール."""
import json
import os
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
import fcntl
import asyncio
import logging
from google import genai

from src.errors import MCPError
from src.logging_config import get_logger

# ロガーの設定
logger = get_logger(__name__)


class RAGError(MCPError):
    """RAG関連のエラー.
    
    Gemini APIの呼び出し、ファイルアップロード、
    RAG設定ファイルの操作などで発生するエラー。
    """
    pass


class GeminiRAGManager:
    """Gemini RAGを管理するクラス."""
    
    # 日本標準時のタイムゾーン
    JST = timezone(timedelta(hours=9))
    
    def __init__(
        self,
        config_path: str,
        file_search_api_key: Optional[str] = None,
        code_gen_api_key: Optional[str] = None
    ):
        """
        RAGマネージャーを初期化.
        
        Args:
            config_path: RAG設定ファイルのパス
            file_search_api_key: Gemini File Search API Key（Noneの場合は環境変数GEMINI_FILE_SEARCH_API_KEYから取得）
            code_gen_api_key: Gemini Code Generation API Key（Noneの場合は環境変数GEMINI_CODE_GEN_API_KEYから取得）
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # File Search API用のクライアントを初期化
        if file_search_api_key is None:
            file_search_api_key = os.getenv("GEMINI_FILE_SEARCH_API_KEY")
        
        if not file_search_api_key:
            raise RAGError("GEMINI_FILE_SEARCH_API_KEYが設定されていません")
        
        self.file_search_client = genai.Client(api_key=file_search_api_key)
        
        # Code Generation API用のクライアントを初期化
        if code_gen_api_key is None:
            code_gen_api_key = os.getenv("GEMINI_CODE_GEN_API_KEY")
        
        if not code_gen_api_key:
            raise RAGError("GEMINI_CODE_GEN_API_KEYが設定されていません")
        
        self.code_gen_client = genai.Client(api_key=code_gen_api_key)
    
    def _acquire_lock(self, file_handle, timeout: int = 10) -> bool:
        """
        ファイルロックを取得.
        
        Args:
            file_handle: ファイルハンドル
            timeout: タイムアウト時間（秒）
            
        Returns:
            bool: ロック取得に成功した場合True
            
        Raises:
            RAGError: ロック取得に失敗した場合
        """
        start_time = time.time()
        while True:
            try:
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except (IOError, OSError):
                if time.time() - start_time >= timeout:
                    raise RAGError(f"ファイルロックの取得がタイムアウトしました（{timeout}秒）")
                time.sleep(0.1)
    
    def _release_lock(self, file_handle):
        """
        ファイルロックを解放.
        
        Args:
            file_handle: ファイルハンドル
        """
        try:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
        except (IOError, OSError):
            pass
    
    def _load_config(self, with_lock: bool = True) -> dict:
        """
        RAG設定ファイルを読み込む.
        
        Args:
            with_lock: ロックを取得するかどうか（デフォルト: True）
        
        Returns:
            dict: RAG設定データ
            
        Raises:
            RAGError: 設定ファイルの読み込みに失敗した場合
        """
        config_file = Path(self.config_path)
        
        # ファイルが存在しない場合は空の設定を作成
        if not config_file.exists():
            default_config = {"rags": {}}
            self._save_config(default_config)
            return default_config
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if with_lock:
                    # 読み取りロックを取得
                    self._acquire_lock(f)
                try:
                    config = json.load(f)
                finally:
                    if with_lock:
                        self._release_lock(f)
                
            # 設定ファイルの構造を検証
            if not isinstance(config, dict):
                raise RAGError("RAG設定ファイルの形式が不正です: ルートがdictではありません")
            
            if "rags" not in config:
                config["rags"] = {}
            
            if not isinstance(config["rags"], dict):
                raise RAGError("RAG設定ファイルの形式が不正です: 'rags'がdictではありません")
            
            return config
            
        except json.JSONDecodeError as e:
            raise RAGError(f"RAG設定ファイルのJSONパースに失敗しました: {e}")
        except RAGError:
            raise
        except Exception as e:
            raise RAGError(f"RAG設定ファイルの読み込みに失敗しました: {e}")
    
    def _save_config(self, config: Optional[dict] = None):
        """
        RAG設定ファイルを保存.
        
        Args:
            config: 保存する設定データ（Noneの場合は現在の設定を保存）
            
        Raises:
            RAGError: 設定ファイルの保存に失敗した場合
        """
        if config is None:
            config = self.config
        
        config_file = Path(self.config_path)
        
        # 親ディレクトリが存在しない場合は作成
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 書き込みロックを取得して保存
            with open(config_file, 'w', encoding='utf-8') as f:
                self._acquire_lock(f)
                try:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    self._release_lock(f)
        except RAGError:
            raise
        except Exception as e:
            raise RAGError(f"RAG設定ファイルの保存に失敗しました: {e}")

    def add_rag(
        self,
        doc_type: str,
        rag_id: str,
        description: Optional[str] = None
    ) -> dict:
        """
        RAG設定ファイルに新しいRAGを追加.
        
        Args:
            doc_type: ドキュメントの種類（例: 'gemini', 'gas'）
            rag_id: RAG ID（例: 'fileSearchStores/abc123xyz'）
            description: RAGの説明（オプション）
            
        Returns:
            dict: 追加されたRAGエントリ
            
        Raises:
            RAGError: RAGの追加に失敗した場合
        """
        if not doc_type:
            raise RAGError("doc_typeは必須です")
        
        if not rag_id:
            raise RAGError("rag_idは必須です")
        
        # 現在時刻をJST（日本標準時）で取得し、YYYY/MM/DD hh:mm:ss形式で保存
        created_at = datetime.now(self.JST).strftime('%Y/%m/%d %H:%M:%S')
        
        # 新しいRAGエントリを作成
        rag_entry = {
            "rag_id": rag_id,
            "created_at": created_at,
            "doc_type": doc_type
        }
        
        if description:
            rag_entry["description"] = description
        
        config_file = Path(self.config_path)
        
        # ファイルロックを取得して、読み込み→更新→保存を原子的に実行
        try:
            # 'r+'モードでファイルを開く（読み書き両用）
            # ファイルが存在しない場合は作成
            if not config_file.exists():
                config_file.parent.mkdir(parents=True, exist_ok=True)
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump({"rags": {}}, f)
            
            with open(config_file, 'r+', encoding='utf-8') as f:
                # 排他ロックを取得
                self._acquire_lock(f)
                try:
                    # ファイルの先頭から読み込み
                    f.seek(0)
                    content = f.read()
                    if content:
                        config = json.loads(content)
                    else:
                        config = {"rags": {}}
                    
                    # 設定ファイルの構造を検証
                    if not isinstance(config, dict):
                        config = {"rags": {}}
                    if "rags" not in config:
                        config["rags"] = {}
                    if not isinstance(config["rags"], dict):
                        config["rags"] = {}
                    
                    # doc_typeの配列が存在しない場合は作成
                    if doc_type not in config["rags"]:
                        config["rags"][doc_type] = []
                    
                    # 配列形式でRAGを管理
                    if not isinstance(config["rags"][doc_type], list):
                        # 既存の設定が配列でない場合は配列に変換
                        old_entry = config["rags"][doc_type]
                        config["rags"][doc_type] = [old_entry]
                    
                    # 新しいRAGを配列に追加
                    config["rags"][doc_type].append(rag_entry)
                    
                    # ファイルの先頭に戻って書き込み
                    f.seek(0)
                    f.truncate()
                    json.dump(config, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                    
                    # メモリ上の設定も更新
                    self.config = config
                    
                finally:
                    self._release_lock(f)
                    
        except RAGError:
            raise
        except Exception as e:
            raise RAGError(f"RAGの追加に失敗しました: {e}")
        
        return rag_entry
    
    def get_rags_by_type(self, doc_type: str) -> list[dict]:
        """
        指定されたドキュメント種類のすべてのRAGを取得.
        
        Args:
            doc_type: ドキュメントの種類
            
        Returns:
            list[dict]: RAGエントリのリスト（存在しない場合は空リスト）
        """
        if doc_type not in self.config["rags"]:
            return []
        
        rags = self.config["rags"][doc_type]
        
        # 配列でない場合は配列に変換
        if not isinstance(rags, list):
            return [rags]
        
        return rags
    
    def get_all_rags(self) -> dict[str, list[dict]]:
        """
        すべてのRAGを取得.
        
        Returns:
            dict[str, list[dict]]: ドキュメント種類をキーとしたRAGエントリのリスト
        """
        result = {}
        
        for doc_type, rags in self.config["rags"].items():
            if isinstance(rags, list):
                result[doc_type] = rags
            else:
                result[doc_type] = [rags]
        
        return result
    
    def get_latest_rag_id(self, doc_type: str) -> Optional[str]:
        """
        指定されたドキュメント種類の最新のRAG IDを取得.
        
        Args:
            doc_type: ドキュメントの種類
            
        Returns:
            Optional[str]: 最新のRAG ID、存在しない場合はNone
        """
        rags = self.get_rags_by_type(doc_type)
        
        if not rags:
            return None
        
        # created_atでソート（降順）して最新のRAGを取得
        # created_atは 'YYYY/MM/DD HH:MM:SS' 形式なので文字列比較で正しくソートできる
        sorted_rags = sorted(rags, key=lambda x: x.get("created_at", ""), reverse=True)
        
        return sorted_rags[0].get("rag_id")
    
    async def _create_file_search_store_with_retry(
        self,
        doc_type: str,
        max_retries: int = 3
    ) -> str:
        """
        File Search Storeを作成（リトライ付き）.
        
        Args:
            doc_type: ドキュメントの種類
            max_retries: 最大リトライ回数（デフォルト: 3）
            
        Returns:
            str: 作成されたFile Search StoreのID
            
        Raises:
            RAGError: 作成に失敗した場合
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # File Search Storeを作成
                # Gemini APIではdisplay_nameではなく、引数なしで作成
                store = await asyncio.to_thread(
                    self.file_search_client.file_search_stores.create
                )
                
                return store.name
                
            except Exception as e:
                last_error = e
                
                # 最後の試行でない場合は指数バックオフで待機
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1秒、2秒、4秒...
                    await asyncio.sleep(wait_time)
        
        # すべてのリトライが失敗した場合
        raise RAGError(
            f"File Search Storeの作成に失敗しました（{max_retries}回試行）\n"
            f"エラー: {last_error}"
        )
    
    async def _upload_file_to_store_with_retry(
        self,
        store_id: str,
        file_path: str,
        max_retries: int = 3
    ) -> str:
        """
        ファイルをFile Search Storeにアップロード（リトライ付き）.
        
        Args:
            store_id: File Search StoreのID
            file_path: アップロードするファイルのパス
            max_retries: 最大リトライ回数（デフォルト: 3）
            
        Returns:
            str: アップロードされたファイルのURI
            
        Raises:
            RAGError: アップロードに失敗した場合
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # ファイルをFile Search Storeにアップロード
                # Gemini APIではファイルパスを直接指定する
                operation = await asyncio.to_thread(
                    self.file_search_client.file_search_stores.upload_to_file_search_store,
                    file_search_store_name=store_id,
                    file=file_path
                )
                
                # アップロード処理の完了を待つ
                logger.info(f"Waiting for file processing to complete: {file_path}")
                await self._wait_for_operation(operation)
                logger.info(f"File processing completed: {file_path}")
                
                return operation.name
                
            except Exception as e:
                last_error = e
                
                # 最後の試行でない場合は指数バックオフで待機
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1秒、2秒、4秒...
                    await asyncio.sleep(wait_time)
        
        # すべてのリトライが失敗した場合
        raise RAGError(
            f"ファイルのアップロードに失敗しました（{max_retries}回試行）: {file_path}\n"
            f"エラー: {last_error}"
        )
    
    async def _wait_for_operation(
        self,
        operation,
        timeout: int = 300,
        poll_interval: int = 2
    ):
        """
        オペレーションの完了を待つ.
        
        Args:
            operation: Gemini APIのオペレーションオブジェクト
            timeout: タイムアウト時間（秒、デフォルト: 300秒 = 5分）
            poll_interval: ポーリング間隔（秒、デフォルト: 2秒）
            
        Raises:
            RAGError: タイムアウトまたはオペレーションが失敗した場合
        """
        start_time = time.time()
        
        while True:
            # タイムアウトチェック
            if time.time() - start_time > timeout:
                raise RAGError(
                    f"オペレーションがタイムアウトしました（{timeout}秒）"
                )
            
            # オペレーションの状態を確認
            if hasattr(operation, 'done') and operation.done:
                logger.info("Operation completed successfully")
                return
            
            # まだ完了していない場合は待機
            logger.debug(f"Operation still processing... (elapsed: {int(time.time() - start_time)}s)")
            await asyncio.sleep(poll_interval)
    
    async def upload_documents(
        self,
        doc_type: str,
        file_paths: list[str],
        description: Optional[str] = None
    ) -> str:
        """
        ドキュメントをGemini RAGにアップロード.
        
        Args:
            doc_type: ドキュメントの種類（例: 'gemini', 'gas'）
            file_paths: アップロードするファイルパスのリスト
            description: RAGの説明（オプション）
            
        Returns:
            str: 作成されたRAG ID
            
        Raises:
            RAGError: アップロードに失敗した場合
        """
        if not file_paths:
            raise RAGError("アップロードするファイルが指定されていません")
        
        # ファイルの存在確認
        for file_path in file_paths:
            if not Path(file_path).exists():
                raise RAGError(f"ファイルが存在しません: {file_path}")
        
        try:
            # File Search Storeを作成
            logger.info(f"Creating File Search Store for {doc_type}...")
            store_id = await self._create_file_search_store_with_retry(doc_type)
            logger.info(f"File Search Store created: {store_id}")
            
            # すべてのファイルをFile Search Storeにアップロード
            logger.info(f"Uploading {len(file_paths)} files to File Search Store...")
            for i, file_path in enumerate(file_paths, 1):
                logger.info(f"Uploading file {i}/{len(file_paths)}: {file_path}")
                await self._upload_file_to_store_with_retry(store_id, file_path)
            
            logger.info(f"All files uploaded successfully to {store_id}")
            
            # RAG設定ファイルに追加
            self.add_rag(
                doc_type=doc_type,
                rag_id=store_id,
                description=description or f"{doc_type} API Documentation"
            )
            
            return store_id
            
        except RAGError:
            raise
        except Exception as e:
            raise RAGError(f"ドキュメントのアップロードに失敗しました: {e}")
    
    def _git_pull(self) -> bool:
        """
        Git pullを実行してドキュメントを最新化.
        
        Returns:
            bool: 成功した場合True
        """
        try:
            # プロジェクトルートを取得
            project_root = Path(self.config_path).parent.parent
            
            logger.info("Executing git pull to update documents...")
            result = subprocess.run(
                ['git', 'pull'],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Git pull successful: {result.stdout.strip()}")
                return True
            else:
                logger.warning(f"Git pull failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.warning("Git pull timed out")
            return False
        except Exception as e:
            logger.warning(f"Git pull error: {e}")
            return False
    
    async def generate_code(
        self,
        prompt: str,
        doc_type: str,
        model: str = "gemini-2.0-flash-exp"
    ) -> str:
        """
        APIドキュメントに基づいてコードを生成.
        
        Args:
            prompt: コード生成プロンプト
            doc_type: 参照するドキュメントの種類（例: 'gemini', 'gas'）
            model: 使用するGeminiモデル（デフォルト: gemini-2.0-flash-exp）
            
        Returns:
            str: 生成されたコード
            
        Raises:
            RAGError: コード生成に失敗した場合
        """
        if not prompt:
            raise RAGError("プロンプトは必須です")
        
        if not doc_type:
            raise RAGError("doc_typeは必須です")
        
        # Git pullを実行してドキュメントを最新化
        self._git_pull()
        
        # 最新のRAG IDを取得
        rag_id = self.get_latest_rag_id(doc_type)
        
        if not rag_id:
            raise RAGError(
                f"ドキュメント種類 '{doc_type}' のRAGが見つかりません。"
                f"先にupload_documentsを実行してください。"
            )
        
        # システムプロンプトを設定
        system_prompt = """あなたは優秀なソフトウェアエンジニアです。
提供されたAPIドキュメントに基づいて、正確で実用的なコードを生成してください。

コード生成時の要件:
1. エラーハンドリングを適切に実装する
2. コードにコメントを含める（日本語または英語）
3. ベストプラクティスに従う
4. 可読性の高いコードを書く
5. 必要に応じて使用例を含める
6. APIドキュメントの仕様に正確に従う

生成するコードは、すぐに実行可能な状態にしてください。"""
        
        try:
            # Gemini APIを呼び出してコードを生成（Code Generation API用クライアントを使用）
            response = await asyncio.to_thread(
                self.code_gen_client.models.generate_content,
                model=model,
                contents=prompt,
                config={
                    "system_instruction": system_prompt,
                    "tools": [
                        {
                            "file_search": {
                                "file_search_store_ids": [rag_id]
                            }
                        }
                    ]
                }
            )
            
            # レスポンスからテキストを抽出
            if not response or not response.text:
                raise RAGError("Gemini APIからの応答が空です")
            
            return response.text
            
        except RAGError:
            raise
        except Exception as e:
            raise RAGError(
                f"コード生成に失敗しました: {e}\n"
                f"モデル: {model}\n"
                f"ドキュメント種類: {doc_type}\n"
                f"RAG ID: {rag_id}"
            )
    
    async def cleanup_old_rags(self, max_age_days: int = 90) -> dict:
        """
        古いRAGを削除.
        
        Args:
            max_age_days: RAGの最大保持日数（デフォルト: 90日）
            
        Returns:
            dict: 削除結果の情報
                - deleted_count: 削除されたRAGの数
                - deleted_rags: 削除されたRAGのリスト
                - errors: 削除中に発生したエラーのリスト
                
        Raises:
            RAGError: クリーンアップ処理に失敗した場合
        """
        if max_age_days <= 0:
            raise RAGError("max_age_daysは正の整数である必要があります")
        
        # 現在時刻（JST）を取得
        now = datetime.now(self.JST)
        
        # 削除対象のRAGを収集
        rags_to_delete = []
        
        for doc_type, rags in self.config["rags"].items():
            # 配列でない場合は配列に変換
            if not isinstance(rags, list):
                rags = [rags]
            
            for rag in rags:
                created_at_str = rag.get("created_at", "")
                
                if not created_at_str:
                    # created_atが存在しない場合はスキップ
                    continue
                
                try:
                    # created_atをパース（YYYY/MM/DD HH:MM:SS形式）
                    created_at = datetime.strptime(created_at_str, '%Y/%m/%d %H:%M:%S')
                    # JSTタイムゾーンを設定
                    created_at = created_at.replace(tzinfo=self.JST)
                    
                    # 経過日数を計算
                    age_days = (now - created_at).days
                    
                    # max_age_daysを超えている場合は削除対象に追加
                    if age_days > max_age_days:
                        rags_to_delete.append({
                            "doc_type": doc_type,
                            "rag_id": rag.get("rag_id"),
                            "created_at": created_at_str,
                            "age_days": age_days
                        })
                
                except ValueError:
                    # 日付のパースに失敗した場合はスキップ
                    continue
        
        # 削除処理を実行
        deleted_rags = []
        errors = []
        
        for rag_info in rags_to_delete:
            rag_id = rag_info["rag_id"]
            doc_type = rag_info["doc_type"]
            
            try:
                # Gemini APIでRAGを削除（File Search API用クライアントを使用）
                await asyncio.to_thread(
                    self.file_search_client.file_search_stores.delete,
                    name=rag_id
                )
                
                # RAG設定ファイルから削除
                self._remove_rag_from_config(doc_type, rag_id)
                
                deleted_rags.append(rag_info)
                
            except Exception as e:
                errors.append({
                    "rag_id": rag_id,
                    "doc_type": doc_type,
                    "error": str(e)
                })
        
        return {
            "deleted_count": len(deleted_rags),
            "deleted_rags": deleted_rags,
            "errors": errors
        }
    
    def _remove_rag_from_config(self, doc_type: str, rag_id: str):
        """
        RAG設定ファイルから指定されたRAGを削除.
        
        Args:
            doc_type: ドキュメントの種類
            rag_id: 削除するRAG ID
            
        Raises:
            RAGError: RAGの削除に失敗した場合
        """
        config_file = Path(self.config_path)
        
        try:
            # ファイルロックを取得して、読み込み→更新→保存を原子的に実行
            with open(config_file, 'r+', encoding='utf-8') as f:
                # 排他ロックを取得
                self._acquire_lock(f)
                try:
                    # ファイルの先頭から読み込み
                    f.seek(0)
                    content = f.read()
                    if content:
                        config = json.loads(content)
                    else:
                        config = {"rags": {}}
                    
                    # doc_typeが存在しない場合は何もしない
                    if doc_type not in config["rags"]:
                        return
                    
                    rags = config["rags"][doc_type]
                    
                    # 配列でない場合は配列に変換
                    if not isinstance(rags, list):
                        rags = [rags]
                    
                    # 指定されたRAG IDを除外
                    filtered_rags = [rag for rag in rags if rag.get("rag_id") != rag_id]
                    
                    # 空になった場合はdoc_typeごと削除
                    if not filtered_rags:
                        del config["rags"][doc_type]
                    else:
                        config["rags"][doc_type] = filtered_rags
                    
                    # ファイルの先頭に戻って書き込み
                    f.seek(0)
                    f.truncate()
                    json.dump(config, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                    
                    # メモリ上の設定も更新
                    self.config = config
                    
                finally:
                    self._release_lock(f)
                    
        except RAGError:
            raise
        except Exception as e:
            raise RAGError(f"RAGの削除に失敗しました: {e}")
