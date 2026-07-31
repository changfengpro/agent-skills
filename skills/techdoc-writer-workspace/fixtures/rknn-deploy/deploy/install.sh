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
