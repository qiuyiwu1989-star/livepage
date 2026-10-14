# Detail reader repair — 2026-10-14

The production detail pages now request media through the LivePage namespace. Hero images request HD directly; recommendation cards request bounded thumbnails. Reader requests time out after 12 seconds and playback readiness resolves even on failed association, avoiding an indefinite dependency wait. The controller URL is versioned to invalidate cached copies.

atom-0001 retains original title 核心问题: in the overlay and uses 产品定义：产品形态、功能集合与成本结构 as a source-text-based candidate pending human confirmation. This is not a claim that every title was reviewed.

Production probes: hero 200, 306614 bytes; recommendation thumbnail 200, 7145 bytes; course directory and removal status 200. JavaScript syntax validation passed on the server. Browser automation timed out; actual authenticated browser rendering and the user's pending-load symptom still require a browser recheck. These changes address identified route and failure-handling weaknesses, not a proven single root cause for all latency.

## 当前环境后续优化

当前页详情缓存复用，优先显示原图与翻页；课程目录和转换清单不阻塞首屏。JSON 请求12秒超时，快速切页用请求序号防旧响应覆盖。HTML重复点击不重设相同iframe URL，原图和HTML提供加载提示。脚本URL加入版本号。

验证：node tests/reader-loading.cjs 覆盖目录永不返回时原图仍启动、首条详情只请求一次、重复切HTML不重新请求。未代表真实浏览器性能和生产部署验收。

字体膨胀仍待转换管线处理：PDF样例第三页1,877,450字节，其中六份base64字体约1.63MB。保留原制品，不在本轮直接重写转换结果。
