# 数据库约束文档

数据库采用 SQLite，单文件存放于项目根目录的 `data/larkbow.db`。

## 表 1：program —— 下游程序表

本表登记所有已注册的下游程序。

### 表结构

| 字段 | 类型 | 约束 | 存储内容 |
|---|---|---|---|
| `id` | INTEGER | 主键 | 下游程序的唯一编号，注册时显式分配，范围 100000-999999；删除后可能复用，不保证严格递增 |
| `name` | TEXT | 非空，全表唯一 | 下游程序名 |
| `base_url` | TEXT | 非空 | 下游程序地址，如 `http://127.0.0.1:9001` |
| `updated_at` | INTEGER | 非空 | 最近一次注册时间（Unix 秒）。 |
| `heart_time` | INTEGER | 非空 | 最近一次心跳或注册时间（Unix 秒）。 |

### 建表语句

```sql
CREATE TABLE IF NOT EXISTS program (
    id         INTEGER PRIMARY KEY,
    name       TEXT UNIQUE NOT NULL,
    base_url   TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
    heart_time INTEGER NOT NULL
);
```

## 表 2：command —— 接口表

本表登记每个下游程序对外提供的接口。

### 表结构

| 字段 | 类型 | 约束 | 存储内容 |
|---|---|---|---|
| `id` | INTEGER | 主键 | 接口的唯一编号，注册时显式分配，范围 100000-999999；删除后可能复用，不保证严格递增 |
| `program_id` | INTEGER | 非空，外键 → `program.id`，`ON DELETE CASCADE` | 所属程序的编号 |
| `cmd` | TEXT | 非空；与 `program_id` 组合唯一（联合唯一约束） | 接口名，同一程序内不许重名，跨程序可重名 |
| `path` | TEXT | 非空，须以 `/` 开头 | 接口路径，如 `/query`。派发时与所属程序的 `base_url` 拼成完整下游 URL |

### 建表语句

```sql
CREATE TABLE IF NOT EXISTS command (
    id         INTEGER PRIMARY KEY,
    program_id INTEGER NOT NULL REFERENCES program(id) ON DELETE CASCADE,
    cmd        TEXT NOT NULL,
    path       TEXT NOT NULL,
    UNIQUE(program_id, cmd)
);
```
