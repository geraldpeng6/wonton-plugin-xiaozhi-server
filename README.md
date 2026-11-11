# 小智语音服务（xiaozhi-esp32-server）

给小智 AI 音箱/机器人（[78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) 等设备）用的自建后端：设备连家里这台服务器，说话、回答都不经过官方服务。上游项目 [xinnan-tech/xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server)（MIT），本插件是最简化部署：只装 server，不带智控台（manager-api / manager-web）和 MySQL/Redis。

## 工作方式

| 模块 | 走哪 | 说明 |
| --- | --- | --- |
| 对话模型 | 云吞模型网关 | 清单申请 `models`，注入的 `WONTON_MODEL_*` 由一次性服务写进 `data/.config.yaml`（上游的覆盖配置）。网关没接上时选回上游默认的 ChatGLMLLM（占位 key），对话不可用；网关装好后核心重建容器，自动接上。 |
| 语音识别 | 本机 Vosk 小模型 | `vosk-model-small-cn-0.22`（约 42 MB，Apache 2.0），首次安装时由一次性服务从 [alphacephei.com](https://alphacephei.com/vosk/models) 下载到数据目录，识别在本机做。上游默认的本地 FunASR 要下载约 1 GB 模型，最简化部署不采用。 |
| 语音合成 | 微软 Edge 免费语音 | 上游默认的 EdgeTTS，需要出网（`network.egress`）。 |
| 语音活动检测 | SileroVAD | 模型已打进上游镜像，不需要额外下载。 |
| 视觉分析（设备拍照） | 未接入 | 上游默认配置的视觉模型（ChatGLM）没有可用的 key，拍照识物会失败；需要时在上游配置里自行接入。 |

其余配置（角色提示词、音色、天气/新闻插件等）保持上游 `config.yaml` 默认。要改就编辑数据目录里的 `data/.config.yaml`（上游的覆盖配置，改完重启插件生效），键结构见上游 [config.yaml](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/main/xiaozhi-server/config.yaml)。

## 权限

- `models`：对话模型走模型网关。
- `network.egress`：EdgeTTS 语音合成、识别模型下载、上游自带的天气/新闻插件。
- `network.lan`：设备直连的两个端口——8000（WebSocket）和 8003（OTA 接口、视觉分析）。这两个端口不经云吞网关，上游默认不对设备做认证：局域网里的任何设备都能连上来聊天、消耗对话模型额度。装好后在插件设置里打开“局域网访问”端口才开；不要把这两个端口暴露到家庭网络以外。

## 设备怎么连

1. 装好后到插件设置里打开“局域网访问”。
2. 插件详情里显示设备的地址（OTA 接口），设备配网时在“高级选项”里粘贴它，保存并重启设备。
3. 设备访问 OTA 接口后会自动拿到 WebSocket 地址；上游固件 ≥ 1.6.1（见上游 [固件配置文档](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/firmware-setting.md)）。

## 开发

`scripts/` 来自[插件模板](https://github.com/geraldpeng6/wonton-plugin-template)：开发环境、检查、冒烟的用法见[开发指南](https://github.com/wontonapp/wonton-docs/blob/main/develop.md)。

## 图标与商标

图标取自上游 README 横幅里的小智机器人形象，底色用横幅的品牌蓝；来源、许可全文和商标说明见 [NOTICE](NOTICE)。
