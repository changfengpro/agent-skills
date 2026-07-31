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
