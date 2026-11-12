# 健康检查：OTA 接口能报“运行正常”（说明应用起来了、data/.config.yaml 读到了），再对 WebSocket
# 端口做一次真实握手。不查对话模型：模型网关是可选的，没接上时服务也健康。
import asyncio
import os
import sys
import urllib.request

# 出网插件带代理变量；回环地址本就不该走代理，明确清掉更稳。
for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(key, None)

try:
    with urllib.request.urlopen("http://127.0.0.1:8003/xiaozhi/ota/", timeout=5) as response:
        body = response.read().decode("utf-8", "replace")
except Exception as error:
    print(f"OTA 接口连不上：{error}")
    sys.exit(1)
if "运行正常" not in body:
    print(f"OTA 接口异常：{body[:120]}")
    sys.exit(1)

import websockets


async def websocket_handshake():
    async with websockets.connect("ws://127.0.0.1:8000/xiaozhi/v1/", open_timeout=10):
        pass


try:
    asyncio.run(websocket_handshake())
except Exception as error:
    print(f"WebSocket 握手失败：{error}")
    sys.exit(1)
