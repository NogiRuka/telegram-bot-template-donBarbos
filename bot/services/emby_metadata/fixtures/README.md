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

快速准备目录
------------

不需要手动建立数据源、`search` 和 `detail` 目录，也不需要先手动创建 HTML 文件。只需传入数据源名、detail 名、search 名：

```bash
uv run python -m scripts.prepare_emby_fixture str8boys2023 GV-OAV1350 OAV135
```

命令会创建 `detail/GV-OAV1350.html` 和 `search/OAV135.html` 两个空文件，之后直接把浏览器保存的 HTML 内容放进去。名称可以自行带 `.html` 后缀；已有同名文件默认不会覆盖，确认要清空时加 `--overwrite`。

项目根目录还提供了简短包装命令：

```powershell
.\fix.ps1 str8boys2023
```

如果希望直接输入 `fix str8boys2023`，可在 PowerShell Profile 中注册一次：

```powershell
function fix { & "D:\Projects\Python\telegram-bot-template-donBarbos\fix.ps1" @args }
```
