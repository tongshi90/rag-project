---
name: openvalley-docs
description: 在鸿云平台 API 文档检索工具。根据用户问题从 docs-dev.openvalley.net 文档站点检索相关内容。使用场景：(1) 查询在鸿云平台的API接口 (2) 查询平台功能说明 (3) 查询开发文档。

---

# 在鸿云文档检索工具

## 文档站点

- **地址**: https://docs-dev.openvalley.net/
- **内容**: 在鸿云平台 API 文档，包括设备、安全、原子化、认证、通用服务、在鸿OS、在鸿云AI平台等模块

## 检索流程

**重要：每次检索前必须执行以下步骤：**

1. **分析用户问题** - 提取关键词，确定属于哪个模块
2. **访问对应页面** - 根据模块确定 URL 路径
3. **获取文档内容** - 使用脚本获取页面 markdown 内容
4. **返回结果** - 整理并返回相关内容

## 模块匹配规则

根据问题关键词匹配对应的文档模块：

| 关键词                                | 模块           | URL 路径   |
| ------------------------------------- | -------------- | ---------- |
| 设备、设备管理、设备接入、物模型、OTA | 设备管理平台   | /device/   |
| 安全、认证、证书、ID2、加密、签名     | 安全平台       | /safety/   |
| 应用、应用市场、原子化、卡片          | 原子化管理平台 | /appstore/ |
| 认证、token、鉴权                     | 认证平台       | /auth/     |
| 天气、定位                            | 通用服务       | /common/   |
| 在鸿OS、OpenHarmony、ArkTS            | 在鸿OS         | /zaiohos/  |
| AI、大模型、模型管理、Agent、语音     | 在鸿云AI平台   | /ai/       |

## 检索示例

```bash
# 检索设备相关的API文档
python scripts/retrieve.py --query "设备注册" --module device

# 检索天气API
python scripts/retrieve.py --query "获取天气" --module common

# 检索AI平台文档
python scripts/retrieve.py --query "模型管理" --module ai
```

## 输出格式

返回的内容包括：

- 文档标题
- 完整的 API 说明、参数、返回值等
- 相关代码示例（如果有）

## 重要提示

- 必须先匹配模块，再进行检索
- 返回原文内容，不要精简
- 可以在原文后增加总结
- **必须带上文档链接**，格式：`文档：xxx | 链接：https://docs-dev.openvalley.net/xxx`