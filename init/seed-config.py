# 一次性服务：应用启动前写 data/.config.yaml（上游的覆盖配置，见上游 config.yaml 开头的说明），
# 并准备本地语音识别模型。每次创建容器都会重跑，必须幂等：模型只下载一次，地址按本次注入的写。
# 只写下面这些键，其余配置保持上游 config.yaml 的默认（角色提示词、音色、时长这些都在上游那边）。
#
# - server.websocket / server.vision_explain：OTA 下发给设备的地址，取 WONTON_LAN_ADDRESSES 的第一个。
#   局域网开关没开（变量为空串）时不写：端口本来就没开，OTA 会按容器地址生成，等开关打开后
#   核心重建容器，这里会重跑并写进真实地址。
# - selected_module.LLM + LLM.WontonLLM：模型网关（OpenAI 兼容）。网关没接上时选回上游默认的
#   ChatGLMLLM（占位 key 只写日志，服务照常启动，详情页有“没接上”提示），并删掉自己写过的条目。
# - ASR 用 Vosk 小模型（约 43 MB，首次运行下载），识别在本机做；上游默认的本地 FunASR 要下载
#   约 1 GB 模型，最简化部署不采用。

import io
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

from ruamel.yaml import YAML

PROJECT = Path("/opt/xiaozhi-esp32-server")
DATA = PROJECT / "data"
CONFIG_PATH = DATA / ".config.yaml"
MODEL_DIR = DATA / "models" / "vosk-model-small-cn-0.22"
MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip"
MODEL_SENTINEL = MODEL_DIR / "conf" / "model.conf"

LAN_PORTS_WS = 8000
LAN_PORTS_HTTP = 8003


def fail(message):
    print(f"一次性服务失败：{message}", file=sys.stderr)
    sys.exit(1)


def download_model():
    """下载并解压 Vosk 识别模型；已就绪时不动。失败如实报错，装不上好过装上听不见。"""
    if MODEL_SENTINEL.is_file():
        print(f"识别模型已就绪：{MODEL_DIR}")
        return
    print(f"下载识别模型 {MODEL_URL}（约 44 MB）……")
    DATA.mkdir(parents=True, exist_ok=True)
    try:
        request = urllib.request.Request(MODEL_URL)
        with urllib.request.urlopen(request, timeout=120) as response, io.BytesIO() as buf:
            if response.status != 200:
                fail(f"模型下载 HTTP {response.status}")
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                buf.write(chunk)
            buf.seek(0)
            with zipfile.ZipFile(buf) as archive:
                names = archive.namelist()
                if not any(n.startswith("vosk-model-small-cn-0.22/") for n in names):
                    fail(f"下载的内容不对：{names[:3]}")
                archive.extractall(DATA / "models")
    except Exception as error:
        fail(f"下载或解压识别模型失败：{error}")
    if not MODEL_SENTINEL.is_file():
        fail(f"解压后没有识别模型：{MODEL_DIR}")
    print(f"识别模型已下载：{MODEL_DIR}")


def main():
    lan_addresses = os.environ.get("WONTON_LAN_ADDRESSES", "").strip()
    base_url = os.environ.get("WONTON_MODEL_BASE_URL", "").strip()
    api_key = os.environ.get("WONTON_MODEL_API_KEY", "").strip()
    default_model = os.environ.get("WONTON_MODEL_DEFAULT", "").strip()
    gateway_connected = bool(base_url and api_key and default_model)

    yaml = YAML(typ="safe")
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as file:
            config = yaml.load(file) or {}
        if not isinstance(config, dict):
            fail(f"{CONFIG_PATH} 不是键值形式的 YAML：{type(config)}")
    else:
        config = {}

    server = config.setdefault("server", {})
    if lan_addresses:
        address = lan_addresses.split(",")[0].strip()
        if not address:
            fail(f"WONTON_LAN_ADDRESSES 里没有可用的地址：{lan_addresses!r}")
        server["websocket"] = f"ws://{address}:{LAN_PORTS_WS}/xiaozhi/v1/"
        server["vision_explain"] = f"http://{address}:{LAN_PORTS_HTTP}/mcp/vision/explain"
        print(f"设备地址按 {address} 写入")

    selected = config.setdefault("selected_module", {})
    llm = config.setdefault("LLM", {})
    if gateway_connected:
        selected["LLM"] = "WontonLLM"
        llm["WontonLLM"] = {
            "type": "openai",
            "model_name": default_model,
            "base_url": base_url,
            "api_key": api_key,
        }
        print(f"对话模型走模型网关：{default_model}")
    else:
        selected["LLM"] = "ChatGLMLLM"
        llm.pop("WontonLLM", None)
        print("模型网关没接上：对话不可用，等网关装好后核心会重建容器并自动接上")

    selected["ASR"] = "VoskASR"
    config.setdefault("ASR", {})["VoskASR"] = {
        "type": "vosk",
        "model_path": "data/models/vosk-model-small-cn-0.22",
        "output_dir": "tmp/",
    }
    download_model()

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = CONFIG_PATH.with_suffix(".yaml.tmp")
    with open(tmp_path, "w", encoding="utf-8") as file:
        yaml.dump(config, file)
    tmp_path.rename(CONFIG_PATH)
    print(f"已写入 {CONFIG_PATH}")


main()
