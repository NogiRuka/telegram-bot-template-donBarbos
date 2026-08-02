fixtures/

开发调试用网页快照。

所有 HTML 均为浏览器保存的原始页面，用于：

- 离线开发 Parser
- AI 分析 DOM
- 单元测试
- 避免频繁请求目标网站

命名规则：

ck-download/
    detail/
        31839.html

如果以后一个影片有多个页面
例如
https://ck-download.com/product/detail/31839
https://ck-download.com/product/series/123
https://ck-download.com/product/actress/555
推荐命名规则：

ck-download/
    detail/
        31839.html
        31840.html

    series/
        123.html

    actress/
        555.html