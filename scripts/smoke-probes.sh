# shellcheck shell=bash
# scripts/smoke.sh 的一项一项探测，跟着插件走。没写的项会 FAIL 并给出写法，不会默认放行。
#
# 这个插件是设备后端，没有应用账号和应用内数据：
# - 网页入口是 8003 的 OTA 状态页（纯文本），web_assert 断言状态行；
# - 局域网开关（lan_webui）打开后，OTA 下发给设备的 WebSocket 地址必须是局域网地址，不是容器地址——
#   这是设备能不能连上的关键，探针读容器环境里的 WONTON_LAN_ADDRESSES 对比页面。
#
# 变量：SMOKE_WEB_URL 是网页入口（套件已去尾斜杠，但可能带路径）；
#       拼 API 路径用 SMOKE_WEB_ORIGIN（只有 scheme://host:port），别直接接在 SMOKE_WEB_URL 后面。

_container() { # <服务名>：本实例里这个服务的容器（按核心打的标签找，e2e 和 smoke 都成立）
  local inst="${SMOKE_INSTANCE:-}" args=(--filter "label=wonton.plugin=$SMOKE_PLUGIN_ID" --filter "label=wonton.service=$1")
  if [[ -z "$inst" && -n "${SMOKE_BASE:-}" ]]; then
    inst="${SMOKE_BASE#http://}"; inst="${SMOKE_BASE%%.*}"
    inst="${inst#wonton-}"
  fi
  [[ -z "$inst" ]] || args+=(--filter "label=wonton.instance=${inst//-/}")
  docker ps --format '{{.Names}}' "${args[@]}" | head -1
}

web_assert() {
  grep -q 'OTA接口运行正常' || { echo "OTA 状态页没有“运行正常”：$(head -c 200)"; return 1; }
  local lan page ws_url
  page="$(cat)"
  lan="$(docker exec "$(_container xiaozhi)" printenv WONTON_LAN_ADDRESSES 2>/dev/null | cut -d, -f1)"
  ws_url="$(grep -o 'ws://[^ ，。]*' <<<"$page" | head -1)"
  if [[ -z "$ws_url" ]]; then
    echo "OTA 状态页里没有 WebSocket 地址：$(head -c 200 <<<"$page")"
    return 1
  fi
  if [[ -n "$lan" ]]; then
    grep -qF "ws://$lan:8000" <<<"$ws_url" || {
      echo "下发地址 $ws_url 不是局域网地址 ws://$lan:8000"
      return 1
    }
  else
    echo "（局域网开关没开，下发的是容器地址：$ws_url）"
  fi
}

identity_check() { # 应用没有用户体系：设备服务无登录页，“当前用户”由云吞网关的会话保证（匿名 401 套件已验）
  echo "应用无用户体系（设备后端），套件的匿名 401 检查即身份边界"
}

# 应用不存用户数据：设备会话在内存里。数据目录里一次性服务写的配置和识别模型在重装时保留，
# 冒烟的 API 层数据钩子覆盖不到，在开发环境用 reinstall 后检查 .config.yaml 和模型目录验证。
DATA_NA=1
SMOKE_NOTE="设备后端无用户数据；配置和识别模型的保留在开发环境手工验证"
