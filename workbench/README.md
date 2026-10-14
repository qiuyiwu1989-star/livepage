# 本地工作台实现（迁移中的适配层）

从现有 LivePage 本地工作台提取的实现代码，含目录/原子读取、可恢复删除、补充标注、母课程、组课版本、Agent 建议、来源治理，以及组课界面和内嵌原图/HTML 阅读器。

它仍是迁移适配层，并非开箱即用的完整公共产品。生成的全库索引、真实原子档案、字体与媒体、目录快照、课程和工作区状态不随代码发布。

## 验证

Python 3.10+，安装 requirements.txt；当前 API 测试仅需 Flask。运行：

```sh
python3 -m unittest discover -s workbench -p 'test_*.py'
```

测试使用临时合成记录。依赖真实历史快照的测试会跳过；不能将跳过项宣称验收通过。

## 连接已有私有工作区

```sh
LIVEPAGE_WORKSPACE_ROOT=/path/to/private/workspace \
LIVEPAGE_CATALOG_ROOT=/path/to/private/catalog-root \
python3 workbench/workspace_server.py
```

catalog-root 下应有 generated/catalog.json；原子与治理视图另依赖 generated/atomic-catalog.json 等既有快照。PRIVATE workspace 需要原有前端、data/annotations.json 等资源。请使用测试数据或已有私有工作区，不要把真实资料提交到这里。

服务默认只监听 127.0.0.1:5198，限制本机 Host。当前静态文件与私有数据隔离依靠本机边界；禁止直接绑定公网。公网部署需要单独完成登录、授权、静态路径白名单、备份及资产权限验收。

模型配置通过部署环境注入；未配置真实 provider 时，不宣称 Agent 已接入。HTML 切换只证明有草稿入口，不证明忠实度或人工验收。库中 generated/accepted、源版本、编辑版本、部署状态必须分别记录。

## 库首页加载

build_index.py 生成新版库首页，需要既有私有索引、标题与预览清单；这些数据不随仓库发布。首批24张卡片，用户点击加载更多后才创建下一批。缩略图由 IntersectionObserver 在进入可视区附近时设置 src/srcset，首屏不下载全部图片；浏览器保留原比例和多尺寸选择。首屏内嵌的目录字段是元数据，不能称作已下载PPT原件。

部署应保留云端现有标题、恢复图片和转换版本的合并结果，不用另一台电脑的旧索引直接覆盖。当前首次生产迁移使用了对应来源合并，后续生成流程仍需复用该对账步骤。
