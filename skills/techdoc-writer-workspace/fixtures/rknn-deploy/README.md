# rknn-infer

RV1126 上基于 RKNN runtime 的 yolov5 推理服务，随 systemd 常驻。

- `deploy/rknn-infer.service` — systemd unit
- `deploy/config.yaml` — 运行配置（模型路径、NPU core、监听端口）
- `infer_server.py` — 推理服务主程序
