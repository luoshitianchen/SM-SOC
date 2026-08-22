# SM SOC

安全运营中心：事件、风险评分、威胁检测和响应。

```powershell
git clone https://github.com/luoshitianchen/SM-SOC.git
cd SM-SOC
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8460
```

接口：`/health`、`/readyz`、`/api/overview`、`/api/items`、`/api/ops/metrics`、`/api/crypto/status`。

内置 TrustedHost、安全响应头、CSP、国密状态接口和容器加固。
