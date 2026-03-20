#!/usr/bin/env python3
"""
在鸿云文档检索脚本 - 从HTML中提取渲染后的内容
"""

import argparse
import subprocess
import re
import sys

# 文档站点基础URL
BASE_URL = "https://docs-dev.openvalley.net"

def fetch_page_content(url):
    """获取页面内容"""
    try:
        result = subprocess.run(
            ["curl", "-s", url],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            return result.stdout
    except Exception as e:
        pass
    return None

def extract_content_from_html(html_content):
    """从HTML中提取主要内容"""
    if not html_content:
        return "", ""

    # 提取标题
    title_match = re.search(r'<title>([^<]+)</title>', html_content)
    title = title_match.group(1).replace(' | 在鸿云文档', '').strip() if title_match else "未知标题"

    # 提取主要文档内容 (vp-doc 类中的内容)
    content_match = re.search(r'<div[^>]*class="vp-doc[^"]*"[^>]*>(.*?)</div>\s*</main>', html_content, re.DOTALL)
    if not content_match:
        # 尝试另一种方式
        content_match = re.search(r'<main[^>]*class="main[^"]*"[^>]*>.*?<div[^>]*>(.*?)</div>\s*</main>', html_content, re.DOTALL)

    if content_match:
        content = content_match.group(1)
        # 清理HTML标签但保留文本
        # 移除script标签
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        # 移除HTML标签，保留文本
        content = re.sub(r'<[^>]+>', '\n', content)
        # 解码HTML实体
        content = content.replace('&nbsp;', ' ')
        content = content.replace('&lt;', '<')
        content = content.replace('&gt;', '>')
        content = content.replace('&amp;', '&')
        # 清理多余空白
        content = re.sub(r'\n+', '\n', content)
        content = re.sub(r' +', ' ', content)
        return title, content.strip()

    return title, ""

def search_by_module(query, module, top_k=3):
    """根据模块检索文档"""
    if module not in MODULE_PATHS:
        print(f"错误: 未知模块 {module}")
        return []

    # 获取模块下的页面
    pages_to_check = get_pages_for_module(module)

    results = []
    query_keywords = query.lower().split()

    for page in pages_to_check:
        url = f"{BASE_URL}{page}"
        html = fetch_page_content(url)

        if html:
            title, content = extract_content_from_html(html)

            if content:
                # 关键词匹配
                content_lower = content.lower()
                score = sum(1 for keyword in query_keywords if keyword in content_lower)

                if score > 0:
                    results.append({
                        "url": url,
                        "title": title,
                        "content": content[:3000],  # 限制内容长度
                        "score": score
                    })

    # 按分数排序
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

def get_pages_for_module(module):
    """获取模块下的所有可能页面"""
    pages = []

    if module == "device":
        pages = [
            "/device/platform/platform-introduce.html",
            "/device/platform/product-funciton.html",
            "/device/tlink/connect-auth.html",
            "/device/tlink/property.html",
            "/device/tlink/command.html",
            "/device/tlink/ota.html",
            "/device/tlink/gateway-sub.html",
            "/device/api/device/registerDevice.html",
            "/device/api/device/queryDeviceList.html",
            "/device/quickAccess/safe-auth.html",
            "/device/tlink/dynamic-reg.html",
            "/device/tlink/auto-reg.html",
            "/device/tlink/https-access.html",
            "/device/tlink/tcp-auth.html",
            "/device/tlink/websocket-auth.html",
        ]
    elif module == "safety":
        pages = [
            "/safety/platform/platform-introduce.html",
            "/safety/platform/product-funciton.html",
            "/safety/api/iot/id2/getId2.html",
            "/safety/api/iot/cert/getToken.html",
            "/safety/api/iot/cert/iotRegister.html",
            "/safety/api/signCenter/sign.html",
            "/safety/api/signCenter/verifySignature.html",
            "/safety/quickAccess/iot/id2.html",
            "/safety/quickAccess/iot/cert.html",
        ]
    elif module == "appstore":
        pages = [
            "/appstore/platform-introduce.html",
            "/appstore/app-publish.html",
            "/appstore/api/QueryAppDetail.html",
            "/appstore/api/QueryAppPageList.html",
            "/appstore/api/CheckAppUpdate.html",
        ]
    elif module == "auth":
        pages = [
            "/auth/platform-introduce.html",
            "/auth/token/getToken.html",
        ]
    elif module == "common":
        pages = [
            "/common/platform-introduce.html",
            "/common/weather/free/getWeather.html",
            "/common/weather/free/getFourteen.html",
            "/common/weather/free/get48HourTemperature.html",
            "/common/weather/free/getFull.html",
        ]
    elif module == "zaiohos":
        pages = [
            "/zaiohos/platform-introduce.html",
            "/zaiohos/api/ai/voiceassistant.html",
            "/zaiohos/api/device-manager/led.html",
            "/zaiohos/api/device-manager/buzzer.html",
            "/zaiohos/api/device-manager/humiture.html",
            "/zaiohos/api/device-manager/ultrasonic.html",
            "/zaiohos/api/device-manager/steeringGear.html",
        ]
    elif module == "ai":
        pages = [
            "/ai/platform-introduce.html",
            "/ai/platform/platform-introduce.html",
            "/ai/platform/product-framework.html",
            "/ai/platform/product-funciton.html",
            "/ai/api/agent/modelManager/introduction/pro-introduce.html",
            "/ai/api/agent/pluginManager/introduction/pro-introduce.html",
            "/ai/api/agent/synergyManager/introduction/pro-introduce.html",
            "/ai/api/agent/chat/chat-single.html",
            "/ai/api/agent/chat/chat-stream.html",
            "/ai/api/speech/tts.html",
            "/ai/api/speech/streamasr.html",
        ]

    return pages

# 模块映射
MODULE_PATHS = {
    "device": "/device/",
    "safety": "/safety/",
    "appstore": "/appstore/",
    "auth": "/auth/",
    "common": "/common/",
    "zaiohos": "/zaiohos/",
    "ai": "/ai/",
}

def detect_module(query):
    """根据关键词自动检测模块"""
    query_lower = query.lower()

    if any(k in query_lower for k in ["设备", "设备管理", "物模型", "ota", "ota升级", "产品", "设备注册", "设备列表", "device", "tlink"]):
        return "device"
    elif any(k in query_lower for k in ["安全", "认证", "证书", "id2", "加密", "签名", "token", "鉴权", "safety", "cert", "iot"]):
        return "safety"
    elif any(k in query_lower for k in ["应用", "应用市场", "原子化", "卡片", "app", "appstore"]):
        return "appstore"
    elif any(k in query_lower for k in ["认证", "token", "鉴权", "登录", "auth"]):
        return "auth"
    elif any(k in query_lower for k in ["天气", "定位", "通用服务", "weather", "common"]):
        return "common"
    elif any(k in query_lower for k in ["在鸿os", "openharmony", "arkts", "鸿蒙", "os", "zaiohos"]):
        return "zaiohos"
    elif any(k in query_lower for k in ["ai", "大模型", "模型", "agent", "语音", "tts", "asr", "智能", "chat", "model"]):
        return "ai"
    else:
        return None

def main():
    parser = argparse.ArgumentParser(description="在鸿云文档检索")
    parser.add_argument("--query", "-q", required=True, help="搜索关键词")
    parser.add_argument("--module", "-m", help="指定模块 (device/safety/appstore/auth/common/zaiohos/ai)")
    parser.add_argument("--top-k", "-k", type=int, default=3, help="返回结果数量")

    args = parser.parse_args()

    # 确定模块
    module = args.module
    if not module:
        module = detect_module(args.query)

    if not module:
        print("无法确定模块，请手动指定 --module 参数")
        print("可选模块: device, safety, appstore, auth, common, zaiohos, ai")
        sys.exit(1)

    print(f"检测到模块: {module}", file=sys.stderr)

    # 检索文档
    results = search_by_module(args.query, module, args.top_k)

    if not results:
        print("未找到相关内容")
        sys.exit(0)

    # 输出结果
    for i, result in enumerate(results, 1):
        print(f"\n{'='*60}")
        print(f"结果 {i} (相似度: {result['score']})")
        print(f"标题: {result['title']}")
        print(f"链接: {result['url']}")
        print(f"{'='*60}")
        print(f"\n内容:\n{result['content']}")

if __name__ == "__main__":
    main()