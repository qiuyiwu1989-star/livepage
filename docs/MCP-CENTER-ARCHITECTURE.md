# 全站 MCP 中心 · 第一期

统一管理入口 /admin/mcp/；统一调用入口 https://qiuyiwu.com/mcp。/mcp/livepage 保留兼容。网页管理中心、协议网关、应用业务API分层，应用注册不等于应用授权。

## 当前实现

应用目录记录 id/name/url/description/integration。已适配livepage，其余登记directory_only；禁止签发未适配应用的有效密钥。

新密钥使用 mcp_ 前缀，凭证哈希仍位于统一clients注册表。授权模型 grants: {"livepage":{"actions":["read","download"],"collections":["course-id"]}}。grants是权威来源，存在时不使用旧allowed_decks/asset_download扩大权限。无grants的历史密钥只映射到livepage，兼容旧接入。保留旧字段供已有消费者过渡，不是第二授权真源。

center_list_applications 返回当前密钥可调用应用和操作；其他工具仍按livepage_命名。当前一个密钥的创建UI只允许选择一个已适配应用，尚不支持多应用联合签发；授权数据结构已为多个应用预留，不宣称全部应用已接通。

## 后续应用接入契约

新增适配器需声明 app_id、工具命名空间、可授予操作、资源范围类型、业务API适配、授权验证与测试。网关按请求上下文解析授权；不得把本机路径、后台Cookie或其他模型Key透传给Agent。接入前完成跨应用越权、撤销、版本与写入边界验收，再标active。

不得仅凭登记URL代理任意远端工具或转发本站密钥。服务状态应来自真实健康检查，当前未探活登记项明确显示未核验。

当前统一入口和LivePage适配已上线；多应用工具动态路由、联合授权、统一调用审计、OAuth仍是后续工作。
