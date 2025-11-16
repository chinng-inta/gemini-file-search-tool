"""環境変数とアプリケーション設定を管理するモジュール."""
import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    # .envファイルを自動的に読み込む
    load_dotenv()
except ImportError:
    # python-dotenvがインストールされていない場合はスキップ
    pass


class ConfigError(Exception):
    """設定関連のエラー."""
    pass


class Config:
    """アプリケーション設定を管理するクラス."""
    
    def __init__(self):
        """設定を初期化."""
        self._load_env()
        self._validate()
    
    def _load_env(self):
        """環境変数を読み込む."""
        # Gemini API Key
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # Paths
        self.rag_config_path = os.getenv(
            "RAG_CONFIG_PATH",
            "/workspace/config/rag_config.json"
        )
        self.docs_store_path = os.getenv(
            "DOCS_STORE_PATH",
            "/workspace/data/docs"
        )
        self.url_config_path = os.getenv(
            "URL_CONFIG_PATH",
            "/workspace/config/url_config.json"
        )
        
        # RAG Cleanup
        self.rag_max_age_days = int(os.getenv("RAG_MAX_AGE_DAYS", "90"))
    
    def _validate(self):
        """設定を検証."""
        if not self.gemini_api_key:
            raise ConfigError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please set it in your .env file or environment."
            )
        
        # パスの存在確認（ディレクトリは作成）
        self._ensure_directory(Path(self.docs_store_path))
        self._ensure_directory(Path(self.rag_config_path).parent)
        self._ensure_directory(Path(self.url_config_path).parent)
    
    @staticmethod
    def _ensure_directory(path: Path):
        """ディレクトリが存在することを確認し、なければ作成."""
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
    
    def get_gemini_api_key(self) -> str:
        """Gemini API Keyを取得."""
        return self.gemini_api_key
    
    def get_rag_config_path(self) -> str:
        """RAG設定ファイルのパスを取得."""
        return self.rag_config_path
    
    def get_docs_store_path(self) -> str:
        """ドキュメントストアのパスを取得."""
        return self.docs_store_path
    
    def get_url_config_path(self) -> str:
        """URL設定ファイルのパスを取得."""
        return self.url_config_path
    
    def get_rag_max_age_days(self) -> int:
        """RAGの最大保持日数を取得."""
        return self.rag_max_age_days


# グローバル設定インスタンス（遅延初期化）
_config: Optional[Config] = None


def get_config() -> Config:
    """
    グローバル設定インスタンスを取得.
    
    Returns:
        Config: 設定インスタンス
        
    Raises:
        ConfigError: 設定の初期化に失敗した場合
    """
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config():
    """グローバル設定インスタンスをリセット（主にテスト用）."""
    global _config
    _config = None
