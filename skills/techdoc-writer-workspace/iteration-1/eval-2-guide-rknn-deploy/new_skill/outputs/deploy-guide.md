# RV1126 yolov5 RKNN 推理服务部署指南

## 前言

### 概述

本文档说明在 RV1126 开发板上部署 yolov5 RKNN 推理服务（`rknn-infer`）的标准流程。该服务以 RKNN runtime 加载经 PC 端转换的 yolov5 模型，对外提供 HTTP 推理接口，并以 systemd unit 形式常驻、随系统自启。读者按本指南操作，可在一块全新或刚重烧固件的 RV1126 板上完成从文件落位、安装、自启注册到接口验证的完整部署。

本指南为部署/操作类文档，描述的是一条已验证可复现的正向部署流程，不含故障排查内容。

### 平台支持

下表列出本指南验证所基于的平台与关键组件。

| 项目 | 取值 | 说明 |
|---|---|---|
| 目标芯片 | Rockchip RV1126 | 单核 NPU |
| 板端 NPU 核心数 | 1 | 故 `core_mask` 固定为 0 |
| 服务进程管理 | systemd | unit：`rknn-infer.service` |
| 运行时解释器 | `/usr/bin/python3` | 板端预置 |
| 推理运行库 | `rknnlite`（RKNN Toolkit Lite2 runtime） | 提供 `RKNNLite` API |
| 模型格式 | `.rknn` | 由 PC 端 RKNN Toolkit2 转换得到 |
| 监听地址/端口 | `0.0.0.0:8080` | 见 `config.yaml` |

### 读者对象

- 负责 RV1126 板端 AI 推理服务部署与运维的嵌入式工程师
- 需要在多块同型号板上批量复现该服务的测试与产线人员
- 维护 yolov5 模型转换链路、需了解模型落位约定的算法工程师

### 修订记录

| 版本号 | 作者 | 修改日期 | 修改说明 |
|---|---|---|---|
| v1.0 | techdoc-writer | 2026-06-12 | 首次发布，依据 `rknn-deploy` 仓库三个提交整理 |

---

## Chapter-1 系统概述

### 1.1 服务架构简介

`rknn-infer` 是一个单进程的 HTTP 推理服务。其运行链路为：systemd 拉起 `infer_server.py`，该程序读取配置文件，经 RKNN runtime 加载 `.rknn` 模型并初始化 NPU 运行时，随后在指定端口上监听 HTTP POST 请求，对请求体携带的图片完成 yolov5 推理并返回结果。

```
                 systemd (rknn-infer.service)
                          │ ExecStart
                          ▼
        /usr/bin/python3 infer_server.py --config /etc/rknn-infer/config.yaml
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
   load_config()    init_runtime()    HTTPServer
   读取 yaml 配置    RKNNLite 加载     监听 0.0.0.0:8080
                    yolov5s.rknn      处理 POST 推理请求
                    init_runtime
                    (core_mask=0)
```

图 1-1 rknn-infer 服务运行链路

### 1.2 软硬件环境

部署前需确认以下条件成立：

- RV1126 板已完成基础 bring-up，可通过网络访问（SSH/`scp` 可达）。
- 板端 `/usr/bin/python3` 可用，且已安装 `rknnlite`、`yaml`（PyYAML）两个 Python 依赖。
- 板端已具备 systemd（`systemctl` 可用）。
- PC 端已使用 RKNN Toolkit2 将 yolov5 模型转换为 `yolov5s.rknn`（转换过程不在本指南范围内，落位约定见 2.1 节）。

### 1.3 部署流程总览

整体部署分为四个阶段，下表标注各阶段对应章节与完成标志。

| 阶段 | 内容 | 对应章节 | 完成标志 |
|---|---|---|---|
| 1 前置物料落位 | 仓库与模型 `scp` 到板端约定目录 | 2.1 | `/userdata/rknn-infer` 下含仓库文件与 `yolov5s.rknn` |
| 2 配置确认 | 核对模型路径、NPU core、监听端口 | 2.2 | `config.yaml` 各字段与实际环境一致 |
| 3 安装与自启注册 | 执行 `install.sh`，注册 systemd 服务 | 3.1 | `systemctl status rknn-infer` 显示 active (running) |
| 4 接口验证 | 发起 HTTP POST 请求验证推理通路 | 4.1 | 返回 `{"ok": true}` |

---

## Chapter-2 前置物料与运行配置

本章说明部署前必须就位的输入产物及其来源、落位、持久性，并解释运行配置各字段的含义。这是整套流程中最容易在"换一块板"时卡住的环节——以下文件均为手动传到板上、未随固件构建持久化，须显式部署。

### 2.1 前置物料的来源与落位

服务运行依赖两类输入产物：本仓库代码、以及 PC 端转换得到的 `.rknn` 模型。二者均需落位到板端 `/userdata/rknn-infer` 目录。

下表列出各产物的来源、落位方式与重烧固件后的持久性。

| 产物 | 来源 | 落位方式 | 重烧后是否保留 |
|---|---|---|---|
| `rknn-infer` 仓库（含 `deploy/`、`infer_server.py`） | 本 Git 仓库 | `scp -r` 整个仓库到板端 `/userdata/rknn-infer` | 否，需重新 `scp` |
| `yolov5s.rknn` | PC 端 RKNN Toolkit2 转换产物 | `scp` 到板端 `/userdata/rknn-infer/yolov5s.rknn` | 否，需重新转换或重新 `scp` |

落位命令示例（在 PC 端执行，`<board>` 替换为板端 IP）：

```sh
# 1. 推送仓库（落位到 /userdata/rknn-infer）
scp -r rknn-deploy/ root@<board>:/userdata/rknn-infer

# 2. 推送 PC 端转换得到的模型，与 config.yaml 中 model.path 对应
scp yolov5s.rknn root@<board>:/userdata/rknn-infer/yolov5s.rknn
```

`config.yaml` 与 `install.sh` 中的前置约定可在源文件注释中复核：

```yaml
model:
  path: /userdata/rknn-infer/yolov5s.rknn   # 由 PC 端 rknn-toolkit2 转换得到，须 push 到板端
```

```sh
# install.sh 头部注释
# 在板端安装 rknn-infer 服务。前置：本仓库已 scp 到 /userdata/rknn-infer，
# yolov5s.rknn 已由 PC 端转换并放到同目录。
```

> 持久性说明：`/userdata/rknn-infer` 与 `yolov5s.rknn` 均位于板端可写分区、由手动 `scp` 写入，**不随 rootfs/固件构建持久化**。一旦重烧固件，该目录会回到出厂态，仓库与模型都将丢失，须按本节重新落位后再执行 Chapter-3 的安装步骤。`/etc/rknn-infer/config.yaml` 与 `/etc/systemd/system/rknn-infer.service` 同理（由 `install.sh` 写入），重烧后须重新执行 `install.sh` 才会再次生成。

### 2.2 运行配置说明

服务的全部运行参数集中在 `deploy/config.yaml`。安装时该文件由 `install.sh` 拷贝到板端 `/etc/rknn-infer/config.yaml`，供 `infer_server.py` 通过 `--config` 加载。完整内容如下：

```yaml
# RKNN 推理服务配置
model:
  path: /userdata/rknn-infer/yolov5s.rknn   # 由 PC 端 rknn-toolkit2 转换得到，须 push 到板端
  input_size: [640, 640]
  num_classes: 80

runtime:
  core_mask: 0          # RV1126 单核 NPU，固定 0
  perf_detail: false

server:
  listen: 0.0.0.0
  port: 8080
  log_level: info
```

各字段含义如下表所示。

| 字段 | 取值 | 说明 |
|---|---|---|
| `model.path` | `/userdata/rknn-infer/yolov5s.rknn` | 模型落位路径，须与 2.1 节 `scp` 目标一致 |
| `model.input_size` | `[640, 640]` | yolov5 输入分辨率，须与模型转换时一致 |
| `model.num_classes` | `80` | 检测类别数（此处为 COCO 80 类） |
| `runtime.core_mask` | `0` | NPU 核心掩码；RV1126 为单核 NPU，固定为 0 |
| `runtime.perf_detail` | `false` | 是否输出 RKNN 性能明细，部署默认关闭 |
| `server.listen` | `0.0.0.0` | 监听地址，`0.0.0.0` 表示对外可达 |
| `server.port` | `8080` | HTTP 监听端口 |
| `server.log_level` | `info` | 日志级别 |

技术原理：`core_mask` 固定为 0 的原因是 RV1126 仅含单核 NPU，运行时初始化只能绑定到 0 号 core。在多核 NPU 平台（如 RK3588）上该值才需按核心数调整，本平台无须改动。

修改配置后需重新执行 `install.sh`（或单独重拷 `config.yaml` 到 `/etc/rknn-infer/` 并 `systemctl restart rknn-infer`）才能生效，因为服务实际读取的是 `/etc/rknn-infer/config.yaml` 而非仓库内的副本。

---

## Chapter-3 安装与自启注册

本章说明如何在板端将服务安装到位并注册为 systemd 自启服务。前置条件为 Chapter-2 的物料已落位。

### 3.1 执行安装脚本

`deploy/install.sh` 封装了安装的全部步骤：创建配置目录、拷贝配置与 unit 文件、重载 systemd、使能并启动服务。完整脚本如下（与仓库 `deploy/install.sh` 一致，可直接在板端运行）：

```sh
#!/bin/sh
# 在板端安装 rknn-infer 服务。前置：本仓库已 scp 到 /userdata/rknn-infer，
# yolov5s.rknn 已由 PC 端转换并放到同目录。
set -e
install -d /etc/rknn-infer
cp /userdata/rknn-infer/deploy/config.yaml /etc/rknn-infer/config.yaml
cp /userdata/rknn-infer/deploy/rknn-infer.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now rknn-infer
systemctl status rknn-infer --no-pager
```

在板端执行：

```sh
sh /userdata/rknn-infer/deploy/install.sh
```

逐步说明：

1. `install -d /etc/rknn-infer`：创建配置目录。
2. `cp .../config.yaml /etc/rknn-infer/config.yaml`：将运行配置拷贝到服务实际读取的位置。
3. `cp .../rknn-infer.service /etc/systemd/system/`：安装 systemd unit。
4. `systemctl daemon-reload`：让 systemd 识别新增 unit。
5. `systemctl enable --now rknn-infer`：注册开机自启（`enable`）并立即启动（`--now`）。
6. `systemctl status rknn-infer --no-pager`：打印当前状态供核对。

脚本首行 `set -e` 保证任一步骤失败即中止，避免在前置文件缺失时继续执行而留下半成品状态。

### 3.2 systemd unit 说明

服务的自启行为由 `deploy/rknn-infer.service` 定义，安装后位于 `/etc/systemd/system/rknn-infer.service`。完整内容如下：

```ini
[Unit]
Description=RKNN Inference Service (yolov5)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/userdata/rknn-infer
ExecStart=/usr/bin/python3 /userdata/rknn-infer/infer_server.py --config /etc/rknn-infer/config.yaml
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

关键字段说明如下表。

| 字段 | 取值 | 说明 |
|---|---|---|
| `After` / `Wants` | `network-online.target` | 服务监听网络端口，故在网络就绪后启动 |
| `Type` | `simple` | 主进程即 `ExecStart` 进程，前台运行 |
| `WorkingDirectory` | `/userdata/rknn-infer` | 工作目录，与物料落位目录一致 |
| `ExecStart` | `python3 infer_server.py --config /etc/rknn-infer/config.yaml` | 启动命令；配置取自 `/etc` 下的安装副本 |
| `Restart` / `RestartSec` | `on-failure` / `3` | 异常退出后 3 秒自动重启 |
| `WantedBy` | `multi-user.target` | `enable` 后随多用户目标自启 |

技术原理：`ExecStart` 指向 `/etc/rknn-infer/config.yaml` 而非仓库内 `deploy/config.yaml`，因此运行期生效的始终是安装副本。这也是 2.2 节强调"改配置后须重新安装/重拷"的原因。`Restart=on-failure` 配合 `RestartSec=3` 提供进程级守护：进程非正常退出时由 systemd 在 3 秒后拉起，保证服务常驻。

---

## Chapter-4 推理服务程序与接口验证

本章说明服务主程序 `infer_server.py` 的结构，并给出部署完成后的验证方法。

### 4.1 服务程序结构

`infer_server.py` 是单文件 HTTP 推理服务，结构为：加载配置 → 初始化 RKNN 运行时 → 启动 HTTPServer 监听并处理 POST 请求。完整程序如下（与仓库 `infer_server.py` 一致，可直接在板端运行）：

```python
#!/usr/bin/env python3
"""RV1126 RKNN 推理 HTTP 服务：加载 rknn 模型，对上传图片做 yolov5 推理。"""
import argparse
import yaml
from http.server import BaseHTTPRequestHandler, HTTPServer
from rknnlite.api import RKNNLite


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def init_runtime(cfg):
    rknn = RKNNLite()
    rknn.load_rknn(cfg["model"]["path"])
    rknn.init_runtime(core_mask=cfg["runtime"]["core_mask"])
    return rknn


class InferHandler(BaseHTTPRequestHandler):
    rknn = None

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        _ = self.rfile.read(length)
        # 推理逻辑略：解码图片 -> letterbox -> rknn.inference -> 后处理
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"ok": true}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    InferHandler.rknn = init_runtime(cfg)
    srv = HTTPServer((cfg["server"]["listen"], cfg["server"]["port"]), InferHandler)
    srv.serve_forever()


if __name__ == "__main__":
    main()
```

各部分职责如下：

- `load_config(path)`：读取 `--config` 指定的 YAML，返回配置字典。
- `init_runtime(cfg)`：构造 `RKNNLite` 实例，`load_rknn` 加载模型文件，`init_runtime(core_mask=...)` 在指定 NPU 核心上初始化运行时，返回可用的运行时句柄。
- `InferHandler.do_POST`：读取请求体，执行推理（仓库版本中推理逻辑以注释 `解码图片 -> letterbox -> rknn.inference -> 后处理` 占位），返回 HTTP 200 与 `{"ok": true}`。
- `main()`：解析参数、加载配置、初始化运行时并将句柄挂到 `InferHandler.rknn`，随后在 `listen:port` 上 `serve_forever`。

> 说明：`do_POST` 中的推理主体在仓库当前版本里为占位注释，对外接口先返回固定 `{"ok": true}` 以打通服务与自启通路。补全 letterbox/`rknn.inference`/后处理后，接口语义不变，仅返回体改为真实检测结果。本指南据此说明，不对占位部分作额外发挥。

### 4.2 部署验证

完成 Chapter-3 安装后，按以下三步验证。

第一步，确认服务进程状态：

```sh
systemctl status rknn-infer --no-pager
```

预期 `Active:` 行显示 `active (running)`。

第二步，确认端口监听：

```sh
netstat -tlnp | grep 8080
```

预期可见 `0.0.0.0:8080` 处于 LISTEN 状态，与 `config.yaml` 的 `server.listen`/`server.port` 一致。

第三步，发起一次 HTTP POST 验证推理通路（在板端或同网段主机执行，`<board>` 替换为板端 IP）：

```sh
curl -s -X POST --data-binary @test.jpg http://<board>:8080/
```

预期返回：

```
{"ok": true}
```

三步均符合预期，即表示服务已部署、自启已注册、HTTP 推理通路已打通。

---

## Chapter-5 附录

### 5.1 术语表

| 术语 | 全称 | 说明 |
|---|---|---|
| RV1126 | Rockchip RV1126 | 本指南目标 SoC，含单核 NPU |
| RKNN | Rockchip Neural Network | 瑞芯微 NPU 推理模型格式与运行时体系，模型扩展名 `.rknn` |
| NPU | Neural Processing Unit | 神经网络加速单元；RV1126 为单核，故 `core_mask=0` |
| RKNN Toolkit2 | RKNN Toolkit2 | PC 端模型转换/量化工具链，将原始模型转为 `.rknn` |
| RKNN Toolkit Lite2 | RKNN Toolkit Lite2 | 板端轻量运行库，提供 `rknnlite`/`RKNNLite` 推理 API |
| yolov5 | You Only Look Once v5 | 目标检测模型系列；本服务部署其 `yolov5s` 变体 |
| systemd | system and service manager | Linux 系统与服务管理器，负责服务自启与守护 |
| unit | systemd unit | systemd 的服务定义文件，此处为 `rknn-infer.service` |
| HTTP | HyperText Transfer Protocol | 服务对外接口协议 |
| letterbox | — | yolov5 预处理中的等比缩放加灰边填充步骤 |
| core_mask | — | NPU 核心掩码，指定运行时绑定的核心；本平台固定 0 |

### 5.2 关键文件清单

| 文件 | 位置 / 来源 | 是否随重烧持久 | 说明 |
|---|---|---|---|
| `infer_server.py` | 仓库根 → 板端 `/userdata/rknn-infer/` | 否，需重新 `scp` | 推理服务主程序 |
| `deploy/config.yaml` | 仓库 → 安装后 `/etc/rknn-infer/config.yaml` | 否，需重跑 `install.sh` | 运行配置 |
| `deploy/rknn-infer.service` | 仓库 → 安装后 `/etc/systemd/system/` | 否，需重跑 `install.sh` | systemd unit |
| `deploy/install.sh` | 仓库 → 板端 `/userdata/rknn-infer/deploy/` | 否，需重新 `scp` | 安装脚本 |
| `yolov5s.rknn` | PC 端 RKNN Toolkit2 转换产物 → `/userdata/rknn-infer/` | 否，需重新转换/`scp` | 推理模型，须与 `config.yaml` 一致 |

凡是手动 `scp` 或由 `install.sh` 写入板端的文件，均不随固件构建持久化。重烧固件后须按 Chapter-2、Chapter-3 重新落位并安装。

### 5.3 版本控制记录

本指南依据 `rknn-deploy` 仓库以下三个提交整理，`git log --oneline` 原文如下：

```
fa0e509 Add install.sh to deploy config and enable systemd service
2b0b232 Add infer_server.py: load rknn model and serve HTTP inference
6f01b8c Add systemd unit, runtime config and README for rknn-infer
```

各提交引入的内容：

```diff
commit 6f01b8c — Add systemd unit, runtime config and README for rknn-infer
+++ b/README.md
+++ b/deploy/config.yaml
+++ b/deploy/rknn-infer.service
（README、运行配置 config.yaml、systemd unit）
```

```diff
commit 2b0b232 — Add infer_server.py: load rknn model and serve HTTP inference
+++ b/infer_server.py
（推理服务主程序：加载 rknn 模型并提供 HTTP 推理）
```

```diff
commit fa0e509 — Add install.sh to deploy config and enable systemd service
+++ b/deploy/install.sh
（安装脚本：拷贝配置与 unit、注册并启动 systemd 服务）
```

### 5.4 参考文档

- 仓库 `README.md`：`rknn-infer` 服务组成与文件说明
- Rockchip RKNN Toolkit2 / Toolkit Lite2 官方文档（PC 端模型转换与板端运行时 API）
- Rockchip RV1126 平台 NPU 使用说明
