"""Gemini RAG MCPサーバー."""
import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Optional

# .envファイルを最初に読み込む（他のインポートより前）
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path, override=True)
except ImportError:
    pass

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.config import get_config, ConfigError
from src.crawler import APICrawler, CrawlerError
from src.rag_manager import GeminiRAGManager, RAGError
from src.errors import MCPError
from src.logging_config import setup_logging, get_logger


logger = get_logger(__name__)


class GeminiRAGMCPServer:
    """MCP Protocol準拠のサーバー."""
    
    def __init__(self):
        """MCPサーバーを初期化."""
        try:
            # 設定を読み込む
            config = get_config()
            
            # APIクローラーを初期化
            self.crawler = APICrawler(
                docs_path=config.get_docs_store_path(),
                url_config_path=config.get_url_config_path(),
                auto_git_push=True
            )
            
            # Gemini RAGマネージャーを初期化
            self.rag_manager = GeminiRAGManager(
                config_path=config.get_rag_config_path(),
                file_search_api_key=config.get_gemini_file_search_api_key(),
                code_gen_api_key=config.get_gemini_code_gen_api_key()
            )
            
            # MCPサーバーを初期化
            self.server = Server("gemini-rag-mcp")
            
            # ツールハンドラーを登録
            self._register_handlers()
            
            logger.info("Gemini RAG MCPサーバーを初期化しました")
            
        except (ConfigError, CrawlerError, RAGError) as e:
            logger.error(f"MCPサーバーの初期化に失敗しました: {e}")
            raise MCPError(f"Failed to initialize MCP server: {e}")
    
    def _register_handlers(self):
        """ツールハンドラーを登録."""
        # ツールリストハンドラー
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """利用可能なツールのリストを返す."""
            return [
                Tool(
                    name="crawl_api_docs",
                    description="APIドキュメントをクロールします。キーワードまたはURLを指定できます。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "keyword_or_url": {
                                "type": "string",
                                "description": "APIドキュメントのキーワード（例: 'gemini', 'gas'）またはURL"
                            },
                            "max_depth": {
                                "type": "integer",
                                "description": "クロールの最大深度（デフォルト: 3）",
                                "default": 3
                            }
                        },
                        "required": ["keyword_or_url"]
                    }
                ),
                Tool(
                    name="list_api_docs",
                    description="登録されているAPIドキュメントの一覧を返します。",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="list_crawled_files",
                    description="クロール済みのドキュメントファイル一覧を返します。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "doc_type": {
                                "type": "string",
                                "description": "ドキュメントの種類（省略時は全ファイル）"
                            }
                        }
                    }
                ),
                Tool(
                    name="upload_documents",
                    description="クロールしたドキュメントをGemini RAGにアップロードします。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "doc_type": {
                                "type": "string",
                                "description": "ドキュメントの種類（例: 'gemini', 'gas'）"
                            }
                        },
                        "required": ["doc_type"]
                    }
                ),
                Tool(
                    name="generate_code",
                    description="APIドキュメントに基づいてコードを生成します。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "コード生成のプロンプト"
                            },
                            "doc_type": {
                                "type": "string",
                                "description": "参照するドキュメントの種類（例: 'gemini', 'gas'）"
                            }
                        },
                        "required": ["prompt", "doc_type"]
                    }
                ),
                Tool(
                    name="list_uploaded_rags",
                    description="アップロード済みのRAG一覧を取得します。doc_typeを指定すると特定の種類のRAGのみを取得できます。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "doc_type": {
                                "type": "string",
                                "description": "ドキュメントの種類（省略時は全RAGを取得）"
                            }
                        }
                    }
                ),
                Tool(
                    name="upload_file_directly",
                    description="ローカルファイルを直接RAGにアップロードします。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "アップロードするファイルのパス"
                            },
                            "doc_type": {
                                "type": "string",
                                "description": "ドキュメントの種類（省略時はファイル名から推測）"
                            },
                            "description": {
                                "type": "string",
                                "description": "RAGの説明"
                            }
                        },
                        "required": ["file_path"]
                    }
                )
            ]
        
        # ツール呼び出しハンドラー
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """ツールを呼び出す."""
            try:
                if name == "crawl_api_docs":
                    result = await self.handle_crawl_api_docs(
                        keyword_or_url=arguments.get("keyword_or_url"),
                        max_depth=arguments.get("max_depth", 3)
                    )
                elif name == "list_api_docs":
                    result = await self.handle_list_api_docs()
                elif name == "list_crawled_files":
                    result = await self.handle_list_crawled_files(
                        doc_type=arguments.get("doc_type")
                    )
                elif name == "upload_documents":
                    result = await self.handle_upload_documents(
                        doc_type=arguments.get("doc_type")
                    )
                elif name == "generate_code":
                    result = await self.handle_generate_code(
                        prompt=arguments.get("prompt"),
                        doc_type=arguments.get("doc_type")
                    )
                elif name == "list_uploaded_rags":
                    result = await self.handle_list_uploaded_rags(
                        doc_type=arguments.get("doc_type")
                    )
                elif name == "upload_file_directly":
                    result = await self.handle_upload_file_directly(
                        file_path=arguments.get("file_path"),
                        doc_type=arguments.get("doc_type"),
                        description=arguments.get("description")
                    )
                else:
                    raise MCPError(f"Unknown tool: {name}")
                
                return [TextContent(type="text", text=str(result))]
                
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                error_message = f"Error: {str(e)}"
                return [TextContent(type="text", text=error_message)]
    
    async def handle_crawl_api_docs(
        self,
        keyword_or_url: str,
        max_depth: int = 3
    ) -> dict:
        """
        APIドキュメントをクロール.
        
        Args:
            keyword_or_url: APIドキュメントのキーワードまたはURL
            max_depth: クロールの最大深度
            
        Returns:
            dict: クロール結果
        """
        try:
            # URLを解決
            url = self.crawler.resolve_url(keyword_or_url)
            logger.info(f"Crawling API docs: {url}")
            
            # クロールを実行
            file_paths = await self.crawler.crawl(url, max_depth=max_depth)
            
            return {
                "success": True,
                "message": f"Successfully crawled {len(file_paths)} pages",
                "url": url,
                "file_count": len(file_paths),
                "file_paths": file_paths
            }
            
        except CrawlerError as e:
            logger.error(f"Crawler error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.exception("Unexpected error during crawl")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def handle_list_api_docs(self) -> dict:
        """
        登録されたAPIドキュメント一覧を返す.
        
        Returns:
            dict: APIドキュメント一覧
        """
        try:
            apis = self.crawler.list_available_apis()
            
            return {
                "success": True,
                "apis": apis,
                "count": len(apis)
            }
            
        except Exception as e:
            logger.exception("Unexpected error while listing API docs")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def handle_list_crawled_files(self, doc_type: str = None) -> dict:
        """
        クロール済みのドキュメントファイル一覧を返す.
        
        Args:
            doc_type: ドキュメントの種類（省略時は全ファイル）
            
        Returns:
            dict: ファイル一覧
        """
        try:
            docs_path = Path(self.crawler.docs_path)
            
            if not docs_path.exists():
                return {
                    "success": True,
                    "files": [],
                    "count": 0,
                    "message": "No documents directory found"
                }
            
            files_info = []
            
            if doc_type:
                # 特定のdoc_typeのファイルのみ
                # パターン1: ディレクトリ形式
                docs_dir = docs_path / doc_type
                if docs_dir.exists() and docs_dir.is_dir():
                    for file_path in docs_dir.glob("**/*.txt"):
                        if file_path.is_file():
                            files_info.append({
                                "path": str(file_path),
                                "name": file_path.name,
                                "size": file_path.stat().st_size,
                                "doc_type": doc_type
                            })
                
                # パターン2: 単一ファイル形式
                single_file = docs_path / f"{doc_type}.txt"
                if single_file.exists() and single_file.is_file():
                    files_info.append({
                        "path": str(single_file),
                        "name": single_file.name,
                        "size": single_file.stat().st_size,
                        "doc_type": doc_type
                    })
            else:
                # 全ファイル
                for file_path in docs_path.glob("**/*.txt"):
                    if file_path.is_file():
                        # doc_typeを推測
                        if file_path.parent == docs_path:
                            # 単一ファイル形式
                            inferred_doc_type = file_path.stem
                        else:
                            # ディレクトリ形式
                            inferred_doc_type = file_path.parent.name
                        
                        files_info.append({
                            "path": str(file_path),
                            "name": file_path.name,
                            "size": file_path.stat().st_size,
                            "doc_type": inferred_doc_type
                        })
            
            return {
                "success": True,
                "files": files_info,
                "count": len(files_info),
                "doc_type_filter": doc_type
            }
            
        except Exception as e:
            logger.exception("Unexpected error while listing crawled files")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def handle_upload_documents(self, doc_type: str) -> dict:
        """
        ドキュメントをGemini RAGにアップロード.
        
        Args:
            doc_type: ドキュメントの種類
            
        Returns:
            dict: アップロード結果
        """
        try:
            # パラメータ検証
            if not doc_type:
                return {
                    "success": False,
                    "error": "doc_type is required"
                }
            
            # ドキュメントストアからファイルを読み込む
            # 2つのパターンをサポート:
            # 1. docs_path/{doc_type}/ ディレクトリ内の複数ファイル
            # 2. docs_path/{doc_type}.txt 単一ファイル
            
            file_paths = []
            
            # パターン1: ディレクトリ形式
            docs_dir = Path(self.crawler.docs_path) / doc_type
            if docs_dir.exists() and docs_dir.is_dir():
                for file_path in docs_dir.glob("**/*.txt"):
                    if file_path.is_file():
                        file_paths.append(str(file_path))
            
            # パターン2: 単一ファイル形式
            single_file = Path(self.crawler.docs_path) / f"{doc_type}.txt"
            if single_file.exists() and single_file.is_file():
                file_paths.append(str(single_file))
            
            if not file_paths:
                return {
                    "success": False,
                    "error": f"No documents found for type: {doc_type}. Please crawl documents first."
                }
            
            logger.info(f"Uploading {len(file_paths)} documents for type: {doc_type}")
            
            # Gemini RAGマネージャーを呼び出してアップロード
            rag_id = await self.rag_manager.upload_documents(
                doc_type=doc_type,
                file_paths=file_paths,
                description=f"{doc_type} API Documentation"
            )
            
            return {
                "success": True,
                "message": f"Successfully uploaded {len(file_paths)} documents",
                "doc_type": doc_type,
                "file_count": len(file_paths),
                "rag_id": rag_id
            }
            
        except RAGError as e:
            logger.error(f"RAG error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.exception("Unexpected error during document upload")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def handle_generate_code(self, prompt: str, doc_type: str) -> dict:
        """
        コードを生成.
        
        Args:
            prompt: コード生成プロンプト
            doc_type: 参照するドキュメントの種類
            
        Returns:
            dict: コード生成結果
        """
        try:
            # パラメータ検証
            if not prompt:
                return {
                    "success": False,
                    "error": "prompt is required"
                }
            
            if not doc_type:
                return {
                    "success": False,
                    "error": "doc_type is required"
                }
            
            logger.info(f"Generating code for doc_type: {doc_type}")
            
            # Gemini RAGマネージャーを呼び出してコード生成
            generated_code = await self.rag_manager.generate_code(
                prompt=prompt,
                doc_type=doc_type
            )
            
            return {
                "success": True,
                "message": "Code generated successfully",
                "doc_type": doc_type,
                "code": generated_code
            }
            
        except RAGError as e:
            logger.error(f"RAG error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.exception("Unexpected error during code generation")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def handle_list_uploaded_rags(self, doc_type: Optional[str] = None) -> dict:
        """
        アップロード済みのRAG一覧を取得.
        
        Args:
            doc_type: ドキュメントの種類（省略時は全RAG）
            
        Returns:
            dict: RAG一覧と統計情報
        """
        try:
            # RAG情報を取得
            if doc_type:
                # 特定のdoc_typeのRAGのみを取得
                rags_list = self.rag_manager.get_rags_by_type(doc_type)
                rags_dict = {doc_type: rags_list} if rags_list else {}
            else:
                # 全RAGを取得
                rags_dict = self.rag_manager.get_all_rags()
            
            # 統計情報を計算
            total_count = 0
            doc_type_counts = {}
            
            for dt, rags_list in rags_dict.items():
                count = len(rags_list)
                doc_type_counts[dt] = count
                total_count += count
            
            # レスポンスを構築
            response = {
                "success": True,
                "rags": rags_dict,
                "total_count": total_count,
                "doc_type_counts": doc_type_counts
            }
            
            # フィルタリングされている場合はfiltered_byフィールドを追加
            if doc_type:
                response["filtered_by"] = doc_type
            
            # RAGが存在しない場合はメッセージを追加
            if total_count == 0:
                response["message"] = "No RAGs found"
            
            return response
            
        except RAGError as e:
            logger.error(f"RAG error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.exception("Unexpected error while listing uploaded RAGs")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def handle_upload_file_directly(
        self,
        file_path: str,
        doc_type: Optional[str] = None,
        description: Optional[str] = None
    ) -> dict:
        """
        ローカルファイルを直接RAGにアップロード.
        
        Args:
            file_path: アップロードするファイルのパス
            doc_type: ドキュメントの種類（省略時はファイル名から推測）
            description: RAGの説明
            
        Returns:
            dict: アップロード結果
        """
        try:
            # パラメータ検証
            if not file_path:
                return {
                    "success": False,
                    "error": "file_path is required"
                }
            
            logger.info(f"Uploading file directly: {file_path}")
            
            # RAGマネージャーを呼び出してアップロード
            rag_id = await self.rag_manager.upload_file_directly(
                file_path=file_path,
                doc_type=doc_type,
                description=description
            )
            
            return {
                "success": True,
                "message": "File uploaded successfully",
                "file_path": file_path,
                "doc_type": doc_type,
                "rag_id": rag_id
            }
            
        except RAGError as e:
            logger.error(f"RAG error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.exception("Unexpected error during file upload")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def run(self):
        """MCPサーバーを起動."""
        logger.info("Starting Gemini RAG MCP server...")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def parse_args():
    """
    コマンドライン引数を解析.
    
    Returns:
        argparse.Namespace: 解析された引数
    """
    parser = argparse.ArgumentParser(
        description="Gemini RAG MCP Server - APIドキュメントを学習してコード生成を支援するMCPサーバー",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 標準的な起動
  python mcp_server.py
  
  # デバッグモードで起動
  python mcp_server.py --log-level DEBUG
  
  # バージョン情報を表示
  python mcp_server.py --version

環境変数:
  GEMINI_FILE_SEARCH_API_KEY  Gemini File Search APIキー（必須）
  GEMINI_CODE_GEN_API_KEY     Gemini Code Generation APIキー（必須）
  RAG_CONFIG_PATH             RAG設定ファイルのパス
  DOCS_STORE_PATH             ドキュメントストアのパス
  URL_CONFIG_PATH             URL設定ファイルのパス
  RAG_MAX_AGE_DAYS            RAGの最大保持日数（デフォルト: 90）
        """
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="ログレベルを設定（デフォルト: INFO）"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Gemini RAG MCP Server 1.0.0"
    )
    
    return parser.parse_args()


async def main():
    """メインエントリーポイント."""
    # コマンドライン引数を解析
    args = parse_args()
    
    # ロギングを設定
    setup_logging(args.log_level)
    
    try:
        logger.info("Gemini RAG MCP Server starting...")
        logger.debug(f"Log level: {args.log_level}")
        
        # MCPサーバーを初期化して起動
        server = GeminiRAGMCPServer()
        await server.run()
        
    except MCPError as e:
        logger.error(f"MCP server error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return 0
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
