# API 接口文档

本程序（LarkBot）默认监听 `127.0.0.1:8000`（端口可在 `.env` 配置修改），仅本机访问，无认证。

响应格式：

- 成功：HTTP 200，`{"code": 0, "message": "ok", "data": {...}}`。
- 失败：HTTP 4xx/5xx，`{"code": <业务码>, "message": "具体原因", "data": null}`。


## 全局业务状态码表

分段规则：`0` 通用 · `1xxx` 成功但需提示 · `4xxx` 客户端错误 · `5xxx` 服务端/上游错误

| 业务码 | 分段 | 含义 |
|---|---|---|
| 0 | 通用 | 只需要返回 HTTP 码但不需要业务状态码时，或者无对应业务状态码能描述时 |
| 1001 | 成功提示 | 同程序名、同接口名再次注册，覆盖该接口的 path |
| 4001 | 客户端 | 程序未注册（含已被心跳清除） |
| 4003 | 客户端 | 文件名缺少扩展名 |
| 4004 | 客户端 | base64 非法或解码后为空 |
| 4005 | 客户端 | 文件超过 30MB |
| 4006 | 客户端 | mp4 缺少 duration_ms |
| 4007 | 客户端 | 请求参数不合法（字段缺失、类型错误） |
| 5000 | 服务端 | 本程序内部错误 |
| 5001 | 服务端 | 保留，当前版本不返回 |

## 1. POST /register —— 注册下游程序

下游程序注册时调用。每次调用注册一个接口；一个程序有多个接口时，按接口数量多次调用。

请求参数：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| program | string | 是 | 程序名，全局唯一 |
| base_url | string | 是 | 下游程序地址，如 `http://127.0.0.1:9001` |
| cmd | string | 是 | 接口名，同一程序名内唯一 |
| path | string | 是 | 接口路径，必须以 `/` 开头，如 `/query` |

示例：

```json
POST /register
{"program": "基金", "base_url": "http://127.0.0.1:9001", "cmd": "查询", "path": "/query"}

→ 200 {"code": 0, "message": "ok", "data": {"program_id": 100000}}
→ 200 {"code": 1001, "message": "注册成功（覆盖）", "data": {"program_id": 100000}}
```

## 2. POST /heartbeat —— 心跳

下游程序周期调用，用于维持程序及其全部接口存活。

请求参数：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| program | string | 是 | 已注册的程序名 |

示例：

```json
POST /heartbeat
{"program": "基金"}

→ 200 {"code": 0, "message": "ok", "data": null}
→ 404 {"code": 0, "message": "程序未注册: 基金", "data": null}
```

## 3. POST /send/text —— 发送文本

下游用于向指定用户发送文本。

请求参数：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| program | string | 是 | 已注册的程序名 |
| target | string | 是 | 接收用户的 open_id |
| content | string | 是 | 文本内容 |

示例：

```json
POST /send/text
{"program": "基金", "target": "ou_55e1a0c9...", "content": "今日收益 +2.3%"}

→ 200 {"code": 0, "message": "ok", "data": {"queued": true}}
```

## 4. POST /send/file —— 发送文件

下游程序用于向指定用户发送文件。

请求参数：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| program | string | 是 | 已注册的程序名 |
| target | string | 是 | 接收用户的 open_id |
| file_name | string | 是 | 文件名，须带扩展名 |
| content_base64 | string | 是 | 文件内容的标准 base64 编码 |
| duration_ms | int | 仅 mp4 必填 | 视频时长（毫秒） |

示例：

```json
POST /send/file
{"program": "基金", "target": "ou_55e1a0c9...", "file_name": "报告.xlsx",
 "content_base64": "SGVsbG8="}

→ 200 {"code": 0, "message": "ok", "data": {"queued": true}}
```

规则：
- 文件解码后不超过 30MB。
- 扩展名自动映射飞书文件类型：doc/docx→doc，xls/xlsx→xls，ppt/pptx→ppt，pdf→pdf，mp4→mp4，其余→stream。
- 视频自动附带默认封面图。

## 5. GET /health —— 探活

检查本程序 HTTP 服务是否在运行。

示例：

```json
GET /health

→ 200 {"code": 0, "message": "ok", "data": null}
```
