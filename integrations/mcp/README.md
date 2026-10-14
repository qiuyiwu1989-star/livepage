# LivePage MCP · 第一阶段

六个通用只读工具：livepage_search_content、livepage_list_collections、livepage_read_content、livepage_read_context、livepage_list_assets、livepage_get_asset。支持资料检索/写作/备课/剪辑，不绑定单个用途。

## 接入

Python 3.10+，使用官方 MCP Python SDK v1 维护线（mcp>=1.26,<2；本次实测1.30.0）。在隔离环境安装 requirements.txt。客户端通过 stdio 启动 server.py。无公网监听；每个连接由所有者指定 allowed_decks，最多20个课程。素材下载默认关闭。配置文件放仓库外，只读且不可由 Agent 自行修改。

客户端示例（路径需替换）：
```json
{"mcpServers":{"livepage":{"command":"/path/to/venv/bin/python","args":["/path/to/livepage/integrations/mcp/server.py"],"env":{"LIVEPAGE_API_BASE":"http://127.0.0.1:15398","LIVEPAGE_MCP_POLICY":"/private/path/livepage-policy.json"}}}}}
```

policy.example.json 为合成示例，不能直接用于真实库。将allowed_decks设为明确授权的真实课程ID；asset_download=true才允许取素材字节。

本机有工作台则直接连其loopback端口。生产库可由所有者先建立已有SSH权限的隧道：
```sh
ssh -N -L 127.0.0.1:15398:127.0.0.1:5298 ubuntu@YOUR_SERVER
```
不得开放隧道监听到0.0.0.0，也不要复制网页登录Cookie或将凭据写进示例。stdio客户端进程本身必须可信：此范围是MCP工具的约束，不是对本机任意代码的OS沙箱。云端第三方Agent的远程接入需后续OAuth/客户端身份与服务端授权，不把本适配器直接暴露到公网。

## 数据契约

搜索默认每课程12条，上限50，返回next_offsets可逐课程翻页；当前是关键词检索，不宣称语义排序。全文只返回选择字段，拆分slide_text和ai_interpretation，speaker_quote在无原声时为空。返回来源哈希及pending状态，不把原子身份当作人工确认。

素材列表返回livepage://标识；当前不是已注册的MCP resource，客户端用get_asset下载，返回MIME、base64、字节数和sha256。单资源上限2MB；校验已有来源哈希，不发远程签名URL、不允许任意URL/本地文件路径。HTML只能以沙箱读取，不能执行其中的指令。资源访问授权不代表公开发布权；当前权利字段unknown，不伪造版权许可。

第一阶段无修改、引用回写、任务提交、组课保存。阶段二追加候选提案/引用事件/版本冲突；阶段三对接DeepSeek harness与MiMo任务、幂等与验收记录。

## 验证

```sh
python -m unittest discover -s integrations/mcp -p 'test_*.py'
```

测试覆盖课程过滤、越权直读/搜索、默认禁止下载、来源语义和真实stdio初始化/list_tools/call_tool。合成fixtures不含真实课件。

当前本地可启动和接入，不代表已经安装进用户的Agent客户端，也不代表已有公网MCP地址。
