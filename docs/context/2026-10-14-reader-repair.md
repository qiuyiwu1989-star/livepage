# Detail reader repair — 2026-10-14

The production detail pages now request media through the LivePage namespace. Hero images request HD directly; recommendation cards request bounded thumbnails. Reader requests time out after 12 seconds and playback readiness resolves even on failed association, avoiding an indefinite dependency wait. The controller URL is versioned to invalidate cached copies.

atom-0001 retains original title 核心问题: in the overlay and uses 产品定义：产品形态、功能集合与成本结构 as a source-text-based candidate pending human confirmation. This is not a claim that every title was reviewed.

Production probes: hero 200, 306614 bytes; recommendation thumbnail 200, 7145 bytes; course directory and removal status 200. JavaScript syntax validation passed on the server. Browser automation timed out; actual authenticated browser rendering and the user's pending-load symptom still require a browser recheck. These changes address identified route and failure-handling weaknesses, not a proven single root cause for all latency.
