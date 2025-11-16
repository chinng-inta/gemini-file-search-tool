"""ロギング設定モジュール."""
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
    use_stdout: bool = False
) -> logging.Logger:
    """
    アプリケーション全体のロギングを設定.
    
    Args:
        log_level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_file: ログファイルのパス（Noneの場合はコンソール出力のみ）
        log_format: ログフォーマット（Noneの場合はデフォルトフォーマット）
        use_stdout: Trueの場合は標準出力、Falseの場合は標準エラー出力
        
    Returns:
        logging.Logger: ルートロガー
        
    Raises:
        ValueError: 無効なログレベルが指定された場合
    """
    # ログレベルを検証
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    
    # デフォルトのログフォーマット
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # ルートロガーを取得
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # 既存のハンドラーをクリア
    root_logger.handlers.clear()
    
    # フォーマッターを作成
    formatter = logging.Formatter(log_format)
    
    # コンソールハンドラーを追加
    stream = sys.stdout if use_stdout else sys.stderr
    console_handler = logging.StreamHandler(stream)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # ログファイルハンドラーを追加（指定された場合）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    指定された名前のロガーを取得.
    
    Args:
        name: ロガー名（通常は__name__を使用）
        
    Returns:
        logging.Logger: ロガーインスタンス
    """
    return logging.getLogger(name)
