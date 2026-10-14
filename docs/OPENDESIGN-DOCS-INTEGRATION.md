# OpenDesign Docs 接口核对 · 2026-10-14

用户确认入口：https://doc.opendesign.cc 。本次通过HTTPS读取线上入口及它引用的JS（index-CRj4q-6X.js、handoff-Cta5Eb70.js、document-import-C-eM9kRc.js）。以下为静态代码核对，尚非真实浏览器往返验收。原始资源存私有jobs/opendesign-docs-audit-20261014，不入公开仓库。

## 已确认的现有协议

- 导入UTF-8 .html/.htm，单文件最多5 MiB，名称清理后最多150字符。
- 文档/正式版本/草稿/批注存浏览器IndexedDB `opendesign-docs` v3；代码显示版本与草稿有并发校验。不能因此宣称服务端存储或活页回库已接通。
- 入口 `https://doc.opendesign.cc/#handoff=v1` 从window.opener收文档。编辑器发送 `opendesign:handoff-ready`，v=1，随机nonce；来源回复 `opendesign:handoff`、v=1、同nonce、document={name,html,generator?,sourceUrl?}。用户在编辑器确认后保存；返回 `opendesign:handoff-result`（成功/失败信息）。等待15秒超时。
- LivePage实现时必须校验event.origin为精确编辑器origin、event.source为打开的窗口、nonce及消息版本，向精确origin发HTML；不要把ready的广播方式误用为文档广播。
- handoff-result是导入结果，不是编辑完自动回传。已读取的handoff模块未提供保存后返回HTML的协议；需要继续核实导出/下载路径与源码。
- 编辑器使用data-doc-text/data-doc-slide作内部识别，双击切换文字编辑。导入会清理contenteditable及data-doc-*，因此活页自有data-lp-object-id不能直接当编辑器内部ID，保留情况需实测。

## 下一步验收

先用合成单页验证导入→改文字→保存版本→导出HTML→核对data-lp-object-id和字体/坐标，再试真实候选。编辑返回需携带活页基线版本，不凭编辑器自建UUID覆盖知识身份。Deck检测对article.slide及源比例的支持仍待核实；如只支持多section格式，做独立适配，不改源单页。

当前活页实验包是外部适配前的来源与版本封套。尚未上传私人材料、实际导入、自动回写或生产部署。
