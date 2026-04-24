# RV-Insights: 安全与零信任架构深度设计

**版本**: v1.0  
**日期**: 2026-04-21  
**目标**: 为 RV-Insights 平台构建纵深防御的安全体系，覆盖零信任网络、密钥生命周期、沙箱逃逸防护、供应链安全、代码审计自动化及数据隐私合规六大维度。本文档作为 `rv-insights-design.md` 第 7 章的强化替代方案，可直接合并至主方案。

---

## 目录

1. [零信任网络架构](#1-零信任网络架构)
2. [密钥与凭证生命周期管理](#2-密钥与凭证生命周期管理)
3. [沙箱逃逸多层防护](#3-沙箱逃逸多层防护)
4. [供应链攻击防护](#4-供应链攻击防护)
5. [代码安全审计自动化](#5-代码安全审计自动化)
6. [数据隐私与合规](#6-数据隐私与合规)
7. [安全运营与应急响应](#7-安全运营与应急响应)
8. [附录](#8-附录)

---

## 1. 零信任网络架构

> 核心原则：永不信任，始终验证（Never Trust, Always Verify）。所有服务间通信、API 访问、WebSocket 连接均需经过身份验证、授权与加密。

### 1.1 架构概览

```mermaid
graph TB
    subgraph "边缘接入层 (Edge Access)"
        CDN["Cloudflare / AWS CloudFront<br/>DDoS防护 + WAF"]
        GW["API Gateway (Envoy / Kong)<br/>JWT验证 + 速率限制 + 请求签名"]
    end

    subgraph "控制平面 (Control Plane)"
        IDP["Identity Provider (Keycloak / Dex)<br/>OIDC + MFA"]
        VAULT["HashiCorp Vault<br/>动态凭证 + mTLS证书签发"]
        POLICY["OPA / Istio AuthorizationPolicy<br/>细粒度授权"]
    end

    subgraph "服务网格 (Service Mesh: Istio / Linkerd)"
        direction TB
        ING["Ingress Gateway<br/>TLS终止 + 路由"]
        SVC1["UI Service (Next.js)"]
        SVC2["API Service (FastAPI)"]
        SVC3["LangGraph Engine"]
        SVC4["MCP-Server Pool"]
        SVC5["Agent Worker Pool"]
    end

    subgraph "数据平面隔离 (Data Plane Isolation)"
        DB[(PostgreSQL<br/>TLS + 证书认证)]
        RS[(Redis<br/>TLS + AUTH)]
        S3[(MinIO / S3<br/>服务端加密)]
    end

    User["用户/管理员"] -->|HTTPS| CDN
    CDN -->|HTTPS| GW
    GW -->|mTLS| ING
    ING -->|mTLS + JWT| SVC1
    ING -->|mTLS + JWT| SVC2
    SVC2 -->|mTLS + SPIFFE| SVC3
    SVC3 -->|mTLS + SPIFFE| SVC4
    SVC3 -->|mTLS + SPIFFE| SVC5
    SVC4 -->|mTLS| DB
    SVC4 -->|mTLS| RS
    SVC4 -->|HTTPS| S3

    IDP -->|OIDC Discovery| GW
    VAULT -->|动态凭证| SVC2
    VAULT -->|动态凭证| SVC3
    POLICY -->|授权决策| ING
```

### 1.2 服务间通信 mTLS

所有集群内部通信强制启用双向 TLS（mTLS），由服务网格（Istio 或 Linkerd）自动注入 Sidecar 代理管理证书生命周期。

**Istio PeerAuthentication 配置示例：**

```yaml
# 全局强制 mTLS
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: rv-insights
spec:
  mtls:
    mode: STRICT
---
# 按服务细粒度策略
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: mcp-server
  namespace: rv-insights
spec:
  selector:
    matchLabels:
      app: mcp-server
  mtls:
    mode: STRICT
  portLevelMtls:
    8080:
      mode: STRICT
```

**Linkerd 自动 mTLS（简化配置）：**

```bash
# 安装 Linkerd 并注入命名空间
linkerd install --crds | kubectl apply -f -
linkerd install | kubectl apply -f -
kubectl annotate namespace rv-insights linkerd.io/inject=enabled
kubectl rollout restart deployment -n rv-insights
```

**证书管理（cert-manager + Vault PKI）：**

```yaml
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: vault-issuer
  namespace: rv-insights
spec:
  vault:
    server: https://vault.rv-insights.svc:8200
    path: pki/sign/rv-insights-internal
    auth:
      kubernetes:
        role: rv-insights-cert-manager
        mountPath: /v1/auth/kubernetes
        secretRef:
          name: vault-cert-manager-token
          key: token
```

### 1.3 API 网关认证授权

API 网关作为所有外部流量的唯一入口，负责身份验证、速率限制、请求签名验证与审计日志记录。

**Envoy Gateway 安全配置：**

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: rv-insights-gateway
  namespace: rv-insights
spec:
  gatewayClassName: envoy-gateway
  listeners:
    - name: https
      protocol: HTTPS
      port: 443
      tls:
        mode: Terminate
        certificateRefs:
          - name: rv-insights-tls-cert
      allowedRoutes:
        namespaces:
          from: Same
---
apiVersion: gateway.envoyproxy.io/v1alpha1
kind: SecurityPolicy
metadata:
  name: api-auth-policy
  namespace: rv-insights
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: api-routes
  jwt:
    providers:
      - name: keycloak
        issuer: "https://auth.rv-insights.io/realms/rv-insights"
        remoteJWKS:
          uri: "https://auth.rv-insights.io/realms/rv-insights/protocol/openid-connect/certs"
        claimToHeaders:
          - header: x-user-id
            claim: sub
          - header: x-user-role
            claim: roles
  oidc:
    provider:
      issuer: "https://auth.rv-insights.io/realms/rv-insights"
    clientID: rv-insights-api
    clientSecret:
      name: oidc-client-secret
  rateLimit:
    type: Global
    global:
      rules:
        - limit:
            requests: 100
            unit: Minute
          headers:
            - name: x-user-id
              value: "*"
        - limit:
            requests: 10
            unit: Minute
          headers:
            - name: :path
              value: "/api/v1/trade/*"
```

**请求签名验证（HMAC-SHA256，用于 Webhook 与内部服务回调）：**

```python
# FastAPI 中间件示例
import hmac
import hashlib
import time
from fastapi import Request, HTTPException

SECRET_KEY = os.environ["WEBHOOK_SECRET"]  # 从 Vault 动态获取

async def verify_request_signature(request: Request):
    signature = request.headers.get("X-RV-Signature")
    timestamp = request.headers.get("X-RV-Timestamp")
    
    if not signature or not timestamp:
        raise HTTPException(status_code=401, detail="Missing signature headers")
    
    # 防重放攻击：时间戳需在 5 分钟内
    if abs(time.time() - int(timestamp)) > 300:
        raise HTTPException(status_code=401, detail="Request timestamp expired")
    
    body = await request.body()
    expected = hmac.new(
        SECRET_KEY.encode(),
        f"{timestamp}.{body.decode()}".encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=403, detail="Invalid signature")
```

### 1.4 WebSocket 连接安全加固

WebSocket 用于 Web 控制台与 LangGraph 引擎的实时状态推送（SSE 降级），必须实施以下加固措施：

| 安全措施 | 实现方式 | 目的 |
|----------|----------|------|
| TLS 强制 | `wss://` 协议，禁止明文 `ws://` | 防止中间人窃听 |
| JWT 令牌绑定 | 连接建立时通过 `sec-websocket-protocol` 传递短期访问令牌 | 防止未授权连接 |
| 令牌刷新机制 | 使用独立的短期 Token（5 分钟有效期），通过 HTTP POST 刷新 | 减少长期令牌泄露风险 |
| 连接数限制 | 每用户最多 3 个并发 WebSocket 连接 | 防止资源耗尽攻击 |
| 心跳与超时 | 30 秒 Ping/Pong，90 秒无响应强制断开 | 检测僵尸连接 |
| 消息大小限制 | 单帧最大 1MB，消息总大小最大 10MB | 防止内存耗尽攻击 |
|  Origin 校验 | 严格校验 `Origin` 头为允许的域名列表 | 防止 CSWSH 攻击 |

**WebSocket 连接验证流程：**

```mermaid
sequenceDiagram
    actor User
    participant UI as Web Console
    participant GW as API Gateway
    participant Auth as Keycloak
    participant LG as LangGraph Engine

    User->>UI: 登录成功
    UI->>Auth: 请求 WebSocket Token (scope: websocket)
    Auth-->>UI: 返回短期 JWT (exp: 5min)
    UI->>GW: wss://api.rv-insights.io/ws/session/{id}<br/>Headers: Authorization: Bearer <ws-token>
    GW->>GW: 验证 JWT 签名、过期时间、scope
    GW->>GW: 校验 Origin 头
    GW->>LG: 代理 WebSocket 连接
    LG->>LG: 验证 session_id 归属该用户
    LG-->>UI: 连接建立，开始推送状态
    
    loop 每 30 秒
        GW->>UI: Ping
        UI->>GW: Pong
    end
    
    UI->>GW: POST /ws/refresh (携带旧 Token)
    GW->>Auth: 验证并签发新 Token
    GW-->>UI: 新短期 JWT
```

---

## 2. 密钥与凭证生命周期管理

> 核心原则：零硬编码、动态签发、最小权限、自动轮换、全程审计。

### 2.1 HashiCorp Vault 集成架构

```mermaid
graph TB
    subgraph "HashiCorp Vault 集群"
        VAULT_LEADER["Vault Leader<br/>Raft 存储后端"]
        VAULT_STANDBY1["Vault Standby 1"]
        VAULT_STANDBY2["Vault Standby 2"]
        VAULT_LEADER -->|Raft| VAULT_STANDBY1
        VAULT_LEADER -->|Raft| VAULT_STANDBY2
    end

    subgraph "Secret Engines"
        PKI["PKI Engine<br/>服务间 mTLS 证书"]
        KV2["KV v2 Engine<br/>静态配置加密存储"]
        AWS["AWS Engine<br/>临时 IAM 凭证"]
        DB["Database Engine<br/>动态数据库凭证"]
        GIT["GitHub/GitLab Engine<br/>动态 Git Token"]
        LLM["LLM API Engine<br/>动态 API Key 代理"]
    end

    subgraph "认证方法"
        K8S_AUTH["Kubernetes Auth<br/>ServiceAccount JWT"]
        APP_ROLE["AppRole Auth<br/>CI/CD 流水线"]
        OIDC_AUTH["OIDC Auth<br/>管理员紧急访问"]
    end

    VAULT_LEADER --> PKI
    VAULT_LEADER --> KV2
    VAULT_LEADER --> AWS
    VAULT_LEADER --> DB
    VAULT_LEADER --> GIT
    VAULT_LEADER --> LLM
    VAULT_LEADER --> K8S_AUTH
    VAULT_LEADER --> APP_ROLE
    VAULT_LEADER --> OIDC_AUTH

    SVC["Platform Services"] -->|K8S Auth| K8S_AUTH
    CI["CI/CD Pipeline"] -->|AppRole| APP_ROLE
    ADMIN["On-call Admin"] -->|OIDC + MFA| OIDC_AUTH
```

### 2.2 动态凭证签发与自动轮换

#### 2.2.1 LLM API 密钥动态代理

LLM API 密钥（OpenAI、Anthropic、Google 等）绝不直接分发给 Agent，而是通过 Vault 的自定义 Secret Engine 或中间代理进行管控。

```hcl
# Vault 策略：Agent 仅能通过代理访问 LLM API
path "llm-proxy/creds/anthropic" {
  capabilities = ["read"]
  allowed_parameters = {
    "session_id" = ["*"]
    "agent_role" = ["explorer", "developer", "reviewer"]
  }
}

# 拒绝直接访问底层 API Key
path "secret/data/llm/anthropic-api-key" {
  capabilities = ["deny"]
}
```

**LLM 代理中间件（Python 示例）：**

```python
from fastapi import FastAPI, Depends, HTTPException
import httpx
import vault_client  # hvac 库封装

app = FastAPI()

async def get_llm_proxy_token(
    session_id: str,
    agent_role: str,
    vault: vault_client.VaultClient = Depends(get_vault_client)
):
    """从 Vault 获取短期 LLM 代理令牌，绑定 session_id 和 agent_role"""
    token = vault.read(
        f"llm-proxy/creds/anthropic",
        params={"session_id": session_id, "agent_role": agent_role}
    )
    if not token:
        raise HTTPException(status_code=403, detail="LLM access denied for this role")
    return token["data"]["proxy_token"]

@app.post("/v1/proxy/anthropic/messages")
async def proxy_anthropic(
    request: Request,
    token: dict = Depends(get_llm_proxy_token)
):
    """
    代理所有 LLM 请求，实施以下控制：
    1. 速率限制：按 session_id 限制 RPM/TPM
    2. 内容审计：记录请求摘要（脱敏后）到审计日志
    3. 响应拦截：检测并阻断敏感数据泄露
    4. 成本配额：超出预算自动拒绝
    """
    body = await request.json()
    
    # 审计日志（脱敏）
    audit_log.info({
        "event": "llm_request",
        "session_id": token["session_id"],
        "agent_role": token["agent_role"],
        "model": body.get("model"),
        "token_count_estimate": len(str(body)),
        "timestamp": datetime.utcnow().isoformat()
    })
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Authorization": f"Bearer {token['proxy_key']}"},
            json=body,
            timeout=60.0
        )
    
    # 响应审计：检测是否包含疑似密钥的模式
    response_text = response.text
    if contains_credential_pattern(response_text):
        alert_security_team(session_id=token["session_id"], reason="potential_credential_leak")
        raise HTTPException(status_code=500, detail="Response blocked by security policy")
    
    return response.json()
```

#### 2.2.2 Git 凭据动态签发

不同 Agent 使用不同 Scope 的 Git Token，遵循最小权限原则。

```hcl
# Vault GitHub Secret Engine 配置
vault write github/config \
    app_id="${GITHUB_APP_ID}" \
    prv_key="@github-app-private-key.pem" \
    base_url="https://api.github.com"

# 为不同角色创建不同权限的 Token 角色
vault write github/roles/explorer \
    organization="riscv-collab" \
    repository_permissions="read" \
    contents="read" \
    issues="read" \
    ttl="1h" \
    max_ttl="4h"

vault write github/roles/developer \
    organization="riscv-collab" \
    repository_permissions="write" \
    contents="write" \
    pull_requests="write" \
    ttl="2h" \
    max_ttl="8h"

vault write github/roles/reviewer \
    organization="riscv-collab" \
    repository_permissions="read" \
    contents="read" \
    pull_requests="read" \
    ttl="1h" \
    max_ttl="4h"
```

**Python 客户端使用示例：**

```python
import hvac

vault = hvac.Client(url="https://vault.rv-insights.io:8200")
vault.auth.kubernetes.login(
    role="rv-insights-agent",
    jwt=open("/var/run/secrets/kubernetes.io/serviceaccount/token").read()
)

# 开发 Agent 获取短期 Git Token
git_creds = vault.secrets.github.generate_credentials(
    name="developer",
    mount_point="github"
)
access_token = git_creds["data"]["token"]

# Token 自动在 2 小时后过期，无需手动清理
```

#### 2.2.3 数据库密码动态签发

```hcl
# Vault Database Secret Engine 配置
vault write database/config/postgresql \
    plugin_name="postgresql-database-plugin" \
    allowed_roles="langgraph-reader,langgraph-writer,audit-writer" \
    connection_url="postgresql://{{username}}:{{password}}@pg.rv-insights.svc:5432/rvinsights" \
    username="vaultadmin" \
    password="${VAULT_DB_ADMIN_PASSWORD}"

# 为 LangGraph 引擎创建只读角色
vault write database/roles/langgraph-reader \
    db_name="postgresql" \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
                         GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
    default_ttl="1h" \
    max_ttl="24h"

# 为审计服务创建只写角色
vault write database/roles/audit-writer \
    db_name="postgresql" \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
                         GRANT INSERT ON audit_logs TO \"{{name}}\";" \
    default_ttl="1h" \
    max_ttl="24h"
```

### 2.3 禁止硬编码凭据的检测机制

#### 2.3.1 Pre-commit Hook 配置

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: ".*\\.test\\.ts$|.*\\.spec\\.ts$|.*\\.md$"

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.2
    hooks:
      - id: gitleaks
        args: ['protect', '--staged', '--verbose']

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: check-added-large-files
      - id: check-case-conflict
      - id: check-merge-conflict
```

**detect-secrets 基线文件初始化：**

```bash
detect-secrets scan --all-files > .secrets.baseline
detect-secrets audit .secrets.baseline  # 人工审计确认每个疑似项
git add .secrets.baseline
```

#### 2.3.2 CI 流水线扫描

```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on: [push, pull_request]

jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # 完整历史扫描

      - name: TruffleHog OSS
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: main
          head: HEAD
          extra_args: --debug --only-verified

      - name: GitLeaks Scan
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Trivy FS Scan (Secrets)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scanners: 'secret'
          exit-code: '1'
          severity: 'CRITICAL,HIGH'

  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Trivy Dependency Scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scanners: 'vuln,misconfig'
          exit-code: '1'
          severity: 'CRITICAL,HIGH'

      - name: npm audit (for UI)
        working-directory: ./ui
        run: npm audit --audit-level=high

      - name: pip-audit (for Python services)
        run: |
          pip install pip-audit
          pip-audit --requirement=requirements.txt --desc --format=json
```

#### 2.3.3 硬编码凭据检测规则（Semgrep）

```yaml
# .semgrep/rules/hardcoded-secrets.yml
rules:
  - id: hardcoded-api-key
    pattern-regex: '(api[_-]?key|apikey)\s*[:=]\s*["\']\w{16,}["\']'
    languages: [python, javascript, typescript, go, java]
    message: "检测到疑似硬编码 API Key"
    severity: ERROR
    metadata:
      category: security
      cwe: "CWE-798"

  - id: hardcoded-password
    pattern-regex: '(password|passwd|pwd)\s*[:=]\s*["\'][^"\']{8,}["\']'
    languages: [python, javascript, typescript, go, java]
    message: "检测到疑似硬编码密码"
    severity: ERROR
    metadata:
      category: security
      cwe: "CWE-798"

  - id: private-key-in-source
    pattern-regex: '-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'
    languages: [python, javascript, typescript, go, java, yaml, json]
    message: "检测到私钥嵌入源代码"
    severity: ERROR
    metadata:
      category: security
      cwe: "CWE-798"
```

### 2.4 凭证最小权限原则矩阵

| 服务/Agent | Git Token Scope | 数据库权限 | LLM API 配额 | 网络访问 |
|------------|-----------------|------------|--------------|----------|
| Explorer Agent | `repo:read`, `issues:read` | 无 | 100 RPM / 10K TPM | GitHub API, 邮件列表 |
| Planner Agent | `repo:read` | 无 | 50 RPM / 5K TPM | RAG 知识库 |
| Developer Agent | `repo:write`, `pull_requests:write` | 无 | 200 RPM / 20K TPM | GitHub API, 包管理器 |
| Reviewer Agent | `repo:read`, `pull_requests:read` | 无 | 150 RPM / 15K TPM | 无出站 |
| Tester Agent | `repo:read` | 无 | 50 RPM / 5K TPM | 无出站（离线构建） |
| LangGraph Engine | 无 | `checkpoints: RW` | 无 | 内部服务 |
| MCP-Server | 无 | 无 | 无 | 受限白名单 |
| Audit Service | 无 | `audit_logs: W` | 无 | WORM 存储 |
| Human Admin | `repo:admin` (紧急) | `superuser` (紧急) | 无限制 | 全访问 |

---

## 3. 沙箱逃逸多层防护

> 核心原则：纵深防御（Defense in Depth）。即使单层防护被突破，后续层仍可阻止或检测逃逸行为。

### 3.1 四层防护架构

```mermaid
graph TB
    subgraph "第四层：虚拟化隔离"
        FC["Firecracker MicroVM<br/>KVM 硬件虚拟化<br/>独立内核 + 内存隔离"]
    end

    subgraph "第三层：强制访问控制"
        AA["AppArmor / SELinux<br/>强制访问控制策略<br/>文件/网络/能力限制"]
    end

    subgraph "第二层：系统调用过滤"
        SC["seccomp-bpf<br/>系统调用白名单<br/>默认拒绝策略"]
    end

    subgraph "第一层：资源与网络隔离"
        CG["cgroups v2<br/>CPU/内存/IO/网络配额"]
        NS["Linux Namespaces<br/>PID/Network/Mount/UTS/IPC"]
        NET["网络隔离<br/>无出站 / IP 白名单<br/>eBPF 流量过滤"]
    end

    AGENT["Agent 代码执行请求"] -->|RPC| MCP["MCP-Server"]
    MCP -->|编排| FC
    FC -->|启动| VM["MicroVM 实例"]
    VM -->|加载| CG
    VM -->|加载| NS
    VM -->|加载| NET
    NS -->|加载| AA
    AA -->|加载| SC
    SC -->|执行| USER["Agent 进程<br/>最小权限运行"]
```

### 3.2 第一层：seccomp-bpf 系统调用过滤

采用默认拒绝（Default Deny）策略，仅允许执行白名单中的系统调用。所有其他调用触发 `SIGSYS` 信号并记录审计日志。

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "defaultErrnoRet": 1,
  "archMap": [
    { "architecture": "SCMP_ARCH_X86_64", "subArchitectures": ["SCMP_ARCH_X86"] },
    { "architecture": "SCMP_ARCH_AARCH64", "subArchitectures": ["SCMP_ARCH_ARM"] }
  ],
  "syscalls": [
    {
      "names": [
        "accept", "accept4", "access", "adjtimex", "alarm", "bind", "brk",
        "capget", "capset", "chdir", "chmod", "chown", "chown32", "clock_adjtime",
        "clock_getres", "clock_gettime", "clock_nanosleep", "clone", "clone3",
        "close", "close_range", "connect", "copy_file_range", "creat", "dup",
        "dup2", "dup3", "epoll_create", "epoll_create1", "epoll_ctl", "epoll_ctl_old",
        "epoll_pwait", "epoll_pwait2", "epoll_wait", "epoll_wait_old", "eventfd",
        "eventfd2", "execve", "execveat", "exit", "exit_group", "faccessat",
        "faccessat2", "fadvise64", "fadvise64_64", "fallocate", "fanotify_mark",
        "fchdir", "fchmod", "fchmodat", "fchown", "fchown32", "fchownat",
        "fcntl", "fcntl64", "fdatasync", "fgetxattr", "flistxattr", "flock",
        "fork", "fremovexattr", "fsetxattr", "fstat", "fstat64", "fstatat64",
        "fstatfs", "fstatfs64", "fsync", "ftruncate", "ftruncate64", "futex",
        "futex_time64", "getcpu", "getcwd", "getdents", "getdents64", "getegid",
        "getegid32", "geteuid", "geteuid32", "getgid", "getgid32", "getgroups",
        "getgroups32", "getitimer", "getpeername", "getpgid", "getpgrp", "getpid",
        "getppid", "getpriority", "getrandom", "getresgid", "getresgid32",
        "getresuid", "getresuid32", "getrlimit", "get_robust_list", "getrusage",
        "getsid", "getsockname", "getsockopt", "get_thread_area", "gettid",
        "gettimeofday", "getuid", "getuid32", "getxattr", "inotify_add_watch",
        "inotify_init", "inotify_init1", "inotify_rm_watch", "io_cancel",
        "ioctl", "io_destroy", "io_getevents", "io_pgetevents", "io_pgetevents_time64",
        "ioprio_get", "ioprio_set", "io_setup", "io_submit", "io_uring_enter",
        "io_uring_register", "io_uring_setup", "ipc", "kill", "lchown", "lchown32",
        "lgetxattr", "link", "linkat", "listen", "listxattr", "llistxattr",
        "lremovexattr", "lseek", "lsetxattr", "lstat", "lstat64", "madvise",
        "membarrier", "memfd_create", "mincore", "mkdir", "mkdirat", "mknod",
        "mknodat", "mlock", "mlock2", "mlockall", "mmap", "mmap2", "mprotect",
        "mq_getsetattr", "mq_notify", "mq_open", "mq_timedreceive", "mq_timedreceive_time64",
        "mq_timedsend", "mq_timedsend_time64", "mq_unlink", "mremap", "msgctl",
        "msgget", "msgrcv", "msgsnd", "msync", "munlock", "munlockall", "munmap",
        "nanosleep", "newfstatat", "open", "openat", "openat2", "pause", "pidfd_open",
        "pidfd_send_signal", "pipe", "pipe2", "pivot_root", "poll", "ppoll",
        "ppoll_time64", "prctl", "pread64", "preadv", "preadv2", "prlimit64",
        "pselect6", "pselect6_time64", "pwrite64", "pwritev", "pwritev2",
        "read", "readahead", "readdir", "readlink", "readlinkat", "readv",
        "recv", "recvfrom", "recvmmsg", "recvmmsg_time64", "recvmsg", "remap_file_pages",
        "removexattr", "rename", "renameat", "renameat2", "restart_syscall",
        "rmdir", "rseq", "rt_sigaction", "rt_sigpending", "rt_sigprocmask",
        "rt_sigqueueinfo", "rt_sigreturn", "rt_sigsuspend", "rt_sigtimedwait",
        "rt_sigtimedwait_time64", "rt_tgsigqueueinfo", "sched_getaffinity",
        "sched_getattr", "sched_getparam", "sched_get_priority_max", "sched_get_priority_min",
        "sched_getscheduler", "sched_rr_get_interval", "sched_rr_get_interval_time64",
        "sched_setaffinity", "sched_setattr", "sched_setparam", "sched_setscheduler",
        "sched_yield", "seccomp", "select", "semctl", "semget", "semop",
        "semtimedop", "semtimedop_time64", "send", "sendfile", "sendfile64",
        "sendmmsg", "sendmsg", "sendto", "setfsgid", "setfsgid32", "setfsuid",
        "setfsuid32", "setgid", "setgid32", "setgroups", "setgroups32", "setitimer",
        "setpgid", "setpriority", "setregid", "setregid32", "setresgid",
        "setresgid32", "setresuid", "setresuid32", "setreuid", "setreuid32",
        "setrlimit", "set_robust_list", "setsid", "setsockopt", "set_thread_area",
        "set_tid_address", "setuid", "setuid32", "setxattr", "shmat", "shmctl",
        "shmdt", "shmget", "shutdown", "sigaltstack", "signalfd", "signalfd4",
        "sigpending", "sigprocmask", "sigreturn", "socket", "socketcall",
        "socketpair", "splice", "stat", "stat64", "statfs", "statfs64", "statx",
        "symlink", "symlinkat", "sync", "sync_file_range", "syncfs", "sysinfo",
        "tee", "tgkill", "time", "timer_create", "timer_delete", "timer_getoverrun",
        "timer_gettime", "timer_gettime64", "timer_settime", "timer_settime64",
        "timerfd_create", "timerfd_gettime", "timerfd_gettime64", "timerfd_settime",
        "timerfd_settime64", "times", "tkill", "truncate", "truncate64", "ugetrlimit",
        "umask", "uname", "unlink", "unlinkat", "utime", "utimensat", "utimensat_time64",
        "utimes", "vfork", "wait4", "waitid", "waitpid", "write", "writev"
      ],
      "action": "SCMP_ACT_ALLOW"
    },
    {
      "names": ["personality"],
      "action": "SCMP_ACT_ALLOW",
      "args": [
        { "index": 0, "value": 0, "op": "SCMP_CMP_EQ" },
        { "index": 0, "value": 8, "op": "SCMP_CMP_EQ" },
        { "index": 0, "value": 131072, "op": "SCMP_CMP_EQ" },
        { "index": 0, "value": 131073, "op": "SCMP_CMP_EQ" },
        { "index": 0, "value": 4294967295, "op": "SCMP_CMP_EQ" }
      ]
    }
  ]
}
```

**关键禁止的系统调用：**

| 系统调用 | 禁止原因 |
|----------|----------|
| `mount`, `umount2` | 防止挂载恶意文件系统 |
| `pivot_root` | 防止根文件系统切换 |
| `open_by_handle_at` | CVE-2014-9356 容器逃逸 |
| `ptrace` | 防止进程注入与调试 |
| `process_vm_writev` | 防止跨进程内存写入 |
| `kexec_load`, `kexec_file_load` | 防止加载恶意内核 |
| `init_module`, `finit_module` | 防止加载内核模块 |
| `bpf` | 防止加载恶意 eBPF 程序 |
| `perf_event_open` | 防止侧信道攻击 |
| `userfaultfd` | CVE-2021-22543 漏洞利用 |
| `clone` (带 `CLONE_NEWUSER`) | 防止用户命名空间提权 |

### 3.3 第二层：AppArmor/SELinux 强制访问控制

**AppArmor Profile（MCP-Server 沙箱进程）：**

```bash
#include <tunables/global>

profile rv-insights-sandbox flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>
  #include <abstractions/python>
  #include <abstractions/nameservice>

  # 严格限制文件系统访问
  /srv/sandbox/{,**} rwk,
  /tmp/sandbox-*/{,**} rw,
  /var/log/rv-insights/sandbox/{,**} w,

  # 禁止访问敏感系统路径
  deny /etc/shadow r,
  deny /etc/passwd r,
  deny /proc/*/environ r,
  deny /proc/*/mem r,
  deny /proc/*/maps r,
  deny /sys/kernel/{,**} r,
  deny /dev/{mem,kmem,port} rw,
  deny /proc/sys/{,**} w,

  # 网络限制（配合网络命名空间）
  deny network raw,
  deny network packet,
  deny network dgram,

  # 允许访问构建工具链（只读）
  /usr/bin/gcc ix,
  /usr/bin/clang ix,
  /usr/bin/make ix,
  /usr/bin/git ix,
  /usr/lib/gcc/{,**} r,
  /usr/lib/llvm/{,**} r,

  # 限制能力
  deny capability mknod,
  deny capability sys_admin,
  deny capability sys_ptrace,
  deny capability sys_module,
  deny capability dac_read_search,
  deny capability dac_override,

  # 审计所有拒绝操作
  audit deny /** w,
}
```

### 3.4 第三层：Firecracker MicroVM 虚拟化隔离

Firecracker 提供轻量级虚拟化（MicroVM），每个 Agent 会话在独立的 VM 中运行，具备独立的内核和内存空间。

**Firecracker VM 配置：**

```json
{
  "boot-source": {
    "kernel_image_path": "/var/lib/firecracker/vmlinux-5.10-rv-insights",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off nomodules random.trust_cpu=on"
  },
  "drives": [
    {
      "drive_id": "rootfs",
      "path_on_host": "/var/lib/firecracker/rootfs-rv-insights.squashfs",
      "is_root_device": true,
      "is_read_only": true
    },
    {
      "drive_id": "workspace",
      "path_on_host": "/var/lib/firecracker/workspaces/{session_id}.ext4",
      "is_root_device": false,
      "is_read_only": false
    }
  ],
  "machine-config": {
    "vcpu_count": 4,
    "mem_size_mib": 8192,
    "smt": false,
    "track_dirty_pages": true
  },
  "network-interfaces": [
    {
      "iface_id": "eth0",
      "host_dev_name": "tap-{session_id}",
      "guest_mac": "AA:FC:00:00:00:{session_id_suffix}",
      "rx_rate_limiter": {
        "bandwidth": { "size": 100000000, "refill_time": 100 }
      },
      "tx_rate_limiter": {
        "bandwidth": { "size": 100000000, "refill_time": 100 }
      }
    }
  ],
  "vsock": {
    "guest_cid": {auto_generated_cid},
    "uds_path": "/var/run/firecracker/{session_id}.sock"
  },
  "balloon": {
    "amount_mib": 512,
    "deflate_on_oom": true,
    "stats_polling_interval_s": 5
  },
  "mmds-config": {
    "version": "V2",
    "ipv4_address": "169.254.169.250",
    "network_interfaces": ["eth0"]
  }
}
```

**关键安全特性：**

- **无 PCI 设备**：`pci=off` 减少攻击面
- **禁止内核模块加载**：`nomodules` 防止运行时加载恶意模块
- **只读根文件系统**：根文件系统以 SquashFS 只读挂载
- **独立工作卷**：每个会话拥有独立的可写 Ext4 卷，会话结束后销毁
- **内存气球**：动态回收未使用内存，防止内存耗尽攻击
- **脏页追踪**：`track_dirty_pages` 支持快照与迁移安全

### 3.5 第四层：网络隔离

**默认拒绝所有出站连接，仅允许特定白名单。**

```bash
# 使用 iptables + ipset 实现出站白名单
ipset create allowed_ipv4 hash:net
ipset add allowed_ipv4 140.82.112.0/20    # GitHub API
ipset add allowed_ipv4 185.199.108.0/22   # GitHub Pages
ipset add allowed_ipv4 13.107.42.0/24     # Azure DevOps (if needed)

# 应用到 Firecracker tap 接口
iptables -A FORWARD -i tap-+ -m set ! --match-set allowed_ipv4 dst -j DROP
iptables -A FORWARD -i tap-+ -p tcp --dport 443 -m set --match-set allowed_ipv4 dst -j ACCEPT
iptables -A FORWARD -i tap-+ -p tcp --dport 80 -m set --match-set allowed_ipv4 dst -j ACCEPT
iptables -A FORWARD -i tap-+ -j LOG --log-prefix "RV-SANDBOX-BLOCKED: "
iptables -A FORWARD -i tap-+ -j DROP

# 禁止入站连接（仅允许已建立连接）
iptables -A FORWARD -i tap-+ -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A FORWARD -i tap-+ -m state --state NEW -j DROP
```

**eBPF 增强流量监控（Cilium 或自定义）：**

```c
// 使用 eBPF 监控沙箱中的异常网络行为
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>

SEC("xdp")
int sandbox_net_monitor(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;
    struct ethhdr *eth = data;
    
    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;
    
    if (eth->h_proto != __constant_htons(ETH_P_IP))
        return XDP_PASS;
    
    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_PASS;
    
    // 检测异常：非白名单目的 IP
    __u32 dst_ip = ip->daddr;
    if (!is_ip_whitelisted(dst_ip)) {
        // 记录到 perf buffer，用户态告警
        struct event evt = {};
        evt.src_ip = ip->saddr;
        evt.dst_ip = dst_ip;
        evt.proto = ip->protocol;
        evt.timestamp = bpf_ktime_get_ns();
        bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &evt, sizeof(evt));
        
        return XDP_DROP;
    }
    
    // 检测异常：大量连接尝试（端口扫描行为）
    if (ip->protocol == IPPROTO_TCP) {
        struct tcphdr *tcp = (void *)ip + (ip->ihl * 4);
        if ((void *)(tcp + 1) <= data_end) {
            __u16 dst_port = __constant_ntohs(tcp->dest);
            update_conn_attempt_counter(dst_ip, dst_port);
            if (get_conn_attempt_rate(dst_ip) > 100) {  // 100 conn/min
                trigger_alert(ALERT_PORT_SCAN, dst_ip);
                return XDP_DROP;
            }
        }
    }
    
    return XDP_PASS;
}
```

### 3.6 逃逸检测与响应

**异常行为检测规则：**

| 检测维度 | 异常指标 | 响应动作 |
|----------|----------|----------|
| 系统调用 | 调用黑名单 syscall（如 `mount`, `ptrace`） | 立即终止 VM + 告警 |
| 系统调用 | syscall 频率突增 > 10x 基线 | 限速 + 人工审查 |
| 文件系统 | 访问 `/proc/self/mem`, `/etc/shadow` | 立即终止 VM + 告警 |
| 文件系统 | 尝试写入系统目录（`/usr`, `/bin`） | 阻断写入 + 告警 |
| 网络 | 连接非白名单 IP/域名 | 阻断连接 + 告警 |
| 网络 | 异常端口扫描行为 | 阻断出站 + 告警 |
| 进程 | 尝试 `fork bomb` 或创建大量进程 | 触发 OOM killer + 告警 |
| 进程 | 尝试执行非白名单二进制 | 阻断执行 + 告警 |
| 内核 | 检测到内核 panic / Oops | 自动重启 VM + 告警 |

**Falco 规则配置：**

```yaml
# falco/rules/rv-insights-sandbox.yaml
- rule: Sandbox Escape Attempt - Mount
  desc: Detect mount syscall in sandbox (potential container escape)
  condition: >
    spawned_process and
    container.name contains "rv-insights-sandbox" and
    (syscall.type = mount or syscall.type = umount2)
  output: >
    Sandbox escape attempt detected
    (user=%user.name command=%proc.cmdline container=%container.name)
  priority: CRITICAL

- rule: Sandbox Escape Attempt - Ptrace
  desc: Detect ptrace usage in sandbox
  condition: >
    spawned_process and
    container.name contains "rv-insights-sandbox" and
    (syscall.type = ptrace)
  output: >
    Ptrace detected in sandbox
    (user=%user.name command=%proc.cmdline container=%container.name)
  priority: CRITICAL

- rule: Sandbox Unauthorized Network Connection
  desc: Detect outbound connections to non-whitelisted IPs
  condition: >
    outbound and
    container.name contains "rv-insights-sandbox" and
    not (fd.ip = "140.82.112.0/20" or fd.ip = "185.199.108.0/22")
  output: >
    Unauthorized network connection from sandbox
    (connection=%fd.name container=%container.name)
  priority: HIGH

- rule: Sandbox Credential Access
  desc: Detect access to sensitive files
  condition: >
    open_read and
    container.name contains "rv-insights-sandbox" and
    (fd.name contains "/etc/shadow" or fd.name contains "/etc/passwd" or
     fd.name contains ".ssh/id_rsa" or fd.name contains ".aws/credentials")
  output: >
    Sensitive file access in sandbox
    (file=%fd.name user=%user.name container=%container.name)
  priority: HIGH
```

---

## 4. 供应链攻击防护

> 核心原则：信任但验证（Trust but Verify）。所有进入生产环境的依赖、镜像、构建产物必须经过校验与签名。

### 4.1 依赖锁定与强制校验

**Python (pip)：**

```bash
# 生成锁定文件
pip install pip-tools
pip-compile --generate-hashes requirements.in -o requirements.txt

# CI 强制校验
pip install --require-hashes -r requirements.txt
```

**Node.js (npm)：**

```bash
# package-lock.json 必须提交到版本控制
npm ci --ignore-scripts  # 禁用 postinstall 脚本，防止供应链攻击

# 使用 sigstore 校验
npm audit signatures
```

**Go：**

```bash
# go.sum 已内建校验，强制校验模式
GOSUMDB="sum.golang.org" go mod verify

# 私有模块使用企业级校验和数据库
GOSUMDB="sum.rv-insights.io" go mod verify
```

**Rust：**

```bash
# Cargo.lock 必须提交
cargo generate-lockfile
cargo audit  # 使用 cargo-audit 检查 CVE
```

**CI 强制校验脚本：**

```yaml
# .github/workflows/supply-chain.yml
name: Supply Chain Security

on: [push, pull_request]

jobs:
  verify-locks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Verify Python dependencies
        run: |
          pip install --require-hashes -r requirements.txt

      - name: Verify Node.js dependencies
        working-directory: ./ui
        run: |
          npm ci --ignore-scripts
          npm audit signatures

      - name: Verify Go dependencies
        working-directory: ./services
        run: |
          go mod verify

      - name: Run cargo audit
        working-directory: ./sandbox
        run: |
          cargo install cargo-audit
          cargo audit

      - name: Check for unauthorized dependency changes
        run: |
          # 确保 lock 文件与源码同时修改
          git diff --name-only HEAD^ HEAD | grep -E "(requirements\.txt|package-lock\.json|go\.sum|Cargo\.lock)" > /dev/null
          if [ $? -ne 0 ]; then
            echo "No lock file changes detected. If dependencies changed, lock files must be updated."
            exit 1
          fi
```

### 4.2 SBOM 生成与漏洞扫描

**生成 SBOM（使用 Syft）：**

```bash
# 容器镜像 SBOM
syft packages registry.rv-insights.io/mcp-server:latest -o spdx-json > sbom-mcp-server.spdx.json

# 文件系统 SBOM
syft dir:./services/api -o cyclonedx-json > sbom-api.cyclonedx.json

# 提交到依赖追踪系统
sbom-tool upload --project rv-insights --version $(git describe --tags) \
  --file sbom-mcp-server.spdx.json
```

**漏洞扫描（Trivy + Snyk）：**

```yaml
# .github/workflows/vulnerability-scan.yml
name: Vulnerability Scan

on:
  schedule:
    - cron: '0 6 * * *'  # 每日 6 AM
  push:
    branches: [main]

jobs:
  trivy-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build images
        run: docker compose -f docker-compose.build.yml build

      - name: Trivy image scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'rv-insights-mcp-server:latest'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

      - name: Upload to GitHub Security tab
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Trivy SBOM scan
        run: |
          trivy sbom sbom-mcp-server.spdx.json --severity HIGH,CRITICAL

  snyk-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Snyk dependency test
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high --sarif-file-output=snyk-results.sarif

      - name: Upload to GitHub Security tab
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'snyk-results.sarif'
```

### 4.3 基础容器镜像签名验证

使用 Sigstore/Cosign 对基础镜像进行签名与验证。

```bash
# 生成密钥对（或使用 KMS）
cosign generate-key-pair

# 签名镜像
cosign sign --key cosign.key \
  registry.rv-insights.io/mcp-server:v1.2.3

# 验证镜像（在 CI/CD 中强制执行）
cosign verify --key cosign.pub \
  registry.rv-insights.io/mcp-server:v1.2.3
```

**Kubernetes 准入控制器（Kyverno / OPA Gatekeeper）强制签名验证：**

```yaml
# kyverno/policy/verify-image.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
spec:
  validationFailureAction: Enforce
  background: false
  rules:
    - name: verify-cosign-signature
      match:
        any:
          - resources:
              kinds:
                - Pod
              namespaces:
                - rv-insights
      verifyImages:
        - imageReferences:
            - "registry.rv-insights.io/*"
          attestors:
            - entries:
                - keys:
                    publicKeys: |
                      -----BEGIN PUBLIC KEY-----
                      MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE8G...
                      -----END PUBLIC KEY-----
          required: true
```

### 4.4 不可变构建（Reproducible Build）策略

```dockerfile
# Dockerfile.reproducible
# 使用固定基础镜像 digest
FROM python:3.11.9-slim-bookworm@sha256:abc123...

# 固定构建时间戳
ENV SOURCE_DATE_EPOCH=1713686400

# 使用锁定文件安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# 记录构建信息
LABEL org.opencontainers.image.source="https://github.com/rv-insights/platform"
LABEL org.opencontainers.image.revision="${GIT_COMMIT}"
LABEL org.opencontainers.image.build-date="${BUILD_DATE}"

# 使用非 root 用户运行
RUN useradd -m -u 1000 rvuser
USER rvuser

WORKDIR /app
COPY --chown=rvuser:rvuser . .

EXPOSE 8080
CMD ["python", "-m", "app"]
```

**Reproducible Build 验证脚本：**

```bash
#!/bin/bash
set -euo pipefail

IMAGE_TAG=$1
BUILD_DIR=$(mktemp -d)

# 拉取已构建镜像
docker pull registry.rv-insights.io/mcp-server:${IMAGE_TAG}

# 重新构建（使用相同源码和参数）
git checkout ${IMAGE_TAG}
SOURCE_DATE_EPOCH=1713686400 docker build \
  -f Dockerfile.reproducible \
  -t mcp-server-rebuild:${IMAGE_TAG} \
  --build-arg GIT_COMMIT=$(git rev-parse HEAD) \
  --build-arg BUILD_DATE=$(date -u -d @1713686400 +%Y-%m-%dT%H:%M:%SZ) \
  .

# 比较镜像 digest
ORIGINAL_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' \
  registry.rv-insights.io/mcp-server:${IMAGE_TAG})
REBUILD_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' \
  mcp-server-rebuild:${IMAGE_TAG})

if [ "$ORIGINAL_DIGEST" == "$REBUILD_DIGEST" ]; then
  echo "Build is reproducible: $ORIGINAL_DIGEST"
  exit 0
else
  echo "Build is NOT reproducible!"
  echo "Original: $ORIGINAL_DIGEST"
  echo "Rebuild:  $REBUILD_DIGEST"
  exit 1
fi
```

---

## 5. 代码安全审计自动化

> 核心原则：自动化检测 + 人工确认。机器负责发现潜在问题，人类负责最终判断。

### 5.1 补丁提交前强制安全检查清单

在人工审核 UI 中集成安全检查清单，所有补丁必须通过以下检查方可进入人工审核阶段。

```typescript
// 安全检查清单数据结构
interface SecurityChecklist {
  session_id: string;
  patch_id: string;
  checks: SecurityCheck[];
  overall_status: "PASS" | "FAIL" | "WARNING";
  completed_at: string;
}

interface SecurityCheck {
  id: string;
  category: "secret" | "dependency" | "static_analysis" | "behavior" | "riscv_specific";
  name: string;
  description: string;
  status: "PASS" | "FAIL" | "WARNING" | "PENDING";
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  details?: string;
  tool_output?: string;
  remediation?: string;
}

// 默认检查项
const DEFAULT_SECURITY_CHECKS: SecurityCheck[] = [
  {
    id: "secret-scan",
    category: "secret",
    name: "硬编码凭据扫描",
    description: "检测补丁中是否包含 API Key、密码、私钥等敏感信息",
    status: "PENDING",
    severity: "CRITICAL"
  },
  {
    id: "dependency-scan",
    category: "dependency",
    name: "依赖漏洞扫描",
    description: "检查新增依赖是否存在已知 CVE",
    status: "PENDING",
    severity: "HIGH"
  },
  {
    id: "static-analysis",
    category: "static_analysis",
    name: "静态代码分析",
    description: "运行 sparse、clang-tidy、semgrep 检测代码缺陷",
    status: "PENDING",
    severity: "HIGH"
  },
  {
    id: "behavior-analysis",
    category: "behavior",
    name: "沙箱行为分析",
    description: "监控测试执行期间的系统调用与网络行为",
    status: "PENDING",
    severity: "HIGH"
  },
  {
    id: "riscv-spec-check",
    category: "riscv_specific",
    name: "RISC-V 规范符合性",
    description: "检查是否违反 RISC-V ISA/ABI 规范",
    status: "PENDING",
    severity: "HIGH"
  },
  {
    id: "memory-safety",
    category: "static_analysis",
    name: "内存安全审查",
    description: "检测 UAF、越界访问、缓冲区溢出等漏洞",
    status: "PENDING",
    severity: "CRITICAL"
  }
];
```

**人工审核 UI 安全检查面板（Markdown 规格）：**

```markdown
## 安全检查面板 (Security Check Panel)

### 布局
- 位置：代码 Diff 查看器上方，占据全宽横幅区域
- 状态：根据 overall_status 显示绿色(PASS)/黄色(WARNING)/红色(FAIL)边框

### 交互
1. **展开/折叠**：点击标题展开详细检查项列表
2. **查看详情**：每项右侧有 "查看报告" 按钮，点击弹出模态框展示完整工具输出
3. **强制通过**：管理员可点击 "Override" 按钮跳过某项检查（需填写理由并记录审计日志）
4. **重新扫描**：对 PENDING 或 WARNING 项，可触发重新扫描

### 阻塞规则
- 任何 CRITICAL 级别检查为 FAIL 时，禁止点击 "APPROVE" 按钮
- HIGH 级别检查为 FAIL 时，显示二次确认弹窗
- WARNING 状态不阻塞，但必须在注释中说明已审阅
```

### 5.2 敏感数据泄露扫描

**git-secrets 配置：**

```bash
# 安装 git-secrets
git secrets --install
git secrets --register-aws  # AWS 密钥模式
git secrets --add 'api[_-]?key\s*=\s*["\']\w{16,}["\']'
git secrets --add 'private[_-]?key\s*=\s*["\']\w{32,}["\']'
git secrets --add 'sk-[a-zA-Z0-9]{20,}'  # OpenAI/Anthropic key pattern
```

**TruffleHog 企业级扫描（CI 集成）：**

```yaml
# .github/workflows/trufflehog-scan.yml
name: TruffleHog Secret Scan

on: [push, pull_request]

jobs:
  trufflehog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: TruffleHog Scan
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: main
          head: HEAD
          extra_args: --debug --only-verified

      - name: Scan Git History
        run: |
          trufflehog git file://. --since-commit=HEAD~50 --only-verified --json > trufflehog-history.json
          if [ -s trufflehog-history.json ]; then
            echo "Secrets found in git history!"
            cat trufflehog-history.json
            exit 1
          fi
```

### 5.3 RISC-V 特定安全规则

为审核 Agent 和静态分析工具注入 RISC-V 专用安全规则。

**Semgrep RISC-V 规则集：**

```yaml
# .semgrep/rules/riscv-security.yml
rules:
  - id: riscv-kernel-space-access
    pattern: |
      $PTR = ($TYPE *)$USER_ADDR;
      *$PTR = $VALUE;
    languages: [c, cpp]
    message: >
      Potential unsafe kernel-space memory access.
      In RISC-V Linux kernel, user-space pointers must be accessed via
      copy_from_user() / copy_to_user() wrappers.
    severity: ERROR
    metadata:
      category: security
      cwe: "CWE-822"
      references:
        - https://docs.kernel.org/arch/riscv/

  - id: riscv-unsafe-inline-asm
    pattern: |
      __asm__ volatile ($ASM)
    languages: [c, cpp]
    message: >
      Inline assembly detected. Ensure it does not bypass kernel security
      mechanisms (e.g., SMAP/SMEP on RISC-V with PMP).
    severity: WARNING
    metadata:
      category: security

  - id: riscv-missing-smp-barrier
    pattern: |
      spin_lock(&$LOCK);
      ...
      spin_unlock(&$LOCK);
    languages: [c, cpp]
    message: >
      Verify that spin_lock/spin_unlock pairs include proper SMP barriers
      for RISC-V weak memory model. Consider using smp_mb__after_spinlock().
    severity: WARNING
    metadata:
      category: security
      references:
        - https://riscv.org/wp-content/uploads/2019/12/riscv-spec.pdf

  - id: riscv-uninitialized-csr
    pattern: |
      csr_read($CSR);
    languages: [c, cpp]
    message: >
      CSR read without prior initialization check. Some CSRs may have
      architecturally undefined values at boot.
    severity: WARNING

  - id: riscv-stack-buffer-overflow
    pattern: |
      char $BUF[$SIZE];
      ...
      strcpy($BUF, $SRC);
    languages: [c, cpp]
    message: >
      Potential stack buffer overflow. Use strlcpy or ensure bounds checking.
    severity: ERROR
    metadata:
      category: security
      cwe: "CWE-121"
```

**自定义 Clang Static Analyzer Checker（RISC-V 内核）：**

```cpp
// clang-tools-extra/clang-tidy/riscv/RiscvKernelAccessChecker.cpp
#include "clang/StaticAnalyzer/Checkers/BuiltinCheckerRegistration.h"
#include "clang/StaticAnalyzer/Core/BugReporter/BugType.h"
#include "clang/StaticAnalyzer/Core/Checker.h"
#include "clang/StaticAnalyzer/Core/PathSensitive/CallEvent.h"
#include "clang/StaticAnalyzer/Core/PathSensitive/CheckerContext.h"

using namespace clang;
using namespace ento;

namespace {
class RiscvKernelAccessChecker : public Checker<check::PreCall> {
  mutable std::unique_ptr<BugType> BT;

public:
  void checkPreCall(const CallEvent &Call, CheckerContext &C) const {
    if (!BT)
      BT = std::make_unique<BugType>(this, "Unsafe RISC-V kernel memory access",
                                     "RISC-V Security");

    // 检测直接解引用用户空间指针
    if (const auto *FD = Call.getDecl()->getAsFunction()) {
      StringRef Name = FD->getName();
      if (Name == "__get_user" || Name == "__put_user")
        return;  // 白名单：安全包装函数

      // 检测直接指针解引用
      for (unsigned i = 0; i < Call.getNumArgs(); ++i) {
        const Expr *Arg = Call.getArgExpr(i);
        if (isUserSpacePointer(Arg, C)) {
          ExplodedNode *N = C.generateErrorNode();
          if (N) {
            auto R = std::make_unique<PathSensitiveBugReport>(
                *BT, "Potential unsafe access to user-space pointer", N);
            C.emitReport(std::move(R));
          }
        }
      }
    }
  }

  bool isUserSpacePointer(const Expr *E, CheckerContext &C) const {
    // 简化实现：检测是否来自 __user 标记的指针
    QualType T = E->getType();
    return T.hasAttr(attr::AddressSpace) &&
           T.getAddressSpace() == LangAS::opencl_global;  // 简化示例
  }
};
}

void ento::registerRiscvKernelAccessChecker(CheckerManager &mgr) {
  mgr.registerChecker<RiscvKernelAccessChecker>();
}
```

---

## 6. 数据隐私与合规

> 核心原则：数据最小化、目的限制、存储限制、完整性与保密性（GDPR 第 5 条）。

### 6.1 日志脱敏策略

所有日志在写入存储前必须经过脱敏处理，确保不包含 PII（个人可识别信息）或敏感代码片段。

```python
# utils/log_sanitizer.py
import re
import hashlib
from typing import Any, Dict

class LogSanitizer:
    """日志脱敏器：在写入日志前移除或匿名化敏感数据"""

    # 正则模式定义
    PATTERNS = {
        "email": (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), "[EMAIL_REDACTED]"),
        "phone": (re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'), "[PHONE_REDACTED]"),
        "api_key": (re.compile(r'(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36})'), "[API_KEY_REDACTED]"),
        "ip_address": (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'), "[IP_REDACTED]"),
        "credit_card": (re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'), "[CC_REDACTED]"),
    }

    # 代码片段匿名化配置
    CODE_ANONYMIZATION = {
        "preserve_structure": True,  # 保留代码结构，替换标识符
        "max_code_length": 500,      # 超过此长度的代码片段截断并哈希
        "hash_algorithm": "sha256",
    }

    @classmethod
    def sanitize(cls, data: Any) -> Any:
        """递归脱敏任意数据结构"""
        if isinstance(data, dict):
            return {k: cls.sanitize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.sanitize(item) for item in data]
        elif isinstance(data, str):
            return cls._sanitize_string(data)
        return data

    @classmethod
    def _sanitize_string(cls, text: str) -> str:
        # 应用正则脱敏
        for name, (pattern, replacement) in cls.PATTERNS.items():
            text = pattern.sub(replacement, text)

        # 代码片段匿名化
        if cls._is_code_snippet(text):
            text = cls._anonymize_code(text)

        return text

    @classmethod
    def _is_code_snippet(cls, text: str) -> bool:
        """启发式检测是否为代码片段"""
        code_indicators = [
            "def ", "class ", "#include", "int main", "function", "const ",
            "var ", "let ", "=>", "{}", ";\n", "# ", "// ", "/* ", "*/",
            "__asm__", "csr_", "spin_lock", "copy_from_user"
        ]
        return any(ind in text for ind in code_indicators)

    @classmethod
    def _anonymize_code(cls, code: str) -> str:
        """匿名化代码片段：保留结构，替换标识符"""
        if len(code) > cls.CODE_ANONYMIZATION["max_code_length"]:
            # 截断并哈希
            prefix = code[:200]
            suffix = code[-100:]
            hash_val = hashlib.sha256(code.encode()).hexdigest()[:16]
            return f"[CODE_TRUNCATED hash:{hash_val}]\n{prefix}\n...\n{suffix}"

        # 简单标识符替换（保留结构）
        # 注意：生产环境应使用 AST 解析进行更精确的匿名化
        code = re.sub(r'\b[a-zA-Z_]\w{3,}\b', lambda m: cls._hash_identifier(m.group()), code)
        return f"[CODE_ANONYMIZED]\n{code}"

    @classmethod
    def _hash_identifier(cls, ident: str) -> str:
        """将标识符哈希为固定长度的匿名标识符"""
        h = hashlib.sha256(ident.encode()).hexdigest()[:8]
        return f"id_{h}"


# 使用示例
import logging
import json

class SanitizedLogHandler(logging.StreamHandler):
    def emit(self, record):
        if isinstance(record.msg, dict):
            record.msg = LogSanitizer.sanitize(record.msg)
        elif isinstance(record.msg, str):
            record.msg = LogSanitizer.sanitize(record.msg)
        super().emit(record)

# 配置日志
logger = logging.getLogger("rv-insights")
handler = SanitizedLogHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# 示例：LLM 对话日志脱敏
llm_conversation = {
    "session_id": "sess-123",
    "agent": "developer",
    "prompt": "请优化以下函数：def calculate_hash(data): ...",
    "response": "优化后的代码：def optimized_hash(data): ...",
    "user_email": "admin@rv-insights.io"  # 将被脱敏
}
logger.info(llm_conversation)
# 输出：{... "user_email": "[EMAIL_REDACTED]", "prompt": "[CODE_ANONYMIZED]\n..."}
```

### 6.2 会话数据保留策略与 GDPR 合规删除

**数据分类与保留期限：**

| 数据类别 | 示例 | 保留期限 | 删除机制 |
|----------|------|----------|----------|
| 会话元数据 | session_id, 时间戳, 状态 | 2 年 | 自动归档后删除 |
| LLM 对话记录 | Prompt, Response | 90 天 | 自动清理任务 |
| 代码变更产物 | Patch, Diff | 1 年 | 用户请求后 30 天内删除 |
| 审计日志 | 操作记录, 决策历史 | 7 年 | 仅归档，不可删除（合规要求） |
| 用户个人数据 | 邮箱, 姓名, 偏好 | 账户存续期 | 账户注销后立即删除 |
| 沙箱执行日志 | strace, 网络日志 | 30 天 | 自动清理任务 |

**GDPR 删除机制（Right to Erasure）：**

```python
# services/compliance/gdpr_service.py
from datetime import datetime, timedelta
from typing import List
import asyncio

class GDPRComplianceService:
    """GDPR 合规服务：处理数据删除请求与自动清理"""

    RETENTION_POLICIES = {
        "llm_conversation": timedelta(days=90),
        "sandbox_logs": timedelta(days=30),
        "code_artifacts": timedelta(days=365),
        "session_metadata": timedelta(days=730),
    }

    async def handle_deletion_request(self, user_id: str) -> Dict[str, Any]:
        """
        处理用户删除请求（GDPR Article 17）。
        流程：
        1. 验证用户身份
        2. 生成删除任务清单
        3. 执行级联删除（软删除 + 异步硬删除）
        4. 生成删除证明报告
        """
        deletion_report = {
            "user_id": self._hash_user_id(user_id),
            "requested_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "deleted_items": [],
            "retained_items": [],  # 法律要求保留的审计日志
            "status": "IN_PROGRESS"
        }

        # 1. 删除用户个人数据
        personal_data = await self.db.users.find({"user_id": user_id})
        for record in personal_data:
            await self._secure_delete("users", record["_id"])
            deletion_report["deleted_items"].append({
                "table": "users",
                "record_id": str(record["_id"]),
                "type": "personal_data"
            })

        # 2. 匿名化会话关联数据（保留审计日志但去除 PII）
        sessions = await self.db.sessions.find({"created_by": user_id})
        for session in sessions:
            await self._anonymize_session(session["_id"], user_id)
            deletion_report["deleted_items"].append({
                "table": "sessions",
                "record_id": str(session["_id"]),
                "type": "anonymized"
            })

        # 3. 审计日志保留（法律要求），但去除 PII
        audit_logs = await self.db.audit_logs.find({"user_id": user_id})
        for log in audit_logs:
            await self.db.audit_logs.update_one(
                {"_id": log["_id"]},
                {"$set": {
                    "user_id": "[REDACTED]",
                    "user_email": "[REDACTED]",
                    "ip_address": "[REDACTED]"
                }}
            )
            deletion_report["retained_items"].append({
                "table": "audit_logs",
                "record_id": str(log["_id"]),
                "reason": "legal_retention_required",
                "retention_until": (datetime.utcnow() + timedelta(days=2555)).isoformat()
            })

        # 4. 触发异步清理（S3 对象、Redis 缓存）
        await self._trigger_async_cleanup(user_id)

        deletion_report["completed_at"] = datetime.utcnow().isoformat()
        deletion_report["status"] = "COMPLETED"
        
        # 5. 将删除报告写入 WORM 存储作为法律证明
        await self.worm_storage.write(
            f"gdpr-deletions/{deletion_report['requested_at']}/{user_id}.json",
            deletion_report
        )
        
        return deletion_report

    async def _secure_delete(self, table: str, record_id: Any):
        """安全删除：先软删除，再异步覆写硬删除"""
        # 软删除标记
        await self.db[table].update_one(
            {"_id": record_id},
            {"$set": {"deleted_at": datetime.utcnow(), "_deleted": True}}
        )
        
        # 发送到消息队列，由异步 worker 执行覆写删除
        await self.mq.publish("secure-deletion-queue", {
            "table": table,
            "record_id": str(record_id),
            "scheduled_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
        })

    async def _anonymize_session(self, session_id: str, user_id: str):
        """匿名化会话数据：保留技术数据，去除 PII"""
        await self.db.sessions.update_one(
            {"_id": session_id},
            {"$set": {
                "created_by": "[ANONYMIZED]",
                "human_decisions.$[].decided_by": "[ANONYMIZED]",
                "anonymized_at": datetime.utcnow().isoformat()
            }}
        )

    async def run_retention_cleanup(self):
        """每日运行的自动清理任务"""
        for data_type, retention in self.RETENTION_POLICIES.items():
            cutoff = datetime.utcnow() - retention
            
            if data_type == "llm_conversation":
                await self.db.llm_logs.delete_many({
                    "created_at": {"$lt": cutoff}
                })
            elif data_type == "sandbox_logs":
                # 删除 S3 上的沙箱日志
                old_logs = await self.s3.list_objects(
                    prefix="sandbox-logs/",
                    older_than=cutoff
                )
                for obj in old_logs:
                    await self.s3.delete_object(obj["key"])
            # ... 其他类型

        logger.info(f"Retention cleanup completed for {datetime.utcnow().date()}")
```

### 6.3 审计日志的不可篡改存储

审计日志必须满足不可篡改（Tamper-Evident）和不可删除（WORM）的要求，采用分层存储策略。

**架构设计：**

```mermaid
graph LR
    SVC["平台服务"] -->|写入| KAFKA["Kafka<br/>审计日志流"]
    KAFKA -->|消费| PROCESSOR["日志处理器<br/>结构化 + 脱敏"]
    PROCESSOR -->|批量写入| S3_WORM["S3 Object Lock<br/>WORM 存储<br/>7年保留期"]
    PROCESSOR -->|实时索引| ES["Elasticsearch<br/>查询层<br/>90天热数据"]
    S3_WORM -->|每日哈希| BLOCKCHAIN["区块链轻节点<br/>哈希锚定<br/>Bitcoin/Ethereum"]
    
    ADMIN["合规管理员"] -->|查询| ES
    ADMIN -->|取证| S3_WORM
    AUDITOR["外部审计员"] -->|验证哈希| BLOCKCHAIN
```

**S3 WORM 配置（MinIO 或 AWS S3）：**

```bash
# 创建启用了 Object Lock 的 Bucket
aws s3api create-bucket \
  --bucket rv-insights-audit-logs \
  --object-lock-enabled-for-bucket

# 配置默认保留策略（7 年，合规模式）
aws s3api put-object-lock-configuration \
  --bucket rv-insights-audit-logs \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Years": 7
      }
    }
  }'

# 写入审计日志时显式设置保留
aws s3api put-object \
  --bucket rv-insights-audit-logs \
  --key audit/2026/04/21/audit-log-0001.jsonl \
  --body audit-log-0001.jsonl \
  --object-lock-mode COMPLIANCE \
  --object-lock-retain-until-date "2033-04-21T00:00:00Z"
```

**区块链哈希锚定（每日批次）：**

```python
# services/compliance/blockchain_anchor.py
import hashlib
import json
from web3 import Web3
from datetime import datetime

class BlockchainAnchorService:
    """将审计日志批次哈希锚定到区块链，提供不可篡改证明"""

    def __init__(self):
        # 连接到以太坊节点（或使用 Bitcoin 的 OP_RETURN）
        self.w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/..."))
        self.anchor_wallet = "0x..."  # 专用锚定钱包
        self.private_key = os.environ["ANCHOR_PRIVATE_KEY"]  # 从 Vault 获取

    async def anchor_daily_batch(self, date: str):
        """
        每日将前一天的审计日志批次哈希写入区块链。
        流程：
        1. 计算当天所有日志文件的 Merkle Root
        2. 将 Merkle Root 写入智能合约或作为交易 data
        3. 记录交易哈希，供后续验证
        """
        # 1. 获取当天的所有日志文件
        log_files = await self.s3.list_objects(
            prefix=f"audit/{date.replace('-', '/')}"
        )

        # 2. 计算 Merkle Root
        leaves = []
        for obj in log_files:
            content = await self.s3.get_object(obj["key"])
            leaves.append(hashlib.sha256(content).hexdigest())
        
        merkle_root = self._compute_merkle_root(leaves)

        # 3. 构建并发送锚定交易
        tx_data = self._build_anchor_transaction(merkle_root, date)
        tx_hash = await self._send_transaction(tx_data)

        # 4. 记录锚定证明
        proof = {
            "date": date,
            "merkle_root": merkle_root,
            "blockchain": "ethereum",
            "transaction_hash": tx_hash,
            "block_number": await self._get_tx_block(tx_hash),
            "anchored_at": datetime.utcnow().isoformat(),
            "log_file_count": len(log_files)
        }

        await self.s3.put_object(
            key=f"audit-proofs/{date}.json",
            body=json.dumps(proof, indent=2)
        )

        logger.info(f"Audit log batch anchored: {tx_hash}")
        return proof

    def _compute_merkle_root(self, leaves: List[str]) -> str:
        """计算 Merkle Root"""
        if len(leaves) == 0:
            return hashlib.sha256(b"").hexdigest()
        
        while len(leaves) > 1:
            if len(leaves) % 2 == 1:
                leaves.append(leaves[-1])  # 奇数时复制最后一个
            
            new_level = []
            for i in range(0, len(leaves), 2):
                combined = leaves[i] + leaves[i+1]
                new_level.append(hashlib.sha256(combined.encode()).hexdigest())
            leaves = new_level
        
        return leaves[0]

    def _build_anchor_transaction(self, merkle_root: str, date: str) -> dict:
        """构建锚定交易（使用合约调用或直接 data 字段）"""
        nonce = self.w3.eth.get_transaction_count(self.anchor_wallet)
        
        # 方法：将数据写入交易 input data（成本较低）
        data = f"0xRVINSIGHTS{date.replace('-', '')}{merkle_root}"
        
        tx = {
            'nonce': nonce,
            'to': self.anchor_wallet,  # 发送给自己
            'value': 0,
            'gas': 21000 + len(data) * 68,  # 基础 gas + data gas
            'gasPrice': self.w3.to_wei('20', 'gwei'),
            'data': data,
            'chainId': 1
        }
        return tx

    async def verify_integrity(self, date: str) -> bool:
        """验证某天的审计日志是否被篡改"""
        # 1. 读取存储的证明
        proof = await self.s3.get_object(f"audit-proofs/{date}.json")
        proof = json.loads(proof)

        # 2. 重新计算 Merkle Root
        log_files = await self.s3.list_objects(
            prefix=f"audit/{date.replace('-', '/')}"
        )
        leaves = []
        for obj in log_files:
            content = await self.s3.get_object(obj["key"])
            leaves.append(hashlib.sha256(content).hexdigest())
        
        computed_root = self._compute_merkle_root(leaves)

        # 3. 验证链上交易
        tx = self.w3.eth.get_transaction(proof["transaction_hash"])
        stored_root = tx["input"][22:86]  # 提取 Merkle Root

        return computed_root == stored_root == proof["merkle_root"]
```

---

## 7. 安全运营与应急响应

### 7.1 安全事件分级

| 级别 | 定义 | 示例 | 响应时间 | 通知范围 |
|------|------|------|----------|----------|
| P0 - 紧急 | 生产环境被入侵或数据泄露 | 沙箱逃逸成功、密钥泄露 | 15 分钟 | 全员 + 高管 + 法务 |
| P1 - 严重 | 潜在入侵或核心功能受损 | 大量异常系统调用、未授权访问尝试 | 1 小时 | 安全团队 + SRE |
| P2 - 高危 | 安全策略违规或漏洞暴露 | 依赖项出现 CVE、配置漂移 | 4 小时 | 安全团队 |
| P3 - 中危 | 安全加固项或低风险问题 | 证书即将过期、日志脱敏不完整 | 24 小时 | 值班工程师 |

### 7.2 应急响应 playbook

**场景：检测到沙箱逃逸尝试**

```markdown
1. **立即遏制**（0-5 分钟）
   - 自动：Falco 触发 -> Kubernetes NetworkPolicy 隔离该 Pod
   - 人工：确认隔离状态，必要时手动 `kubectl delete pod`

2. **取证保存**（5-15 分钟）
   - 保存 VM 内存快照：`curl -X PUT http://firecracker/socket/mem --data-binary @mem.dump`
   - 保存磁盘镜像副本到隔离存储
   - 导出该会话所有审计日志

3. **影响评估**（15-30 分钟）
   - 检查该会话是否访问过其他内部服务
   - 检查 Vault 审计日志，确认是否有凭证被读取
   - 检查网络流量日志，确认是否有数据外泄

4. **根除与恢复**（30-60 分钟）
   - 轮换该会话接触过的所有凭证（Git Token、LLM API Key）
   - 更新 seccomp 配置文件，封堵被利用的 syscall
   - 重新部署加固后的沙箱镜像

5. **事后复盘**（24 小时内）
   - 编写事件报告（Timeline、Root Cause、Impact、Lessons Learned）
   - 更新威胁模型和检测规则
   - 向社区披露（如影响开源贡献）
```

### 7.3 安全监控仪表板

```yaml
# Grafana Dashboard 配置摘要
panels:
  - title: "沙箱逃逸尝试"
    type: stat
    query: 'sum(rate(falco_events_total{priority=~"CRITICAL|HIGH"}[5m]))'
    alert: "> 0"

  - title: "Vault 异常访问"
    type: graph
    query: 'sum(rate(vault_audit_log_failure[5m])) by (auth_method)'

  - title: "API 网关拒绝率"
    type: graph
    query: 'sum(rate(envoy_http_rq_xx{response_code_class=~"4xx|5xx"}[5m]))'

  - title: "LLM API 异常响应"
    type: table
    query: 'sum by (session_id, reason) (llm_proxy_blocked_total)'

  - title: "凭证轮换状态"
    type: gauge
    query: 'vault_token_ttl{role=~"developer|explorer"} < 3600'
```

---

## 8. 附录

### 附录 A：安全自查清单

在每次发布前，必须完成以下检查：

- [ ] 无硬编码凭据（通过 pre-commit + CI 扫描）
- [ ] 所有服务间通信启用 mTLS
- [ ] API 网关配置 JWT 验证与速率限制
- [ ] WebSocket 连接启用 TLS + Origin 校验
- [ ] Vault 动态凭证策略已更新
- [ ] 沙箱 seccomp 配置文件为最新版本
- [ ] Firecracker VM 镜像已签名且签名验证通过
- [ ] 依赖 lock 文件已更新且校验通过
- [ ] SBOM 已生成并上传
- [ ] 容器镜像已通过 Cosign 签名
- [ ] 审计日志 WORM 存储策略已启用
- [ ] 日志脱敏规则已覆盖所有 PII 类型
- [ ] GDPR 删除接口已通过测试
- [ ] 安全事件响应 playbook 已更新

### 附录 B：参考标准与合规框架

| 标准/框架 | 适用领域 | 对应章节 |
|-----------|----------|----------|
| NIST SP 800-207 | 零信任架构 | 第 1 章 |
| NIST SP 800-204B | 微服务安全 | 第 1、2 章 |
| CIS Docker Benchmark | 容器安全 | 第 3 章 |
| CIS Kubernetes Benchmark | K8s 安全 | 第 1、3 章 |
| SLSA (Supply-chain Levels for Software Artifacts) | 供应链安全 | 第 4 章 |
| GDPR (EU 2016/679) | 数据隐私 | 第 6 章 |
| ISO 27001:2022 A.8.9 | 配置管理 | 第 4 章 |
| OWASP Top 10 2021 | 应用安全 | 第 5 章 |

### 附录 C：关键配置文件索引

| 配置文件 | 路径 | 用途 |
|----------|------|------|
| Istio PeerAuthentication | `k8s/security/peer-auth.yaml` | 服务间 mTLS |
| Envoy SecurityPolicy | `k8s/security/envoy-policy.yaml` | API 网关认证授权 |
| Vault 策略 | `vault/policies/` | 动态凭证管控 |
| seccomp-bpf | `sandbox/seccomp/default.json` | 系统调用过滤 |
| AppArmor Profile | `sandbox/apparmor/rv-insights-sandbox` | 强制访问控制 |
| Firecracker 配置 | `sandbox/firecracker/vm-config.json` | MicroVM 隔离 |
| Falco 规则 | `falco/rules/rv-insights-sandbox.yaml` | 逃逸检测 |
| Kyverno 策略 | `kyverno/policy/verify-image.yaml` | 镜像签名验证 |
| Semgrep 规则 | `.semgrep/rules/` | 代码安全扫描 |
| Pre-commit 配置 | `.pre-commit-config.yaml` | 提交前安全检查 |
| CI 安全流水线 | `.github/workflows/security*.yml` | 持续安全扫描 |

---

**文档结束**
