# 架构文档

## 文件结构

```
LarkBot/
├── src/
│   ├── main.py
│   ├── queues/
│   │   ├── __init__.py
│   │   └── queues.py
│   ├── feishu/
│   │   ├── __init__.py
│   │   ├── receiver.py
│   │   └── sender.py
│   ├── downstream/
│   │   ├── __init__.py
│   │   ├── api.py
│   │   ├── sender.py
│   │   ├── dispatcher.py
│   │   ├── register.py
│   │   ├── heartbeat.py
│   │   └── sweeper.py
│   ├── logger/
│   │   ├── __init__.py
│   │   ├── dispatch_log.py
│   │   ├── send_log.py
│   │   ├── feishu_log.py
│   │   └── registry_log.py
│   ├── storage/
│   │   ├── __init__.py
│   │   └── sqlite.py
│   └── config/
│       ├── __init__.py
│       └── settings.py
├── test/
├── CLAUDE.md
├── docs/
│   ├── plan/
│   └── project/
│       ├── api.md
│       ├── architecture.md
│       ├── database.md
│       └── log.md
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
└── log/
```

## 模块说明

### main.py —— 启动器

程序唯一入口：初始化数据库、启动后台线程（收飞书、派发、发飞书、清扫），启动 HTTP 服务。

### queues —— 队列模块

Q1 派发队列与 Q2 发送队列定义。各模块通过这两个队列传递数据。

- queues.py：定义 Q1（派发队列）与 Q2（发送队列）。

### feishu —— 飞书模块

负责与飞书交互：收用户消息、向用户发消息。

- receiver.py：维持与飞书的 WebSocket 长连接（线程①），接收事件，把单聊文本消息原样放入 Q1。
- sender.py：发送线程（线程③），循环从 Q2 取任务发送到飞书；文件先上传拿 file_key，处理扩展名映射、校验 30MB 限制、处理 mp4 时长与默认封面，记录 feishu.log。

### downstream —— 下游模块

负责与下游程序交互：接受下游 HTTP 请求、向下游派发命令、管理注册与心跳。

- api.py：六个 HTTP 路由，仅实现接口，不处理业务。
- sender.py：发送业务，处理下游的 /send/text 与 /send/file 请求，校验通过后放入 Q2 立即返回，记录 send.log。
- dispatcher.py：派发线程（线程②），从 Q1 取用户命令，解析出程序名、接口名、参数，查路由后限时 3 秒 POST 给下游，记录 dispatch.log。
- register.py：注册业务，处理 /register：写入数据库，记录 registry.log。
- heartbeat.py：心跳业务，处理 /heartbeat：刷新程序存活时间。
- sweeper.py：清扫线程（线程④），默认每 30 秒扫描心跳超过 120 秒的程序并从数据库删除（可通过配置修改），记录 registry.log。

### logger —— 日志模块

负责日志写入。

- __init__.py：日志基础设施——TSV 拼行、ISO8601 时间戳。
- dispatch_log.py：负责 dispatch.log（派发流水）的写入。
- send_log.py：负责 send.log（发送流水）的写入。
- feishu_log.py：负责 feishu.log（飞书流水）的写入。
- registry_log.py：负责 registry.log（注册流水）的写入。

### storage —— 数据库模块

负责 SQLite 的全部操作，是全程序唯一写 SQL 的地方。

- sqlite.py：建表、注册写入、心跳刷新、路由查询、超时查询与级联删除，WAL 模式。

### config —— 配置模块

负责配置的加载与校验。

- settings.py：读取 .env。

## 其他文件

- api.md / database.md / log.md：接口、数据库、日志三份设计文档。
- requirements.txt：依赖清单；.env.example：配置模板；.gitignore：版本忽略。
- data/ 与 log/：运行时自动生成的数据库文件与流水日志。
