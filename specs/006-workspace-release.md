# 006 可接续工作台版本

用户授权收拢并执行现有任务。

## 当前交付
- 标题修改：持久旁挂、来源不覆盖、追加历史、base_revision冲突409。
- 导入与处理：PDF原件归档复用已有接口，缺source-manifest不报错；任务请求可保存、去重，未接执行器保持blocked。
- 阅读入口共用标题编辑脚本，处理入口指向任务页。

## 不做与边界
本轮不伪造harness执行/模型输出，不自动批量转换，不改源文件、课件历史、认证或MCP权限。新PDF归档尚未自动投影进页面目录。框架证据重算、OpenDesign真实回库、精确音频关联仍为后续阶段，不将本版称作全功能完成。

## 验收
python3 -m unittest discover -s workbench -p 'test_*.py'
PYTHONPATH=src python3 -m unittest discover -s tests
浏览器验证修改标题→重开、任务重复提交与受阻显示、PDF归档；正式视觉验收单列，不能用HTTP200替代。
