#!/usr/bin/env python3
"""
Dify 知识库检索脚本
"""

import argparse
import json
import os
import re
import requests
from datetime import datetime


# 默认配置路径
DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "workspace", "TOOLS.md"
)


def load_default_config():
    """
    从 TOOLS.md 加载默认的 Dify 配置
    
    Returns:
        包含 api_url, api_key, dataset_id 的字典
    """
    config = {}
    
    # 尝试从工作区加载
    workspace_tools = os.path.expanduser("~/.openclaw/workspace/TOOLS.md")
    if os.path.exists(workspace_tools):
        config_path = workspace_tools
    elif os.path.exists(DEFAULT_CONFIG_PATH):
        config_path = DEFAULT_CONFIG_PATH
    else:
        return config
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 解析 Dify 配置
        patterns = {
            "api_url": r"\*\*API 地址\*\*:\s*(.+)",
            "api_key": r"\*\*API Key\*\*:\s*(.+)",
            "dataset_id": r"\*\*Dataset ID\*\*:\s*(.+)",
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                config[key] = match.group(1).strip()
                
    except Exception:
        pass
    
    return config


def list_datasets(api_url: str, api_key: str):
    """
    列出所有知识库
    
    Args:
        api_url: Dify API 地址
        api_key: Dify API Key
    
    Returns:
        知识库列表
    """
    url = f"{api_url}/datasets"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    return data.get("data", [])


def format_datasets(datasets: list) -> str:
    """格式化知识库列表"""
    if not datasets:
        return "未找到任何知识库"
    
    output = ["=== 知识库列表 ===\n"]
    
    for i, ds in enumerate(datasets, 1):
        ds_id = ds.get("id", "N/A")
        name = ds.get("name", "N/A")
        desc = ds.get("description", "")
        doc_count = ds.get("document_count", 0)
        word_count = ds.get("word_count", 0)
        created_at = ds.get("created_at", 0)
        created_time = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M") if created_at else "N/A"
        
        output.append(f"--- 知识库 {i} ---")
        output.append(f"ID: {ds_id}")
        output.append(f"名称: {name}")
        if desc:
            output.append(f"描述: {desc}")
        output.append(f"文档数: {doc_count} | 字数: {word_count}")
        output.append(f"创建时间: {created_time}")
        output.append("")
    
    return "\n".join(output)


def retrieve_knowledge(
    api_url: str,
    api_key: str,
    dataset_id: str,
    query: str,
    top_k: int = 3,
    search_method: str = "hybrid_search",
    score_threshold: float = None,
):
    """
    从 Dify 知识库检索内容
    
    Args:
        api_url: Dify API 地址
        api_key: Dify API Key
        dataset_id: 知识库 ID
        query: 查询文本
        top_k: 返回结果数量
        search_method: 搜索方法
        score_threshold: 分数阈值
    
    Returns:
        检索结果列表
    """
    url = f"{api_url}/datasets/{dataset_id}/retrieve"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # 部分 Dify 私有部署版本不支持 retrieval_model 嵌套，使用简化格式
    payload = {
        "query": query,
        "top_k": top_k,
        "search_method": search_method,
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    return data.get("records", [])


def format_results(records: list) -> str:
    """格式化检索结果"""
    if not records:
        return "未找到相关内容"
    
    output = []
    for i, record in enumerate(records, 1):
        segment = record.get("segment", {})
        content = segment.get("content", "")
        score = record.get("score", 0)
        doc = segment.get("document", {})
        
        output.append(f"--- 结果 {i} (相似度: {score:.4f}) ---")
        output.append(f"文档: {doc.get('name', 'N/A')}")
        output.append(f"内容: {content[:500]}")
        if len(content) > 500:
            output.append("...")
        output.append("")
    
    return "\n".join(output)


def main():
    # 先加载默认配置
    default_config = load_default_config()
    
    # 使用子命令解析
    parser = argparse.ArgumentParser(
        description="Dify 知识库工具",
        epilog=f"默认配置来源: TOOLS.md\n" +
               f"  API 地址: {default_config.get('api_url', '未配置')}\n" +
               f"  Dataset ID: {default_config.get('dataset_id', '未配置')}"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用子命令")
    
    # 子命令: list - 列出知识库
    subparsers.add_parser(
        "list",
        help="列出所有知识库",
        description="列出 Dify 账户下的所有知识库"
    )
    
    # 子命令: retrieve - 检索知识库
    retrieve_parser = subparsers.add_parser(
        "retrieve",
        help="检索知识库内容",
        description="从指定知识库检索内容"
    )
    
    # retrieve 子命令参数
    retrieve_parser.add_argument("--api-url", default=None, help=f"Dify API 地址 (默认: {default_config.get('api_url', '无')})")
    retrieve_parser.add_argument("--api-key", default=None, help=f"Dify API Key (默认: 读取 TOOLS.md)")
    retrieve_parser.add_argument("--dataset-id", default=None, help=f"知识库 ID (默认: 读取 TOOLS.md)")
    retrieve_parser.add_argument("--query", required=True, help="搜索查询")
    retrieve_parser.add_argument("--top-k", type=int, default=3, help="返回结果数量")
    retrieve_parser.add_argument("--search-method", 
                        default="hybrid_search",
                        choices=["hybrid_search", "semantic_search", "full_text_search", "keyword_search"],
                        help="搜索方法")
    retrieve_parser.add_argument("--score-threshold", type=float, help="分数阈值")
    retrieve_parser.add_argument("--json", action="store_true", help="输出原始 JSON")
    
    # 兼容旧版：没有子命令时当作 retrieve 处理
    import sys
    if len(sys.argv) > 1 and sys.argv[1] not in ["list", "retrieve", "-h", "--help"]:
        # 旧版兼容模式：添加默认参数
        sys.argv.insert(1, "retrieve")
    
    args = parser.parse_args()
    
    # 如果没有子命令，显示帮助
    if not hasattr(args, 'command') or args.command is None:
        parser.print_help()
        return
    
    subcommand = args.command
    
    # 使用用户提供的值，或回退到默认配置
    api_url = default_config.get("api_url", "https://api.dify.ai/v1")
    api_key = default_config.get("api_key")
    dataset_id = default_config.get("dataset_id")
    
    # 处理子命令
    if subcommand == "list":
        # list 命令不需要 dataset_id
        if not api_key:
            print("错误: 缺少 API Key，请在 TOOLS.md 中配置或通过 --api-key 指定")
            exit(1)
        
        try:
            datasets = list_datasets(api_url, api_key)
            print(format_datasets(datasets))
        except requests.exceptions.HTTPError as e:
            print(f"请求失败: {e}")
            if e.response is not None:
                print(f"响应内容: {e.response.text}")
            exit(1)
        except Exception as e:
            print(f"错误: {e}")
            exit(1)
    
    elif subcommand == "retrieve":
        # retrieve 命令
        # 允许通过命令行参数覆盖
        if args.api_url:
            api_url = args.api_url
        if args.api_key:
            api_key = args.api_key
        if args.dataset_id:
            dataset_id = args.dataset_id
        
        # 检查必需参数
        if not api_key:
            print("错误: 缺少 API Key，请在 TOOLS.md 中配置或通过 --api-key 指定")
            exit(1)
        if not dataset_id:
            print("错误: 缺少 Dataset ID，请在 TOOLS.md 中配置或通过 --dataset-id 指定")
            exit(1)
        
        try:
            records = retrieve_knowledge(
                api_url=api_url,
                api_key=api_key,
                dataset_id=dataset_id,
                query=args.query,
                top_k=args.top_k,
                search_method=args.search_method,
                score_threshold=args.score_threshold,
            )
            
            if args.json:
                print(json.dumps(records, ensure_ascii=False, indent=2))
            else:
                print(format_results(records))
                
        except requests.exceptions.HTTPError as e:
            print(f"请求失败: {e}")
            if e.response is not None:
                print(f"响应内容: {e.response.text}")
            exit(1)
        except Exception as e:
            print(f"错误: {e}")
            exit(1)


if __name__ == "__main__":
    main()