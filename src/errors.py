"""エラークラスの定義."""


class MCPError(Exception):
    """MCP関連のベースエラー.
    
    すべてのカスタムエラーの基底クラス。
    """
    
    def __init__(self, message: str, details: dict = None):
        """
        エラーを初期化.
        
        Args:
            message: エラーメッセージ
            details: エラーの詳細情報（オプション）
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        """エラーメッセージを文字列として返す."""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class ConfigError(MCPError):
    """設定関連のエラー.
    
    設定ファイルの読み込み、環境変数の取得、
    設定値の検証などで発生するエラー。
    """
    pass


class CrawlerError(MCPError):
    """クローラー関連のエラー.
    
    Webページの取得、HTML解析、ファイル保存、
    URL解決などで発生するエラー。
    """
    pass


class RAGError(MCPError):
    """RAG関連のエラー.
    
    Gemini APIの呼び出し、ファイルアップロード、
    RAG設定ファイルの操作などで発生するエラー。
    """
    pass
