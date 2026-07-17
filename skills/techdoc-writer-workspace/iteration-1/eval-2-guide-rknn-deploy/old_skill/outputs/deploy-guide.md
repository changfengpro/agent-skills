# RV1126 yolov5 RKNN 推理服务部署指南

## 前言

### 概述

本文档描述在 RV1126 开发板上部署 yolov5 RKNN 推理服务（`rknn-infer`）的标准流程。该服务在板端加载经 PC 端转换得到的 `yolov5s.rknn` 模型，通过 RKNN runtime 在 NPU 上执行 yolov5 推理，并以 HTTP 服务的形式对外提供接口；服务随 systemd 常驻、开机自启、异常退出自动重启。

读者按本指南操作，可在一块全新或刚重烧固件的 RV1126 板上，从零完成模型落位、服务安装、自启注册与基本验证。文档同时说明各前置物料的来源、落位方式与重烧固件后的持久性，便于在新设备上复现整套部署。

### 平台支持

本文档涉及的平台与关键组件如下表。

| 项目 | 说明 |
|---|---|
| 目标芯片 | Rockchip RV1126 |
| NPU | 单核 NPU，`core_mask` 固定为 `0` |
| 板端运行时 | RKNN Lite（`rknnlite.api.RKNNLite`） |
| 模型转换工具 | PC 端 rknn-toolkit2（生成 `yolov5s.rknn`） |
| 推理服务语言 | Python 3（板端 `/usr/bin/python3`） |
| 服务承载 | systemd（unit 名 `rknn-infer`） |
| 模型 | yolov5s，输入 `640×640`，`num_classes = 80` |
| 监听 | `0.0.0.0:8080`（HTTP） |

### 读者对象

- 负责 RV1126 板端 bring-up 与服务部署的嵌入式工程师；
- 负责 yolov5 模型转换、需要将模型交付到板端运行的算法/转换工程师；
- 负责在批量设备上复现该推理服务的测试与运维工程师。

### 修订记录

| 版本号 | 作者 | 修改日期 | 修改说明 |
|---|---|---|---|
| V1.0 | ProctorDorsey | 2026-06-12 | 首次发布，整理 RV1126 yolov5 RKNN 推理服务标准部署流程 |

---

## Chapter-1 系统概述

### 1.1 服务架构简介

`rknn-infer` 是一个常驻的板端推理服务。其数据通路为：外部客户端通过 HTTP POST 上传图片，板端服务读取请求体，在 NPU 上执行 yolov5 推理，再将结果以 JSON 返回。模型加载与 NPU runtime 初始化在服务启动时一次性完成，请求处理阶段复用同一 runtime，避免每次请求重复加载模型。

整体部署结构如下图。

```
  PC 端（转换环境）                 RV1126 板端
+--------------------+         +-----------------------------------+
| rknn-toolkit2      |  scp /  | /userdata/rknn-infer/             |
|  yolov5 -> rknn    | ------> |   yolov5s.rknn   (模型)            |
|  生成 yolov5s.rknn |  adb    |   infer_server.py (服务主程序)    |
+--------------------+         |   deploy/config.yaml              |
                               |   deploy/rknn-infer.service       |
                               |   deploy/install.sh               |
                               +-----------------+-----------------+
                                                 | install.sh
                                                 v
                               +-----------------------------------+
                               | /etc/rknn-infer/config.yaml       |
                               | /etc/systemd/system/              |
                               |   rknn-infer.service              |
                               | systemd 拉起 python3 infer_server |
                               |   -> RKNNLite 加载 yolov5s.rknn   |
                               |   -> HTTP 监听 0.0.0.0:8080       |
                               +-----------------------------------+
```

图 1-1 RV1126 yolov5 RKNN 推理服务部署结构

### 1.2 软硬件环境

- 硬件：RV1126 开发板一块，与部署主机网络可达（用于 `scp` 与后续 HTTP 验证）。
- 板端系统：含 systemd 的 Linux rootfs，提供 `/usr/bin/python3`。
- 板端 Python 依赖：`pyyaml`（读取配置）、`rknnlite`（RKNN Lite runtime）。`rknnlite` 由 Rockchip RKNN 板端运行库提供，须随 rootfs 预置或单独安装，详见 2.1 节。
- PC 端：已安装 rknn-toolkit2，用于将 yolov5 模型转换为 RV1126 可用的 `yolov5s.rknn`。

### 1.3 部署流程总览

整个部署按下表阶段顺序执行，每个阶段对应的章节与验证标志如下。

| 阶段 | 内容 | 对应章节 | 验证标志 |
|---|---|---|---|
| 1 | 准备前置物料（模型、仓库、板端依赖） | 2.1 ~ 2.3 | 板端 `/userdata/rknn-infer/` 下文件齐全 |
| 2 | 安装服务并注册自启 | 3.1 ~ 3.2 | `install.sh` 执行无报错 |
| 3 | 确认服务状态与接口可用 | 4.1 ~ 4.2 | `systemctl status` 为 `active (running)`，HTTP 返回 `{"ok": true}` |

---

## Chapter-2 前置物料准备

本章说明部署所消费的三类输入物料：板端运行库、转换后的模型文件、服务仓库本身。三者都不随出厂 rootfs 默认包含全部内容，重烧固件后需要重新确认或重新落位，具体持久性见 2.4 节与 5.1 节。

### 2.1 板端 RKNN runtime（rknnlite）

`infer_server.py` 通过 `from rknnlite.api import RKNNLite` 调用板端 RKNN Lite 运行库。该库不是本仓库的产物，须在板端 Python 环境中可导入。

- **来源**：由 Rockchip RKNN 板端运行库提供，通常随板级 SDK / rootfs 集成。
- **落位**：随 rootfs 预置时无需额外操作；若 rootfs 未集成，则按所用 SDK 提供的板端安装包在板端安装到当前 `python3` 可见的 site-packages。
- **持久性**：若随 rootfs 集成，则重烧同一固件后仍在；若为重烧后手动安装，则重烧后丢失，须重新安装。

验证板端运行库可用：

```sh
python3 -c "from rknnlite.api import RKNNLite; print('rknnlite ok')"
```

预期输出 `rknnlite ok`。若提示 `ModuleNotFoundError: No module named 'rknnlite'`，说明运行库未就位，须先安装后再继续。

### 2.2 yolov5s.rknn 模型文件

服务加载的模型由配置文件 `deploy/config.yaml` 指定：

```yaml
model:
  path: /userdata/rknn-infer/yolov5s.rknn   # 由 PC 端 rknn-toolkit2 转换得到，须 push 到板端
  input_size: [640, 640]
  num_classes: 80
```

- **来源**：`yolov5s.rknn` 由 **PC 端 rknn-toolkit2** 将 yolov5 模型转换得到，**不在本仓库中**，也不随 rootfs 预置。转换需匹配目标平台 RV1126，模型输入尺寸为 `640×640`、类别数 `80`，与配置一致。
- **落位**：在 PC 端完成转换后，将文件传到板端，落位路径须与 `config.yaml` 中 `model.path` 一致，即 `/userdata/rknn-infer/yolov5s.rknn`：

  ```sh
  # PC 端执行，将转换好的模型 push 到板端
  scp yolov5s.rknn root@<板端IP>:/userdata/rknn-infer/yolov5s.rknn
  ```

- **持久性**：`/userdata` 下的模型文件不随构建源管理，**重烧固件后丢失**，须重新转换或重新 `scp`（见 5.1 节）。

> 说明：本指南不涵盖 PC 端 yolov5 → rknn 的转换细节（量化、数据集、转换脚本等），仅约定其产物 `yolov5s.rknn` 的输入尺寸、类别数与落位路径。转换流程以 rknn-toolkit2 官方文档为准。

### 2.3 服务仓库落位

服务主程序与 `deploy/` 下的配置、unit、安装脚本随本仓库一同分发。

- **来源**：本仓库（含 `infer_server.py`、`deploy/config.yaml`、`deploy/rknn-infer.service`、`deploy/install.sh`、`README.md`）。
- **落位**：将整个仓库 `scp` 到板端 `/userdata/rknn-infer/`，使板端目录结构为：

  ```
  /userdata/rknn-infer/
  ├── infer_server.py
  ├── yolov5s.rknn            # 见 2.2 节，单独 push
  └── deploy/
      ├── config.yaml
      ├── rknn-infer.service
      └── install.sh
  ```

  落位命令（PC 端执行）：

  ```sh
  scp -r rknn-deploy/. root@<板端IP>:/userdata/rknn-infer/
  ```

- **持久性**：同样位于 `/userdata` 下，**重烧固件后丢失**，须重新 `scp`（见 5.1 节）。

### 2.4 前置物料就绪检查

进入安装环节前，在板端确认下列文件均存在：

```sh
ls -l /userdata/rknn-infer/infer_server.py \
      /userdata/rknn-infer/yolov5s.rknn \
      /userdata/rknn-infer/deploy/config.yaml \
      /userdata/rknn-infer/deploy/rknn-infer.service \
      /userdata/rknn-infer/deploy/install.sh
```

五个文件全部列出且 `yolov5s.rknn` 大小非零，方可执行 Chapter-3。

---

## Chapter-3 服务安装与自启注册

### 3.1 安装脚本 install.sh

安装由 `deploy/install.sh` 一键完成。脚本来源于提交 `fa0e509`，内容如下：

```diff
diff --git a/deploy/install.sh b/deploy/install.sh
new file mode 100644
index 0000000..b7e2214
--- /dev/null
+++ b/deploy/install.sh
@@ -0,0 +1,10 @@
+#!/bin/sh
+# 在板端安装 rknn-infer 服务。前置：本仓库已 scp 到 /userdata/rknn-infer，
+# yolov5s.rknn 已由 PC 端转换并放到同目录。
+set -e
+install -d /etc/rknn-infer
+cp /userdata/rknn-infer/deploy/config.yaml /etc/rknn-infer/config.yaml
+cp /userdata/rknn-infer/deploy/rknn-infer.service /etc/systemd/system/
+systemctl daemon-reload
+systemctl enable --now rknn-infer
+systemctl status rknn-infer --no-pager
```

脚本各步骤的作用：

1. `set -e`：任一命令失败立即终止，避免在半安装状态下继续。
2. `install -d /etc/rknn-infer`：创建配置目录。
3. `cp .../config.yaml /etc/rknn-infer/config.yaml`：将运行配置部署到 `/etc/rknn-infer/`。这是服务实际读取的配置路径（与 3.3 节 unit 中的 `--config` 参数对应），而非 `/userdata` 下的副本。
4. `cp .../rknn-infer.service /etc/systemd/system/`：将 systemd unit 安装到系统目录。
5. `systemctl daemon-reload`：让 systemd 重新加载 unit 定义。
6. `systemctl enable --now rknn-infer`：注册开机自启并立即启动服务。
7. `systemctl status rknn-infer --no-pager`：打印当前状态，便于安装后立即确认。

### 3.2 执行安装

在板端执行：

```sh
sh /userdata/rknn-infer/deploy/install.sh
```

脚本结尾的 `systemctl status` 会回显服务状态，正常应为 `active (running)`，详见 Chapter-4。

### 3.3 systemd unit 说明

服务的常驻行为由 `deploy/rknn-infer.service` 定义。该 unit 来源于提交 `6f01b8c`，内容如下：

```diff
diff --git a/deploy/rknn-infer.service b/deploy/rknn-infer.service
new file mode 100644
index 0000000..676330f
--- /dev/null
+++ b/deploy/rknn-infer.service
@@ -0,0 +1,14 @@
+[Unit]
+Description=RKNN Inference Service (yolov5)
+After=network-online.target
+Wants=network-online.target
+
+[Service]
+Type=simple
+WorkingDirectory=/userdata/rknn-infer
+ExecStart=/usr/bin/python3 /userdata/rknn-infer/infer_server.py --config /etc/rknn-infer/config.yaml
+Restart=on-failure
+RestartSec=3
+
+[Install]
+WantedBy=multi-user.target
```

关键字段说明：

- `After` / `Wants=network-online.target`：服务对外提供 HTTP 监听，依赖网络就绪后再启动。
- `WorkingDirectory=/userdata/rknn-infer`：工作目录与仓库落位目录一致。
- `ExecStart`：以板端 `python3` 运行 `infer_server.py`，并通过 `--config` 指定配置文件 `/etc/rknn-infer/config.yaml`（即 `install.sh` 部署的那一份）。
- `Restart=on-failure` / `RestartSec=3`：服务异常退出后，systemd 间隔 3 秒自动重启，保证常驻。
- `WantedBy=multi-user.target`：`enable` 后随系统进入多用户态时自启。

### 3.4 服务主程序 infer_server.py

服务主程序 `infer_server.py` 来源于提交 `2b0b232`，负责读取配置、初始化 RKNN runtime 并启动 HTTP 服务。其逻辑顺序为：解析 `--config` 参数 → 加载 YAML 配置 → 用配置中的模型路径与 `core_mask` 初始化 RKNN runtime → 在配置指定的地址与端口上启动 `HTTPServer` 常驻。

```diff
diff --git a/infer_server.py b/infer_server.py
new file mode 100644
index 0000000..1ebc108
--- /dev/null
+++ b/infer_server.py
@@ -0,0 +1,44 @@
+#!/usr/bin/env python3
+"""RV1126 RKNN 推理 HTTP 服务：加载 rknn 模型，对上传图片做 yolov5 推理。"""
+import argparse
+import yaml
+from http.server import BaseHTTPRequestHandler, HTTPServer
+from rknnlite.api import RKNNLite
+
+
+def load_config(path):
+    with open(path) as f:
+        return yaml.safe_load(f)
+
+
+def init_runtime(cfg):
+    rknn = RKNNLite()
+    rknn.load_rknn(cfg["model"]["path"])
+    rknn.init_runtime(core_mask=cfg["runtime"]["core_mask"])
+    return rknn
+
+
+class InferHandler(BaseHTTPRequestHandler):
+    rknn = None
+
+    def do_POST(self):
+        length = int(self.headers.get("Content-Length", 0))
+        _ = self.rfile.read(length)
+        # 推理逻辑略：解码图片 -> letterbox -> rknn.inference -> 后处理
+        self.send_response(200)
+        self.end_headers()
+        self.wfile.write(b'{"ok": true}')
+
+
+def main():
+    ap = argparse.ArgumentParser()
+    ap.add_argument("--config", required=True)
+    args = ap.parse_args()
+    cfg = load_config(args.config)
+    InferHandler.rknn = init_runtime(cfg)
+    srv = HTTPServer((cfg["server"]["listen"], cfg["server"]["port"]), InferHandler)
+    srv.serve_forever()
+
+
+if __name__ == "__main__":
+    main()
```

说明：`init_runtime()` 在服务启动时一次性 `load_rknn()` 并 `init_runtime(core_mask=...)`，随后将 runtime 句柄挂到 `InferHandler.rknn` 上由各请求复用。`do_POST()` 当前的推理逻辑以 `# 推理逻辑略` 占位（解码图片 → letterbox → `rknn.inference` → 后处理），并固定返回 `{"ok": true}`；本指南据此把该返回作为接口连通性的验证标志（见 4.2 节）。完整推理后处理的实现以本仓库后续版本为准，不在本部署指南范围内。

### 3.5 配置项参考

服务行为由 `/etc/rknn-infer/config.yaml` 控制，各字段含义如下表。配置文件来源于提交 `6f01b8c`。

| 配置项 | 取值 | 说明 |
|---|---|---|
| `model.path` | `/userdata/rknn-infer/yolov5s.rknn` | 模型文件路径，须与板端落位一致（见 2.2 节） |
| `model.input_size` | `[640, 640]` | 模型输入尺寸 |
| `model.num_classes` | `80` | 类别数 |
| `runtime.core_mask` | `0` | RV1126 单核 NPU，固定为 `0` |
| `runtime.perf_detail` | `false` | 是否输出性能细节 |
| `server.listen` | `0.0.0.0` | 监听地址 |
| `server.port` | `8080` | 监听端口 |
| `server.log_level` | `info` | 日志级别 |

修改配置后须重启服务使其生效：

```sh
# 修改 /etc/rknn-infer/config.yaml 后
systemctl restart rknn-infer
```

注意：服务读取的是 `/etc/rknn-infer/config.yaml`，而非 `/userdata/rknn-infer/deploy/config.yaml`。若仅改了 `/userdata` 下的副本而未重新部署，配置不会生效。

---

## Chapter-4 部署验证

### 4.1 服务状态验证

安装脚本结尾已调用一次 `systemctl status`。任何时候均可重新查看服务状态：

```sh
systemctl status rknn-infer --no-pager
```

判定标准：`Active:` 行显示 `active (running)`，且 `Loaded:` 行包含 `enabled`（表示已注册开机自启）。

查看服务日志：

```sh
journalctl -u rknn-infer --no-pager
```

### 4.2 接口连通性验证

服务监听 `0.0.0.0:8080`，向其发送一个 HTTP POST 请求确认接口可用：

```sh
curl -s -X POST http://<板端IP>:8080/ --data-binary @test.jpg
```

判定标准：返回 `{"ok": true}`，即说明服务已正常加载模型、HTTP 通路可用。

> 说明：如 3.4 节所述，当前 `do_POST()` 固定返回 `{"ok": true}`，该返回用于验证服务进程与监听通路，不代表已返回真实检测框。真实推理结果的接口约定以后续版本为准。

### 4.3 开机自启验证

由于 unit 已 `enable`，重启板端后服务应自动拉起：

```sh
reboot
# 重启完成后
systemctl is-enabled rknn-infer    # 预期输出 enabled
systemctl is-active rknn-infer     # 预期输出 active
```

---

## Chapter-5 重复部署与重烧固件后的恢复

本章不涉及部署过程中遇到的故障——本次部署流程顺利、无报错。这里集中说明在**全新设备或重烧固件后**重走部署时最容易遗漏的一点：部分前置物料不随构建源持久化，重烧后会回到出厂态而丢失。

### 5.1 重烧固件后须重新落位的物料

下表汇总各物料在重烧同一固件后的持久性。凡标注"否"的，重烧后须按对应章节重新落位，否则服务无法启动或 unit 缺失。

| 物料 | 位置 | 重烧后是否持久 | 重做方式 |
|---|---|---|---|
| `yolov5s.rknn` | `/userdata/rknn-infer/yolov5s.rknn` | 否 | 从 PC 端重新转换并 `scp`（见 2.2 节） |
| 服务仓库（`infer_server.py` 等） | `/userdata/rknn-infer/` | 否 | 重新 `scp` 整个仓库（见 2.3 节） |
| 运行配置 | `/etc/rknn-infer/config.yaml` | 否 | 重跑 `install.sh` 重新部署（见 3.1 节） |
| systemd unit | `/etc/systemd/system/rknn-infer.service` | 否 | 重跑 `install.sh` 重新部署（见 3.1 节） |
| 自启注册（`enable`） | systemd 状态 | 否 | `install.sh` 中的 `enable --now` 会重新注册 |
| 板端 `rknnlite` 运行库 | 板端 site-packages | 视固件而定 | 若随 rootfs 集成则持久；若重烧后手动安装则须重装（见 2.1 节） |

### 5.2 重烧后的标准恢复顺序

重烧固件后，按下列顺序即可恢复服务（即 Chapter-2、Chapter-3 的子集）：

1. 确认板端 `rknnlite` 可导入（2.1 节）。
2. 重新 `scp` 服务仓库到 `/userdata/rknn-infer/`（2.3 节）。
3. 重新 `scp` `yolov5s.rknn` 到 `/userdata/rknn-infer/`（2.2 节）。
4. 执行 `sh /userdata/rknn-infer/deploy/install.sh`（3.2 节）。
5. 按 Chapter-4 验证。

> 提示：若重烧后报 `No such file or directory`（找不到 `infer_server.py` 或 `yolov5s.rknn`），或服务因模型加载失败反复重启，几乎都是上述 `/userdata` 物料未重新落位所致——它们不在构建源中，重烧后必然丢失。

---

## Chapter-6 附录

### 6.1 术语表

| 术语 | 全称 | 说明 |
|---|---|---|
| RV1126 | Rockchip Vision 1126 | 本文档目标 Rockchip 视觉处理芯片，单核 NPU |
| RKNN | Rockchip Neural Network | Rockchip 神经网络推理格式与运行时，`.rknn` 为其模型文件后缀 |
| RKNN Lite | RKNN Lite Runtime | 板端轻量 RKNN 运行库，本服务通过 `rknnlite.api.RKNNLite` 调用 |
| rknn-toolkit2 | RKNN Toolkit 2 | PC 端模型转换工具，将 yolov5 等模型转换为 `.rknn` |
| NPU | Neural Processing Unit | 神经网络处理单元，RV1126 上执行推理的硬件 |
| yolov5 | You Only Look Once v5 | 目标检测模型；本文档使用 yolov5s 变体 |
| `core_mask` | Core Mask | RKNN runtime 指定 NPU 核心的掩码，RV1126 单核固定为 `0` |
| systemd | system and service manager | Linux 系统与服务管理器，承载本服务的常驻与自启 |
| unit | systemd unit | systemd 的服务定义文件，本文档指 `rknn-infer.service` |
| HTTP | HyperText Transfer Protocol | 超文本传输协议，本服务对外接口协议 |
| letterbox | — | 保持长宽比的等比缩放加灰边填充，yolov5 预处理常用步骤 |

### 6.2 关键文件清单

| 文件 | 位置 / 来源 | 重烧后持久 | 说明 |
|---|---|---|---|
| `infer_server.py` | `/userdata/rknn-infer/`（本仓库） | 否 | 推理服务主程序 |
| `yolov5s.rknn` | `/userdata/rknn-infer/`（PC 端 rknn-toolkit2 转换） | 否 | 模型文件，不在仓库与 rootfs 中 |
| `config.yaml` | 源：仓库 `deploy/`；运行：`/etc/rknn-infer/` | 否 | 运行配置，由 `install.sh` 部署 |
| `rknn-infer.service` | 源：仓库 `deploy/`；安装：`/etc/systemd/system/` | 否 | systemd unit |
| `install.sh` | `/userdata/rknn-infer/deploy/`（本仓库） | 否 | 一键安装脚本 |
| `rknnlite` 运行库 | 板端 site-packages（SDK / rootfs） | 视固件而定 | 板端 RKNN runtime，见 2.1 节 |

### 6.3 版本控制记录

本文档对应的服务代码提交记录（`git log --oneline`）：

```
fa0e509 Add install.sh to deploy config and enable systemd service
2b0b232 Add infer_server.py: load rknn model and serve HTTP inference
6f01b8c Add systemd unit, runtime config and README for rknn-infer
```

各提交与本文档章节的对应关系：

| 提交 | 内容 | 对应章节 |
|---|---|---|
| `6f01b8c` | systemd unit、运行配置、README | 3.3、3.5 |
| `2b0b232` | `infer_server.py` 推理服务主程序 | 3.4 |
| `fa0e509` | `install.sh` 安装脚本并启用服务 | 3.1 |

### 6.4 参考文档

- 本仓库 `README.md`
- Rockchip rknn-toolkit2 官方文档（PC 端模型转换）
- Rockchip RKNN Lite 板端运行库文档（板端 runtime 接口）
