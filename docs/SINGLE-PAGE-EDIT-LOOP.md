# 单页编辑闭环试跑

`workbench/edit_loop.py --store <private-sample-store>` 启动127.0.0.1:5320，界面为edit-loop.html。运行环境需Flask及源场景的FontTools、PyMuPDF依赖；试跑复用外置盘font-tools-env。源材料、版本、请求和提案都在仓库外，不能入公开Git。

存储：versions/00000001.json为基线，每次保存追加序号，含source_sha256、稳定object_id、parent_version_id、HTML哈希、时间、provenance与pending审核状态；font-faces.json显式绑定原字体文件和CSS family。写入通过fsync+独占链接发布，不覆盖历史；仅支持单进程本地试跑。

自然语言框生成agent-jobs/<id>.request.json；Codex或Harness处理后落同ID.proposal.json，提案必须绑定base_version_id，包含真实对象ID与白名单文字/字号/颜色/位置修改。UI显示提案，再保存。当前派发由协作者完成，不是假装已接自动Agent API；模型执行者按实际记录。工作台编辑通过同一保存接口追加版本，基线过期409，原始图像/矢量及其他文字不修改。HTML新文字转义，字体子集按实际字体重新生成。

2026-10-14真实0047浏览器试跑：自然语言把氛围改为氛围与感受、颜色#552288；Codex提案生成v2。工作台改60px和left=800px生成v3；检查发现正文使用Regular、初始配置只重建Bold，新增与/受缺字，已补齐双字体重建，追加v4。未覆盖失败试跑记录。v4字形覆盖、HTML哈希、父链、刷新持久化、原始基线未变均核验；冲突/跨站请求拦截与字体按组更新有合成回归。

限制：本地隔离样本库，不是正式全库或OpenDesign保存回流；工作台当前仅文字/字号/颜色/位置，未做图形对象化、拖拽、撤回、deck引用更新及模型自动调度。所有试改是验收示例，不能冒充用户签收。
