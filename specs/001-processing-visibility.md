# 001 课程与处理状态

用户要求区分已处理与未处理，并识别尚未登记管道任务的导入资料。

## 范围
统一课程入口，保留不同来源与课程ID；只读汇总标注、HTML、任务和确认，不能以原文、导入或总确认字段冒充阶段完成。

## 不做
不自动排队、不调用模型、不覆盖原件、不批量转换、不宣称外部任务不存在。

## 验收
- python3 -m unittest discover -s workbench -p 'test_*.py'
- 选择Keynote/PDF课件时高亮对应入口，来源与处理进度分开。
- 无任务登记表显示不可确认外部管道；HTML草稿及pixel-compare不是人工确认。
- 待完成：私有真实数据及登录浏览器验收、部署。

## 状态
implemented-local / pending-browser-and-deployment
