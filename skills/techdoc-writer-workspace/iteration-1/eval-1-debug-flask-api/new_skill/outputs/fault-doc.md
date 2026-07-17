# flask-api `/users` 接口 `database is locked` 故障分析与修复技术文档

## 前言

### 概述

本文档记录 flask-api 服务的 `/users` 接口在并发 POST 写入场景下抛出 `sqlite3.OperationalError: database is locked` 的完整排障过程，涵盖故障现象、逐条日志解析、根本原因分析、解决方案（含真实 git diff）与验证方法。读者据此可复现该故障、理解 SQLite 在多线程并发写下的锁机制，并将同类修复应用到自己的服务中。

### 平台支持

下表列出本案例涉及的关键组件及版本。

| 组件 | 版本 / 取值 | 说明 |
|---|---|---|
| Python | 3.11 | 见 error.log 中 traceback 路径 `python3.11` |
| Flask | 3.0.0 | 见 `requirements.txt` |
| sqlite3 | Python 3.11 内置标准库 | 数据库后端 |
| 运行方式 | `app.run(..., threaded=True)` | Flask 内置 WSGI，多线程并发处理请求 |
| 数据库文件 | `users.db`（rollback journal / WAL 文件随之产生） | 单文件 SQLite，进程内多连接共享 |
| 部署路径 | `/userdata/flask-api/`（见 traceback） | 服务运行目录 |

### 读者对象

- 维护 flask-api `/users` 接口的后端工程师
- 需要在嵌入式 / 单机环境下使用 SQLite 承载并发写的开发者
- 排查 `database is locked` 类锁竞争问题的工程师

### 修订记录

| 版本号 | 作者 | 修改日期 | 修改说明 |
|---|---|---|---|
| V1.0 | techdoc-writer | 2026-06-12 | 首次发布，基于提交 `36a1c4f` 的修复整理 |

---

## Chapter-1 系统概述

### 1.1 服务简介

flask-api 是一个最小用户服务，对外暴露 `/users` 接口，后端以本地单文件 SQLite（`users.db`）存储用户记录：

- `GET /users`：返回全部用户列表（读操作）。
- `POST /users`：插入一条新用户记录（写操作）。

服务以 Flask 内置 WSGI 服务器启动，并显式开启 `threaded=True`，即**每个 HTTP 请求由独立工作线程处理**。这意味着多个 POST 请求可在同一进程内并发进入 `create_user()`，各自持有一个独立的 SQLite 连接同时尝试写库——这正是本次故障的触发条件。

请求处理与数据库访问的关系如下：

```
HTTP POST /users  ──线程 A──▶ create_user() ──▶ conn_A.execute(INSERT) ──┐
HTTP POST /users  ──线程 B──▶ create_user() ──▶ conn_B.execute(INSERT) ──┤──▶ users.db（单写锁）
HTTP GET  /users  ──线程 C──▶ list_users()  ──▶ conn_C.execute(SELECT) ──┘
```

图 1-1 并发请求与 SQLite 单写锁关系示意

### 1.2 软硬件环境

见前言「平台支持」表。要点：Python 3.11 + Flask 3.0.0，多线程模式，SQLite 默认 rollback journal 模式、默认 busy timeout 为 0。

### 1.3 故障复盘流程总览

| 阶段 | 内容 | 对应章节 | 完成标志 |
|---|---|---|---|
| 1 | 采集并发写入下的报错日志 | 2.1 | error.log 中出现两条 `database is locked` |
| 2 | 逐条解析 traceback，定位失败调用 | 2.2 | 确认 INSERT 与 commit 两处均失败 |
| 3 | 机制层面分析锁竞争根因 | 2.3 | 明确默认 busy timeout=0 + 连接不释放 |
| 4 | 落地三项修复并提交 | 2.4 | 提交 `36a1c4f` |
| 5 | 并发回放验证不再报错 | 2.5 | 并发 POST 全部返回 201 |

---

## Chapter-2 故障诊断

### 2.1 故障速查总表

| 故障现象 | 根本原因 | 解决方案 | 详见 |
|---|---|---|---|
| 并发 POST `/users` 返回 500，日志 `sqlite3.OperationalError: database is locked` | 多线程并发写 + SQLite 默认 busy timeout=0，未拿到写锁即刻失败 | 设置连接 `timeout=5.0`（busy timeout），等待锁释放 | 2.4.1 |
| 同一请求 INSERT 成功而 `conn.commit()` 仍报 `database is locked` | rollback journal 模式下写者互斥；连接未及时释放放大锁持有时间 | 启用 WAL 模式，读写不互斥、并发写串行化 | 2.4.2 |
| 连接对象一直不关闭，锁长期占用 | `get_conn()` 返回的连接无 `with` 管理，异常路径不归还连接 | 用 `with get_conn() as conn:` 托管连接生命周期 | 2.4.3 |

### 2.2 故障现象

并发向 `/users` 发起 POST 写入时，服务日志中出现如下原文（摘自仓库根目录 `error.log`，未做任何清洗或改写）：

```text
[2026-06-10 14:22:31] POST /users  name=alice
[2026-06-10 14:22:31] POST /users  name=bob
[2026-06-10 14:22:36,118] ERROR in app: Exception on /users [POST]
Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/flask/app.py", line 1455, in wsgi_app
    response = self.full_dispatch_request()
  File "/usr/local/lib/python3.11/site-packages/flask/app.py", line 869, in full_dispatch_request
    rv = self.dispatch_request()
  File "/userdata/flask-api/app.py", line 28, in create_user
    cur = conn.execute("INSERT INTO users(name) VALUES (?)", (name,))
sqlite3.OperationalError: database is locked
[2026-06-10 14:22:36] 500 POST /users  name=bob
[2026-06-10 14:22:41,260] ERROR in app: Exception on /users [POST]
Traceback (most recent call last):
  File "/userdata/flask-api/app.py", line 29, in create_user
    conn.commit()
sqlite3.OperationalError: database is locked
[2026-06-10 14:22:41] 500 POST /users  name=carol
```

### 2.3 逐条解析

对日志中每条关键记录的解析如下，一条一段。

- **`[14:22:31] POST /users name=alice` 与 `name=bob` 几乎同刻到达**：两条 POST 在同一秒进入服务。由于服务以 `threaded=True` 运行，alice 与 bob 分别由两个独立工作线程处理，各自调用 `get_conn()` 建立**独立的 SQLite 连接**并发写库。这是后续锁竞争的前提。

- **`File ".../app.py", line 28, in create_user` → `cur = conn.execute("INSERT ...")` → `sqlite3.OperationalError: database is locked`**：第一处失败发生在 **INSERT 语句**。此时另一个线程的连接已持有数据库写锁（SQLite 同一时刻只允许一个写者），当前线程尝试获取写锁失败。关键在于：**SQLite 默认 busy timeout 为 0**，即拿不到锁不等待、立即抛 `database is locked`，而非阻塞重试。因此该 INSERT 在抢锁失败的瞬间即以 500 告终（对应 `[14:22:36] 500 POST /users name=bob`）。

- **`File ".../app.py", line 29, in create_user` → `conn.commit()` → `sqlite3.OperationalError: database is locked`**：第二处失败发生在 **commit 阶段**（处理 carol 的请求）。在默认 rollback journal 模式下，写事务提交需要独占数据库；若此刻仍有其他连接持锁未释放，提交同样会立即失败。这条记录表明锁竞争不止发生在 INSERT 取锁时，也发生在事务提交时——只要并发写者存在且无等待机制，写路径上的任一加锁点都可能命中。

- **失败请求的时间分布（14:22:31 进入、14:22:36 / 14:22:41 报错）**：报错并非瞬时返回，而是相隔数秒。这提示连接在异常路径下未被及时关闭、锁被长时间占用，进一步放大了后续请求的取锁失败概率（详见 2.3 根因第 3 点）。

### 2.3 根因分析

故障由三个相互叠加的机制共同导致，缺一不会在如此低的并发下集中爆发。

1. **SQLite 写者互斥 + 默认零等待（busy timeout = 0）**：SQLite 是单写者模型，任一时刻仅允许一个连接持有写锁。修复前 `get_conn()` 调用 `sqlite3.connect(DB_PATH)` 未传 `timeout` 参数，busy timeout 取默认值 0。其语义是：取不到锁**立即**抛 `OperationalError: database is locked`，而不是等待锁释放。因此只要两个 POST 线程同刻写库，落后者必然立刻失败——这是 line 28 INSERT 报错的直接机制。

2. **rollback journal 模式下读写 / 写写互斥**：修复前未设置 `journal_mode`，SQLite 使用默认的 rollback journal。该模式下写事务对数据库加排他锁，提交时需要独占，读者与写者、写者与写者之间互斥。这使得 `conn.commit()`（line 29）在他人持锁时同样会失败，扩大了报错触发面。

3. **连接生命周期未托管，锁持有时间被放大**：修复前 `list_users()` / `create_user()` 直接 `conn = get_conn()`，既无 `with` 也无显式 `close()`。一旦请求路径中抛出异常，连接不会被及时归还，其持有的锁要等到对象被垃圾回收才释放。锁持有窗口越长，并发写者撞上 `database is locked` 的概率越高——这解释了为何在仅 alice / bob / carol 三个请求的低并发下就稳定复现，以及报错与请求之间数秒的时间差。

综上：**单写锁是 SQLite 固有特性，本身不是 bug；真正的缺陷是「零等待 + 长锁持有」的组合**——并发写者拿不到锁时既不等待（busy timeout=0），他人又因连接不释放而长时间占锁，于是必然立即失败。

### 2.4 解决方案

修复在提交 `36a1c4f`（`Fix database is locked: WAL mode, busy timeout, with-managed connections`）中完成，针对 2.3 的三条根因分别施治，仅改动 `app.py`。以下 diff 均来自该真实提交，可用 `git show 36a1c4f` 复核。

#### 2.4.1 设置 busy timeout，并发写改为等待而非立即失败

为连接设置 `timeout=5.0`，将 SQLite busy timeout 由默认 0 提升到 5 秒：取不到写锁时在 5 秒内轮询等待锁释放，而不是瞬间抛 `database is locked`。这直接消除 2.3 根因 1。

```diff
--- a/app.py
+++ b/app.py
@@ -7,24 +7,28 @@ DB_PATH = "users.db"
 
 
 def get_conn():
-    # 每次新建连接，直接连库
-    return sqlite3.connect(DB_PATH)
+    # 写操作等待锁释放最多 5s，避免并发写直接抛 database is locked
+    conn = sqlite3.connect(DB_PATH, timeout=5.0)
```

#### 2.4.2 启用 WAL 模式，读写不互斥、并发写串行化

在连接上执行 `PRAGMA journal_mode=WAL`，将日志模式由默认 rollback journal 切换为 WAL（Write-Ahead Logging）。WAL 下读者不阻塞写者、写者不阻塞读者，多个写者被串行化而非直接失败，显著降低 commit 阶段的锁冲突，对应 2.3 根因 2。

```diff
def get_conn():
-    # 每次新建连接，直接连库
-    return sqlite3.connect(DB_PATH)
+    # 写操作等待锁释放最多 5s，避免并发写直接抛 database is locked
+    conn = sqlite3.connect(DB_PATH, timeout=5.0)
+    # WAL 模式：读写不互斥，并发写串行化而非直接失败
+    conn.execute("PRAGMA journal_mode=WAL")
+    return conn
```

> 注意：WAL 模式会在 `users.db` 旁生成 `users.db-wal` 与 `users.db-shm` 两个伴随文件，这是正常现象；不要在服务运行时手动删除。

#### 2.4.3 用 `with` 托管连接，确保锁及时释放

将 `list_users()` 与 `create_user()` 中裸用的连接改为 `with get_conn() as conn:` 上下文管理。`with` 块在正常或异常退出时都会提交 / 回滚并触发连接归还，缩短锁持有窗口，对应 2.3 根因 3。`create_user()` 中将 `cur.lastrowid` 提前取出为 `new_id`，确保在连接关闭前读取自增主键。

```diff
 @app.route("/users", methods=["GET"])
 def list_users():
-    conn = get_conn()
-    rows = conn.execute("SELECT id, name FROM users").fetchall()
+    with get_conn() as conn:
+        rows = conn.execute("SELECT id, name FROM users").fetchall()
     return jsonify([{"id": r[0], "name": r[1]} for r in rows])
 
 
 @app.route("/users", methods=["POST"])
 def create_user():
     name = request.json["name"]
-    conn = get_conn()
-    cur = conn.execute("INSERT INTO users(name) VALUES (?)", (name,))
-    conn.commit()
-    return jsonify({"id": cur.lastrowid, "name": name}), 201
+    with get_conn() as conn:
+        cur = conn.execute("INSERT INTO users(name) VALUES (?)", (name,))
+        conn.commit()
+        new_id = cur.lastrowid
+    return jsonify({"id": new_id, "name": name}), 201
```

#### 2.4.4 修复后完整 `app.py`

上方分块仅为讲解，可运行版以下方完整脚本为准（即提交 `36a1c4f` 之后的 `app.py`，已在 Python 3.11 + Flask 3.0.0 下运行）：

```python
"""极简用户服务：/users 读写 SQLite。"""
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = "users.db"


def get_conn():
    # 写操作等待锁释放最多 5s，避免并发写直接抛 database is locked
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    # WAL 模式：读写不互斥，并发写串行化而非直接失败
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@app.route("/users", methods=["GET"])
def list_users():
    with get_conn() as conn:
        rows = conn.execute("SELECT id, name FROM users").fetchall()
    return jsonify([{"id": r[0], "name": r[1]} for r in rows])


@app.route("/users", methods=["POST"])
def create_user():
    name = request.json["name"]
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO users(name) VALUES (?)", (name,))
        conn.commit()
        new_id = cur.lastrowid
    return jsonify({"id": new_id, "name": name}), 201


if __name__ == "__main__":
    init = sqlite3.connect(DB_PATH)
    init.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT)")
    init.close()
    app.run(host="0.0.0.0", port=5000, threaded=True)
```

### 2.5 验证结果

复现与验证均针对并发 POST 路径——单请求不触发锁竞争，必须并发回放。

启动服务（首次运行自动建表）：

```bash
python3 app.py
# 期望：监听 0.0.0.0:5000，启动日志无异常
```

并发回放（修复前后对比）：

```bash
# 同时发起 3 个并发 POST，复现 error.log 中的并发场景
for n in alice bob carol; do
  curl -s -X POST http://127.0.0.1:5000/users \
       -H 'Content-Type: application/json' \
       -d "{\"name\": \"$n\"}" &
done
wait
```

- **修复前（提交 `36a1c4f` 之前）**：部分请求返回 `500`，服务日志出现 `sqlite3.OperationalError: database is locked`，与 2.2 现象一致。
- **修复后（提交 `36a1c4f` 之后）**：三个并发 POST 全部返回 `201 Created`，响应体形如 `{"id": 1, "name": "alice"}`，服务日志中**不再出现** `database is locked`。

确认数据写入完整：

```bash
curl -s http://127.0.0.1:5000/users
# 期望：返回 3 条记录，id 连续且 name 覆盖 alice/bob/carol，无丢失
```

判定标准：并发 POST 返回码全部为 201、`GET /users` 返回的记录数等于发起的写入数、日志无 `database is locked`，三者同时满足即视为修复有效。

---

## Chapter-3 附录

### 3.1 术语

| 术语 | 全称 | 说明 |
|---|---|---|
| SQLite | SQLite（Structured Query Language Lite，无官方缩写展开，名义上指轻量级嵌入式 SQL 数据库引擎） | 单文件、进程内嵌入的关系型数据库，本服务的存储后端；采用单写者模型 |
| WAL | Write-Ahead Logging | SQLite 日志模式之一，写入先记入预写日志再合并入主库，读写不互斥、并发写串行化；本次修复经 `PRAGMA journal_mode=WAL` 启用 |
| busy timeout | — | SQLite 在取不到锁时的最大等待时长，默认 0（立即失败）；本次修复经连接参数 `timeout=5.0` 设为 5 秒 |
| rollback journal | — | SQLite 默认日志模式，写事务对库加排他锁、读写互斥；修复前即此模式，是 commit 报锁的成因之一 |
| PRAGMA | — | SQLite 用于查询 / 修改数据库引擎内部行为的特殊命令，如 `PRAGMA journal_mode=WAL` |
| API | Application Programming Interface | 应用编程接口，此处指 `/users` 这一组 HTTP 端点 |
| HTTP | HyperText Transfer Protocol | 超文本传输协议，客户端与 flask-api 之间的通信协议 |
| WSGI | Web Server Gateway Interface | Python Web 服务器与应用之间的标准接口；Flask 内置 WSGI 服务器以 `threaded=True` 多线程处理请求 |
| SQL | Structured Query Language | 结构化查询语言，如 `INSERT` / `SELECT` 语句 |
| GET / POST | — | HTTP 方法，分别对应 `/users` 的读（查询用户）与写（新增用户） |
| CRUD | Create, Read, Update, Delete | 数据增删改查操作的统称，本服务实现了其中 Create / Read |

### 3.2 版本控制记录

本文档对应的 git 提交历史（`git log --oneline`）原文：

```
36a1c4f Fix database is locked: WAL mode, busy timeout, with-managed connections
30c616d Add error.log capturing 'database is locked' under concurrent POST
243d2c2 Add minimal Flask /users API backed by SQLite
```

- `243d2c2`：引入最小 Flask `/users` 服务（含缺陷版 `get_conn()`）。
- `30c616d`：归档并发 POST 下复现的 `error.log`。
- `36a1c4f`：本文档所述修复——WAL 模式、busy timeout、`with` 托管连接。

### 3.3 关键文件清单

| 文件 | 位置 / 来源 | 说明 |
|---|---|---|
| `app.py` | 仓库根目录 | 服务主程序，修复落在此文件（提交 `36a1c4f`） |
| `error.log` | 仓库根目录 | 故障现场日志，2.2 现象原文出处 |
| `requirements.txt` | 仓库根目录 | 依赖声明：`Flask==3.0.0` |
| `users.db` | 服务运行目录（首次运行自动创建） | SQLite 数据文件；WAL 模式下伴随产生 `users.db-wal` / `users.db-shm`，属正常现象 |

### 3.4 参考文档

- SQLite 官方文档：*Write-Ahead Logging*（`https://www.sqlite.org/wal.html`）
- SQLite 官方文档：*PRAGMA journal_mode / busy_timeout*（`https://www.sqlite.org/pragma.html`）
- Python 标准库文档：`sqlite3 — DB-API 2.0 interface for SQLite databases`
- Flask 官方文档：*Deployment & threaded server*
