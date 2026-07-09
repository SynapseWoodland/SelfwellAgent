# Selfwell · Caddy 反代说明 (V1.1 · 2026-07-09)

> ⚠️ **本地 dev-only**：本目录的所有配置**仅用于本地开发**（宿主机 uvicorn + Caddy + Tailscale Funnel）。
> **生产部署仍走 `docker compose` 或 K8s**，后端容器内端口 8000 直出，**不**走 Caddy。
> `backend/Dockerfile` / `docker-compose.yaml` / `backend/.env.example` 都保持 8000，请勿反向同步。

> 让 Tailscale Funnel 对外**只暴露 1 个端口 (8000)**，Caddy 在 127.0.0.1:8000
> 做 path 路由：`/api/*` → FastAPI（127.0.0.1:8001），`/minio/*` → MinIO（9000）。

## 1. 为什么需要它

Tailscale Funnel 在同一台机器上**只能有一个 ingress 进程**（`tailscaled` 自己
占着 443 做 TLS 终结，再原样 HTTP/1.1 转发到一个本地端口）。所以**不能**
用 `funnel 8000` 和 `funnel 9000` 各暴露一个。

Caddy 在中间做"路径分流"，对外只暴露 8000，MinIO 与 FastAPI 仍在本地独立端口。

## 2. 端口规划

| 进程 | 端口 | 监听地址 | 谁连它 |
|---|---|---|---|
| `tailscaled`（Funnel） | 443 / 80 | 0.0.0.0 | 公网用户 |
| **Caddy**（反代） | **8000** | **127.0.0.1** | tailscaled → 8000 |
| uvicorn（FastAPI） | 8001 | 127.0.0.1 | Caddy（/api/*） |
| MinIO | 9000 | 127.0.0.1 | Caddy（/minio/*） |

> **Caddy 占 8000 是因为 funnel 8000 on 的目标必须是本地 8000**。这导致
> uvicorn 必须让出 8000 退到 8001。如果你之后想换端口（funnel 8080 → Caddy
> 改 :8080），uvicorn 仍保持 8001 不动。

## 3. 公网访问映射

| 用途 | 公网 URL | 本地目标 |
|---|---|---|
| FastAPI 后端 | `https://husenlin.tail61999e.ts.net/api/v1/...` | `127.0.0.1:8001` (uvicorn) |
| MinIO S3 API | `https://husenlin.tail61999e.ts.net/minio/...` | `127.0.0.1:9000` (MinIO) |
| 健康检查 | `https://husenlin.tail61999e.ts.net/healthz` | 静态 `ok` |

> `config.ts:31` 的 `API_BASE_URL.dev = https://husenlin.tail61999e.ts.net/api/v1`
> **不需要改**，依旧可用。

## 4. 安装 Caddy

任选一种：

```powershell
# 方式 1: winget
winget install caddy

# 方式 2: choco
choco install caddy

# 方式 3: 单文件
# https://caddyserver.com/download  选 windows/amd64
# 解压后把 caddy.exe 丢到 PATH
```

## 5. 启动

### 4.1 一键脚本（推荐）

```powershell
# 前台 + 实时日志
.\infra\caddy\start.cmd

# 后台
.\infra\caddy\start.cmd background
```

脚本会自动：

1. 预检 8000 是否被占用（占用直接报错并提示怎么杀）
2. `tailscale funnel 9000 off`  —— 关闭之前的"直暴露 MinIO"那个坑
3. `tailscale funnel --bg 8000 on` —— 把 8000 暴露给 Caddy
4. 预检 uvicorn @ 8001（没起的话 warn 但不阻断，方便后启动）
5. `caddy start` / `caddy run`  —— 启动反代

### 4.2 手动启动

```powershell
# 1) 清掉残留 serve 规则(可选,但建议)
tailscale serve reset

# 2) 关闭旧 funnel
tailscale funnel 9000 off

# 3) 启动 uvicorn(8001 让给 Caddy 后,uvicorn 退到 8001)
uv run dev-backend
# 或: uvicorn backend.app.main:app --port 8001

# 4) 启动 Caddy(前台)
caddy run --config .\infra\caddy\Caddyfile

# 5) 另开终端:让 Tailscale 把公网 443 → 本机 8000(Caddy)
tailscale funnel --bg 8000 on
```

## 6. 验证

```powershell
# 1. 后端健康(应返 200 + JSON,经 Caddy 转到 8001)
curl -i http://127.0.0.1:8000/api/v1/healthz

# 2. MinIO 健康(应返 200)
curl -i http://127.0.0.1:8000/minio/health/live

# 3. 自检端点(应返 "ok")
curl -i http://127.0.0.1:8000/healthz

# 4. 直连后端(绕开 Caddy,应返 200)
curl -i http://127.0.0.1:8001/api/v1/healthz

# 5. 走公网(Tailnet 内有效;Funnel 公网需要设备在 admin 启用 Funnel)
curl -i https://husenlin.tail61999e.ts.net/api/v1/healthz
curl -i https://husenlin.tail61999e.ts.net/minio/health/live
```

## 7. 关键反代细节（出问题先看这里）

### 6.1 MinIO 的 SigV4 验签

MinIO 用 SigV4 签名校验所有非匿名请求，签名里包含 **Host 头**和 **path**。
两个雷区：

- **path**：Caddy 用 `uri strip_prefix /minio` 把公网路径前缀削掉，转给
  MinIO 时是 `/<bucket>/<key>`，与 SDK 算的签名路径一致 → **OK**。
- **Host**：必须保留**公网域名** (`{host}`)，不能传 `127.0.0.1:9000`，
  否则 MinIO 比对 `Host` 失败 → **403 SignatureDoesNotMatch**。

`Caddyfile` 里两处 `header_up Host {host}` 都是为此而写。

### 6.2 HTTP/2 与大文件上传

Caddy 默认走 HTTP/2，但 MinIO 的 S3 PUT/分片上传是流式的，HTTP/2 的流
多路复用反而会触发 MinIO 的 `Insufficient data` 错误（开发态常见）。所以
`transport http { versions h1 }` 强制 HTTP/1.1，PUT 大文件才稳。

### 6.3 CORS

**不在 Caddy 配 CORS**。CORS 已在后端 `app/main.py:133` 的 `CORSMiddleware`
按 ADR-0018 配好（dev 全开 `*`）。Caddy 多此一举反而会和后端回显的
`Access-Control-Allow-Origin` 冲突。

### 6.4 微信小程序"合法域名"

如果**只是**让小程序走后端 API，那 `https://husenlin.tail61999e.ts.net`
原本就要在微信公众平台加到：
- request 合法域名
- uploadFile 合法域名
- downloadFile 合法域名

**不需要额外加 MinIO**——业务上传走预签名 URL，**预签 URL 的 host 是
`127.0.0.1:9000`**（见 `app/services/...` 里 MinIO client 的 endpoint 配置），
不走 Caddy。

## 8. 常用运维命令

```powershell
# 看 Caddy 状态（后台模式）
caddy status

# 停 Caddy
caddy stop

# 重载配置（前台模式不支持；start 模式下要 stop 再 start）
caddy stop
caddy start --config .\infra\caddy\Caddyfile

# 看 Tailscale 状态
tailscale funnel status
tailscale serve status

# 关掉整个 funnel
tailscale funnel --bg off
```

## 9. 常见故障

| 症状 | 可能原因 | 排查 |
|---|---|---|
| 502 Bad Gateway | Caddy 找不到上游（uvicorn/MinIO 没起） | `curl 127.0.0.1:8000/api/v1/healthz` 单独验 |
| 403 SignatureDoesNotMatch | MinIO 收到的 Host 不是公网域名 | 确认 Caddyfile 里 `header_up Host {host}` 没被改 |
| `tailscaled: not allowed` | Tailscale admin 没开 Funnel | admin console → Access Controls → Funnel |
| 微信端报 `不在合法域名列表` | 域名没加到公众平台 | 登录 mp.weixin.qq.com → 开发 → 服务器域名 |
| Caddy 启动报 `bind: address already in use` | 8000 已被 uvicorn 或别的进程占 | 1) `netstat -ano \| findstr :8000` 找 PID；2) taskkill /F /PID \<pid\>；3) 确认 uvicorn 用 `--port 8001` |
| Caddy 起来了但 `/api/*` 一律 502 | uvicorn 没起或还在 8000 | 1) `curl 127.0.0.1:8001/api/v1/healthz` 直连验；2) `uv run dev-backend` 启 uvicorn |
| 浏览器开发者工具报 CORS 错 | Caddy 把公网 Host 丢了 | 确认 Caddyfile `header_up Host {host}` 没被改（这个字段用 `{host}` 字面，不是变量替换） |

## 10. 关闭 / 回滚

```powershell
# 停 Caddy
caddy stop

# 把 Tailscale 8000 funnel 关掉
tailscale funnel 8000 off
```

回滚到 2026-07-09 之前的"裸 uvicorn 8000 + tailscale funnel 8000" 状态需要
把 uvicorn 也改回 8000（仅当你**已经**把 pyproject 改成 8001 之后）：

```powershell
# 单次回滚(本进程用 8000,不影响 pyproject 配置)
uvicorn backend.app.main:app --port 8000
```

> **当前 1.1 版推荐保留 Caddy 8000 + uvicorn 8001**，不要回滚。
> 历史上曾用 `tailscale funnel --bg 9000` 把 MinIO 直暴露在公网；这本身
> 没问题，但和现在 8000 funnel 共用同一个域名会有 path 冲突（tailscaled
> 同一 hostname 同节点只能挂一个 ingress），所以开 Caddy 之前必须先
> `tailscale funnel 9000 off` 清理。
