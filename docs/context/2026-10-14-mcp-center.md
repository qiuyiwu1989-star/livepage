# MCP 中心部署

入口 /admin/mcp/，Nginx继承/_qy_auth登录检查，代理到127.0.0.1:5498。systemd mcp-center，独立center-venv，代码复用integrations/mcp/center.py/html/js。所有响应no-store，写入Origin+双提交CSRF，管理服务仅接受loopback Host。

支持：服务目录与其他MCP元数据登记；LivePage密钥备注/1-20份课程/下载开关/有效期（1-90天）；仅创建响应返回明文，列表仅返回安全元数据；撤销后远程MCP下一请求失效。无自动下载或分享凭据。中心注册表/现有LivePage验证器共享/opt/livepage/state/mcp/clients.json，文件0600，写入跨进程锁+原子替换。

新登记的其他服务默认key_management=false。仅目录登记不表示已探活或已授权；后续通过对应服务验证器/适配器接入，不能把中心密钥拿到未集成服务上使用。当前没有最近使用时间统计，不编造该指标。

验证：13项MCP/中心测试通过。线上中心内部200、匿名外部跳登录；真实中心签发临时密钥→HTTPS MCP初始化/课程读取→撤销→401。验收密钥已撤销，未记录明文。尚未完成所有浏览器客户端安装验证。

Nginx改前备份nginx.before-center.conf，首页备份index.before-center.html，均在/opt/livepage/state/mcp。生产新增服务与文档已定向部署；后续发布应收编到独立release脚本。
