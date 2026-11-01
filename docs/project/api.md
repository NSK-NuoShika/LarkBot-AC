# API 接口文档

本程序（LarkBow）默认监听 `127.0.0.1:8000`（端口可在 `.env` 配置修改），仅本机访问，无认证。

响应格式（HTTP 状态码 + 业务状态码）：

- 成功：`{"code": 0, "message": "ok", "data": {...}}`
- 失败：`{"code": 4002, "message": "具体原因", "data": null}`，HTTP 同步返回 4xx/5xx

## 全局业务状态码表

分段规则：`0` 通用 · `1xxx` 成功但需提示 · `4xxx` 客户端错误 · `5xxx` 服务端/上游错误

| 业务码 | 分段 | 含义 |
|---|---|---|
| 0 | 通用 | 只需要返回HTTP码但不需要业务状态码时或者无对应业务状态码能描述时 |
| 1001 | 成功提示 | 注册覆盖：同名旧程序已被替换 |
| 4001 | 客户端 | 程序未注册（含已被心跳清除） |
| 4003 | 客户端 | 文件名不合法（含缺扩展名） |
| 4004 | 客户端 | 不合法 base64 |
| 4005 | 客户端 | 文件超过 30MB |
| 4006 | 客户端 | 时长缺失 |
| 4007 | 客户端 | 注册参数不合法 |
| 5000 | 服务端 | 本程序错误 |
| 5001 | 服务端 | 上游飞书调用失败 |

## 1. POST /register —— 注册下游程序

下游程序注册时调用，每个程序可以注册多个接口。

请求参数：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| program | string | 是 | 程序名，全局唯一 |
| base_url | string | 是 | 下游程序地址，如 `http://127.0.0.1:9001` |
| cmd | string | 是 | 接口名 |
| path | string | 是 | 接口路径，如 `/query` |

示例：

```json
POST /register
{"program": "基金", "base_url": "http://127.0.0.1:9001", "cmd": "查询", "path": "/query"}

→ 200 {"code": 0,    "message": "ok", "data": {"program_id": 100000}}
→ 200 {"code": 1001, "message": "注册成功（覆盖同名程序）", "data": {"program_id": 100000}}
```

## 2. POST /heartbeat —— 心跳

下游调用表示存活；超时未调用，程序及其接口将被自动清除。

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

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| program | string | 是 | 已注册的程序名 |
| target | string | 是 | 接收用户的 open_id |
| content | string | 是 | 文本内容 |

示例：

```json
POST /send/text
{"program": "基金", "target": "ou_55e1a0c9...", "content": "今日收益 +2.3%"}

→ 200 {"code": 0, "message": "ok", "data": {"message_id": "om_xxx"}}
```

## 4. POST /send/file —— 发送文件

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| program | string | 是 | 已注册的程序名 |
| target | string | 是 | 接收用户的 open_id，`ou_` 开头 |
| file_name | string | 是 | 文件名，必须带扩展名，如 `报告.xlsx` |
| content_base64 | string | 是 | 文件内容的 base64 编码 |
| duration_ms | int | mp4 必填 | 视频/音频时长（毫秒）|

限制与规则：

- 文件解码后不超过 30MB
- 扩展名自动映射飞书文件类型：doc/docx→doc，xls/xlsx→xls，ppt/pptx→ppt，pdf→pdf，mp4→mp4，其余→stream
- 视频自动附带默认封面图
