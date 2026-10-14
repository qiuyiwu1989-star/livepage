# 导入、任务与验收分开记录

2026-10-14 用户决定：暂定数据处理使用 DeepSeek harness 中的 MiMo 2.6 Flash，包括标注与 HTML 转换。模型端点、真实模型标识与任务提交协议尚未核验；不复用备课模型端点来冒充这条管道。备课 Agent 与资料处理是两类调用。

课程统一入口，来源用 Keynote/PDF/历史课件标记。来源不代表处理完成。每页分别显示标注、HTML、任务和阶段确认。标注候选不是已确认知识，HTML 草稿不是已验收页面，整份 Keynote 导出不是逐页可编辑转换。

只读处理汇总：GET /api/library/processing。可选私有旁挂 data/processing-jobs.json，结构 {"pages":{"<page_id>":{"status":"queued","job_id":"..."}}}。缺登记只说明未登记，不能推断外部任务不存在；不自动提交任务。状态 queued/running/failed/blocked/succeeded 仍应由外部任务适配器维护，当前尚未接通。

stage_reviews.annotation/html 分别保存 status=confirmed 与 evidence_ref；无阶段证据不将历史总 human_review 或 pixel-compare 清单标签迁成验收完成。未来确认需绑定来源和制品版本，当前为兼容读取，不新增确认写接口。

后续：核验 harness 任务协议和模型实际 ID → 对账已存在任务 → 列出未登记页 → 按代表页小批处理 → 原图/渲染/结构对照 → 人工确认后扩大。此轮不重新转换、覆盖原稿或标注，不调用收费模型。
