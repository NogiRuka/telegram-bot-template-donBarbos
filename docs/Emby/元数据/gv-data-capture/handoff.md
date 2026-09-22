# GV Data Capture 交接文档

更新时间：2026-08-13

## 1. 本次完成内容

本次主要完成 Emby 元数据编辑页的演员与演员图片支持，并按照 UI 设计图调整交互：

- 当前 Emby 演员与候选演员保持左右分栏。
- 演员名称和演员图片作为同一张演员卡片展示，不再拆成两个独立模块。
- 当前演员卡片只读，显示 Emby 中已有的演员名称和图片。
- 候选演员卡片支持横向滚动，适合演员数量较多的情况。
- 候选演员卡片支持右上角 `×` 删除。
- 候选区域末尾提供“输入演员名字”和“添加演员”。
- 输入演员名称后可按回车或点击加号完成添加。
- 添加演员时保留 `type: Actor`，后续仍由现有候选数据和写入流程处理图片。
- 页面整体继续使用现有的“确认写入 Emby”，没有新增演员区域底部操作栏。
- 当前 Emby 演员图片地址由后端根据演员 `Id` 和 `PrimaryImageTag` 生成。
- 鼠标位于演员卡片区域滚动滚轮时，滚轮会转换为横向滚动。
- 候选演员图片位置可点击选择本地图片，图片以 Base64 写入该演员对象的 `image_data`。
- 演员没有图片时统一显示“无图片”。

## 2. 标题翻译规则

当前页面已经按以下逻辑处理标题翻译：

- “标题翻译”按钮位于“AI翻译”按钮前面。
- 点击“标题翻译”后，翻译候选标题。
- 翻译结果写入 `taglines`，对应页面的“宣传语”字段。
- `candidate.title` 保持原候选标题不变。
- 开启自动翻译时，同样只将标题翻译结果写入“宣传语”，不会修改标题。
- 简介的“AI翻译”仍按原有逻辑写入简介翻译结果和原文组合值。

## 3. 涉及文件

### 前端

`web/src/features/emby-metadata/index.tsx`

- 增加演员卡片和横向滚动容器。
- 增加当前演员数据规范化处理。
- 将 `People` 字段接入独立的演员编辑器。
- 支持候选演员删除和添加。
- 支持点击候选演员图片位置上传本地图片。
- 支持演员区域滚轮横向滚动。
- 保持当前值与候选值的两列布局。

`web/src/lib/api.ts`

- 增加 `MetadataPerson` 类型。
- 为演员类型补充角色、类型、图片来源等字段。
- 将 `MetadataCandidate.people` 类型改为 `MetadataPerson[]`。

### 后端

`bot/services/emby_metadata/workbench.py`

- 增加当前 Emby 演员图片 URL 生成逻辑。
- 只在工作台响应中补充 `ImageUrl`，不修改写入流程使用的原始 Emby 快照。

演员图片实际写入流程位于：

`bot/services/emby_metadata/writer.py`

该流程会在演员写入 Emby 后，根据候选演员的图片来源上传演员主图。

## 4. 数据流

```text
Emby People
    -> 后端返回当前演员及 ImageUrl
    -> 前端左侧当前演员卡片

候选数据源 People
    -> 前端右侧候选演员卡片
    -> 用户删除/添加
    -> candidate.people
    -> 确认写入 Emby
    -> Emby People 更新及演员图片上传
```

## 5. 验证结果

已执行：

```powershell
cd web
pnpm build
```

结果：前端构建通过。Vite 只输出已有的 chunk 体积提示，没有阻断错误。

已执行：

```powershell
python -m compileall -q bot/services/emby_metadata
```

结果：后端相关 Python 文件编译通过。

## 6. 后续联调重点

1. 使用真实 Emby 数据验证 `People` 中是否包含 `Id` 和 `PrimaryImageTag`。
2. 验证当前演员图片接口是否能正常访问，尤其是 API Key 和反向代理场景。
3. 验证候选数据源是否提供 `image_url`；没有图片来源时，卡片会显示占位图，但演员仍可写入。
4. 验证删除全部候选演员后写入 Emby 的行为是否符合预期。
5. 验证新增演员没有图片时，Emby 是否保留为空图片，不影响演员名称写入。
6. 使用真实演员图片执行一次完整写入，确认 Emby 中演员主图上传成功。

## 7. 当前工作区状态

本次修改尚未提交 Git，涉及以下文件：

- `bot/services/emby_metadata/workbench.py`
- `web/src/features/emby-metadata/index.tsx`
- `web/src/lib/api.ts`

## 8. 最新交互更新（2026-08-12）

- 元数据编辑区域顶部的三个 Tab 已移除，基本信息直接展示。
- 待处理列表已缩窄，元数据编辑区域加宽；字段列保持原宽度，当前 Emby 值和候选值列使用更多空间。
- “刷新队列”增加刷新中状态及成功/失败提示。
- “抓取封面”区域支持点击上传本地封面；上传图片以 Base64 保存到候选数据，并在写入 Emby 时优先使用。
- 标题翻译使用原标题，并会去除开头的 `【…】` 前缀后再翻译，不翻译该前缀。
- 当前 Emby 演员只读；候选演员名称支持直接编辑，名称下方使用实线提示可编辑。
- 新增演员如果与当前 Emby 演员同名，会自动复用当前 Emby 演员图片。
- 候选演员删除按钮默认隐藏，鼠标移入演员卡片或键盘聚焦时显示。
- 添加演员卡片已更新为渐变背景、虚线边框和悬停效果。
- 元数据图片支持鼠标悬浮显示大图预览，预览显示在原图片旁边；无遮罩、无阴影，空间不足时自动切换到另一侧。

## 9. Koshop 与 CK 元数据合并（2026-08-12）

- Koshop 详情页的 `キーワード` 已解析并加入标签，和 `モデルタイプ`、`シリーズ` 一起去重。
- 选择 Koshop 候选后，系统会使用 Koshop 原标题自动搜索 CK 补充结果。
- 选择 CK 结果后，Koshop 保留为主来源；CK 的标签、演员、类型、工作室等信息会合并补充，不覆盖 Koshop 番号和标题。
- 合并结果会保留两个来源的 Provider ID，方便后续追溯。

## 10. ACCEED 数据源（2026-08-12）

- 新增 `acceed` 日韩数据源，支持 `/search.php?s=...` 搜索和 `/detail.{番号}.html` 详情抓取。
- 支持解析标题、番号、发行日期、封面、出演模型及模型/作品标签。
- `acceed` 已注册到元数据工作台的日韩数据源列表。

## 11. 最新修复（2026-08-13）

- Koshop 封面和演员图片写入 Emby 时关闭该站点的 SSL 证书校验，避免本地环境出现 `CERTIFICATE_VERIFY_FAILED`。
- 标题自动翻译只使用 `original_title`，不包含番号；最终标题仍保持“番号 + 原标题”。
- 自动翻译简介开关恢复到“确认写入 Emby”底部操作栏左侧，并恢复原来的 Button 样式。
- 删除覆盖模式界面和请求参数，写入统一使用固定覆盖逻辑。
- 恢复 `EditorPanel` 兼容导出，避免前端懒加载模块出现导出不存在错误。

## 12. 数据源解析与番号路由更新（2026-08-13）

- 新增 `boy-studio` 日韩数据源，并注册到元数据工作台。
- `boy-studio` 默认使用标题搜索，不使用番号搜索；详情页从 `品番` 解析番号。
- `boy-studio` 的 `レーベル` 映射为工作室，`ジャンル` 和 `シリーズ` 映射为标签，类型保持为空。
- `boy-studio` 简介会过滤订阅价格及购买方式提示，例如 `サブスク会員`、`通常価格` 等商业说明。
- `BOY-` 开头的番号默认使用 `boy-studio` 数据源；`BWB` 开头的番号默认使用 `ko-shop` 数据源。
- `boy-studio` 请求使用浏览器兼容请求头，降低站点返回 HTTP 503 的概率。
- ACCEED 详情标题会移除标题区域中的“お気に入りに追加”按钮文本；搜索结果封面地址会清理首尾空白。
- CK-Download 简介会过滤“ストリーミング再生のみ”提示，产品番号末尾的 `-HD` 会被移除。
- Koshop 详情页的 `シリーズ` 会加入标签，并与 `モデルタイプ`、`キーワード` 一起去重。

## 13. 新增四个日韩数据源（2026-08-13）

- 新增并注册 `ko-video`、`trance-video`、`ko-tube`、`str8boys2023`，分别位于 `parser/ko_video.py`、`parser/trance_video.py`、`parser/ko_tube.py`、`parser/str8boys2023.py` 与对应的 `sources/` 文件。
- 所有详情候选都保留 `parse_report.source_html_fields`，用于按 fixture 逐字段复核；没有在 HTML 中出现的字段保持为空，不用猜测值。
- `ko-video`：详情 `h2` 为原标题；`商品発売日` 为发行日期；`メーカー/レーベル` 的厂家写入 Studios；`シリーズ/ジャンル` 与 `モデル` 写入 Tags；`*_DVD.jpg` 为封面。
- `trance-video`：详情表格中的 `作品ID`、`掲載日`、标题和图片按页面值解析；`label`/`play_type` 链接写入 Tags。
- `str8boys2023`：`品番`、`公開日`、`レーベル`、`MODEL NAME`、`SERIES`、`PLAY LIST`、`MODEL TYPE` 分别映射为番号、日期、工作室、演员和标签；封面优先 `images/{番号}/0s.jpg`。
- `ko-tube`：普通 product 直接使用 `/product/index/{id}`；`KT-25389` 是 package 的外部番号，必须直接请求 `/package/index/25389`，不能拿 `KT-25389` 去搜索。package 详情通过封面 `81-02-0001_C.jpg` 得到 DVD 番号 `81-02-0001`，并在 `parse_report.child_product_links` 保留 `/product/index2/72780/` 等组成 product 链接。
- `ko-tube` product 详情的番号来自 `作品番号`；メーカー写入 Studios；プレイ和モデル写入 Tags。package 的标题、厂家、レーベル、DVD発売和组成 product 链接按 package HTML 保留。

## 14. 本次校对范围与限制

- 已按 `fixtures/日韩/{ko-video,trance-video,ko-tube,str8boys2023}/` 中的 search/detail HTML 对 selector 和字段映射逐项核对。
- 本次按要求未运行测试；后续接入真实站点时应单独确认搜索参数、重定向和站点访问策略，不要把 fixture 解析通过当成线上可用性证明。
- `str8boys2023` 实站搜索使用官网实际请求 `/Store/list.php?keywords=...`；结果链接从 `detail.php` 的 `keywords` 查询参数提取番号。
- `ko-video` 实站搜索参数名是 `name`，请求格式为 `/products/list.php?name=...`。
- `ko-tube` 实站搜索使用 `/search/index?kw=...&sk=0&x=10&y=16`，并跟随 302 到 `/search/result/keep:1`。
- `trance-video` 实站搜索必须先请求 `/product/search?keyword=...` 并跟随 302 到 `/product/result`，再解析最终 HTML。
- `trance-video` 搜索结果只解析 `.title_list > li` 作品卡片，标题只取卡片 `h4`；不能扫描页面所有 `product/detail` 链接，否则会混入排行榜并把日期、价格拼进标题。
- `ko-video` 与 `ko-tube` 仅在各自 source 内使用 `TCPConnector(ssl=False)` 兼容当前站点证书链；不得把关闭证书校验扩展到全局请求或其他数据源。
- 四个新数据源的搜索结果必须填写 `MetadataSearchResult.image_urls`；ko-tube 和 str8boys2023 需从作品卡片的 `li` 容器取图，不能只从标题链接取图。
- ko-tube 搜索结果只解析 `.title_list > li` 和卡片 `h4`，避免把价格、导航或其他推荐作品混入标题和结果。
- `/api/emby/metadata/images` 图片代理必须按图片 URL 的站点选择对应 source 的 `image_headers` 和 SSL 策略；不能统一使用 `CkDownloadSource` 的请求头。ko-video、ko-tube 的图片请求也要在代理阶段保持证书兼容设置。

## 15. 新数据源适配标准流程（后续对话按此执行）

### 15.1 开始前：确认范围与证据

1. 先确认数据源名称、所属媒体库分类、官方搜索 URL、详情 URL、图片 URL 和特殊番号规则。
2. 优先使用用户提供的真实浏览器 Network 记录；必须记录请求方法、最终 URL、302 跳转、POST 表单字段、必要 Cookie/Referer 和响应页面结构。
3. 先检查 `fixtures/日韩/<source>/search` 与 `detail`。fixture 是字段和 selector 的证据，不得凭其他站点经验猜字段。

### 15.2 文件结构：来源规则独立，基础能力复用

- HTML 解析仍放在 `bot/services/emby_metadata/parser/<source>.py`，网络流程仍放在 `bot/services/emby_metadata/sources/<source>.py`。
- 每个 source 只实现本站 selector、字段映射、URL、请求方法、表单、Cookie/Referer、SSL、号码和页面层级差异。
- 文本清洗、多行简介、绝对图片 URL、价格/日期、去重、HTTP Session、超时、重试和错误转换必须集中在 `parser/base.py` 或 `sources/base.py`，不得在每个 source 复制。
- 不创建会按来源名称分支的 `catalog_sources.py` 或 `_catalog_shared.py`；公共代码必须按职责命名、显式传入配置，不得猜测任意站点规则。
- 在 `sources/__init__.py`、`workbench.py` 和必要的前端 source 注册处分别注册。

### 15.3 Parser 实现顺序

1. 先解析搜索结果：`source_id` 必须能用于详情请求，`title` 只取作品标题节点，不能把日期、价格、导航或推荐区文本拼进去。
2. 搜索结果必须填写 `image_urls`；图片从作品卡片容器读取，兼容 `src`、`data-src`、`data-original` 等懒加载属性，并用 `urljoin` 转成绝对 URL。
3. 再解析详情字段：番号、原标题、日期、厂家/工作室、标签、演员、简介、图片分别映射到统一模型；HTML 没有的字段保持空值。
4. 详情必须保留 `parse_report.source_html_fields`，必要时增加页面层级、子作品链接、原始字段等回溯信息。
5. 封面必须明确选择规则（例如固定 `_1.jpg`、`_DVD.jpg`、卡片首图），不能只依赖页面第一张任意图片。

### 15.4 Source 请求实现

- 按官网真实流程实现 GET、POST、302 和最终结果页；不要把需要会话状态的跳转页改成无状态直连。
- POST 表单字段必须使用官网 HTML 中的真实 name/value，例如 ko-tube 的 `data[Search][keyword]`、`data[Search][ex_keyword]`、`data[Search][search_option1]`。
- `aiohttp` 请求必须保留合理 User-Agent，并在同一请求流程中保持 Session/Cookie。
- 证书兼容只能限定在明确有证书链问题的独立 source；禁止修改全局 SSL 校验，也不要让其他数据源继承 `ssl=False`。
- 真实站点搜索和 fixture 解析是两种检查：fixture 通过不代表线上 URL、跳转、图片和证书可用。

### 15.5 特殊番号与多层页面

- 如果番号前缀代表外部 package/DVD，必须在 `_source_for_product_number` 中直接路由，不能把外部番号拿去普通搜索。
- package、product、product/index2 等页面必须分别处理；从 package 提取 DVD 番号和子 product 链接，不把 package 错当成单一 product。
- 详情 URL、`source_id`、`product_number`、`external_ids` 必须区分：站内数字 ID 用于详情请求，页面展示番号用于媒体标题和 ProviderId。

### 15.6 交付前检查

- 检查四个独立 parser/source 文件是否存在，且没有共享数据源文件或残留引用。
- 用每个 source 的 fixture 抽样打印：`source_id`、标题、日期、工作室、标签、演员、封面 URL 和 `parse_report`。
- 做语法、导入和 `git diff --check` 检查；除非用户明确要求，不运行测试套件。
- 更新本 handoff 和 `任务清单.md`，记录已验证的请求方法、参数、跳转、selector、图片规则和未完成的线上联调项。

## 17. 后续修正记录（2026-08-15）

- ck-download 已移除 source 到 parser 的兼容入口；HTML fixture 和 parser 测试直接调用 `CkDownloadParser`，`CkDownloadSource` 只保留 POST/GET 请求、Cookie、重试、图片请求头和异常转换。新增或修改的注释、docstring 和错误说明统一使用中文。
- `sources/base.py` 已提供 `HttpMetadataSource`：集中管理超时、CookieManager、请求头、GET/POST、302、SSL、重试、HTTP/网络异常和图片请求头。ck-download 作为首个接入来源，只声明 `cookie_key`、请求头、POST 搜索表单和详情路径；后续来源按相同边界迁移。
- 已迁移 `acceed`、`boy-studio`、`hunk-ch`、`jgvdata`、`ko-shop`、`mensrush`、`ko-video`、`ko-tube`、`str8boys2023`、`trance-video`。各 source 只保留本站 URL、表单、浏览器请求头、Cookie 标识、SSL 与跳转差异；不再保留重复 `_request` 或 source 到 parser 的转发入口。
- 追加回归修正：`ko-tube` 演员实际位于 `#model_list li h6`，图片位于同一条目的 `img`，不能从演员链接文本读取；`ko-video` 搜索兼容正式作品链接的通用选择器，避免因列表容器 class 变化返回空结果。
- 四个新数据源保留各自 parser/source 文件；公共能力依照 [数据源开发规范](数据源开发规范.md) 收敛到职责明确的基础层，不再复制解析或请求样板代码。
- `ko-video` 搜索只读取 `.item_list_last > li` 正式作品卡片；详情页演员读取 `.model_performance a` 的 `span` 和 `img`，`MetadataPerson.image_url` 必须保存绝对地址，并使用详情页作为 Referer 下载。若页面已有出演模型，不再把简介中的 CAST 重复追加为演员。
- `ko-tube` 搜索只读取 `.title_list > li`，价格从 `.price li.gold`（无该节点时可回退 `.reg`）解析为 `price_yen`，卡片图片从卡片容器读取。`KT-` 号码仍然直接定位 package，不经过搜索；package 的 `81-02-0001_C.jpg` 用于 DVD 番号和封面识别，子 product 链接写入 `parse_report.child_product_links`。
- `ko-tube` 详情页价格分别兼容 `.single_price .price .gold` 和 `.pack_price .price .gold`；简介兼容 `.intro_text` 以及 package 的 `.sub_data > p:not(.dousa)`，保留 `<br>`/块级换行，不得用单个空格压成一整段。
- `trance-video` 搜索流程必须保留 `/product/search?keyword=...` 到 `/product/result` 的 302 会话跳转；结果只解析作品卡片 `h4`，详情厂家/标签按 `.prod_category > li` 的 `strong` 分组读取，标签仅允许“レーベル”和“カテゴリ”，明确过滤 `MORE` 等推荐区文本。
- `str8boys2023` 搜索结果卡片是 `li.thumbox`，标题从 `.id-title a`、番号从详情链接 `keywords`、价格从 `.textblock`、图片从 `.photoblock img.ListThumImg01` 读取；详情价格从 `.detail-price-checkbox .Price` 读取，简介保留页面换行。
- 四个数据源的搜索结果都必须填写绝对 `image_urls`，详情封面 URL 也必须去除首尾空白并转换为绝对 URL；图片代理根据域名选择对应 source 的请求头和 SSL 策略。
- 本次仅做 fixture parser 抽样、`py_compile` 和 `git diff --check`；这些检查不等同于真实站点搜索、302/POST、SSL 和图片代理的线上联调。

## 16. 四个后加数据源字段复核结论（2026-08-14）

- `trance-video`：简介来自 `.intro_text`；工作室来自 `.prod_category` 中“メーカー”；标签只来自 `.prod_category` 的 `label`/`play_type` 链接，因此排除“MORE”等相关推荐链接；详情价格取 `.detail_page .price strong`。
- `ko-video`：简介来自 `.deitail_txt`；演员来自 `.model_performance a span`，并补充简介 `CAST` 行中的演员；`メーカー/レーベル` 的厂家写入 Studios，レーベル与シリーズ/ジャンル、モデル一起写入 Tags。
- `ko-tube`：简介优先 `.intro_text`，package 使用 `.sub_data > p:not(.dousa)`；日期取 `.base_data .date` 或 `.pack_data .date`，DVD発売仍保留页面原值；价格取 `.single_price` 或 `.pack_price` 的 gold price；メーカー写入 Studios，レーベル加入 Tags；可见 `#model_list` 演员写入 People。
- `str8boys2023`：简介来自 `.detailtextblock .cp_container p`；`品番`、`公開日`、レーベル、MODEL NAME、SERIES、PLAY LIST、MODEL TYPE 继续按详情字段映射。
- 统一新增 `MetadataCandidate.price_yen` 保存详情页价格/点数；该字段只用于候选回报和人工校对，不写入 Emby 的标准元数据字段。

### 16.1 本次 fixture 抽样结果

| 来源 | 关键修正后的值 |
|---|---|
| `trance-video/TO-07-0011-01.html` | 简介已解析；工作室 `TRANCE ORIGINAL`；标签 `ワケアリ`、`目隠し`、`手コキ・フェラ`、`拘束`；不再包含 `MORE`；价格 `980`。 |
| `ko-video/KSUI028.html` | 简介已解析；演员包含出演模型和 CAST；工作室 `KO`；标签包含 `SUITS`、`ストーリー`、`普通・スジ筋`、`筋肉・ガチムチ`。 |
| `ko-tube/70-01-0035-01.html` | 简介已解析；日期 `2026-07-02`；价格 `1980`；工作室/レーベル `赤面男子`；プレイ和モデル已进入标签。 |
| `ko-tube/KT-25389.html` | package 简介已解析；日期 `2016-07-01`（页面日期 `2016.07.07`，DVD発売仍为 `2016年07月`）；价格 `8250`；工作室 `KO EAST`；标签包含 `monster`；子 product 链接保留。 |
| `str8boys2023/SBM-0511.html` | 简介已解析；日期、工作室、演员和标签继续按 fixture 值解析。 |

### Fixture 字段值校对记录

| 来源 / fixture | 解析后的关键值 |
|---|---|
| `ko-video/KSUI028.html` | 番号 `KSUI028`；原标题 `ある変態リーマンの淫猥な日常 4`；发行日 `2023-03-24`；厂家 `KO`；标签 `SUITS`、`ストーリー`、`普通・スジ筋`、`筋肉・ガチムチ`；封面 `/upload/save_image/SUITS/KSUI028_DVD/KSUI028_DVD.jpg`。 |
| `trance-video/TO-07-0011-01.html` | 番号 `TO-07-0011-01`；原标题 `【独占配信】ワケアリ part11`；掲載日 `2017-05-26`；表格值 `00:25:24`、`1040MB`、`1920×1080pixel`、`最大5Mbps`；详情标签包含 `ワケアリ`、`目隠し`、`手コキ・フェラ`、`拘束`、`MORE`；封面 `/picture/parent/TO-07-0011-01-14_1.jpg`。 |
| `ko-tube/70-01-0035-01.html` | 番号 `70-01-0035-01`；厂家/レーベル `赤面男子`；プレイ `アナルSEX`、`手コキ・フェラ・アナル責め`；モデル `標準・ムッチリ`；无 DVD発売值。 |
| `ko-tube/KT-25389.html` | package 外部 ID `KT-25389`；DVD 番号 `81-02-0001`；原标题 `【monster】 MONSTER 巨根中毒`；厂家 `KO EAST`；レーベル `monster`；DVD発売 `2016-07-01`（HTML 只有 `2016年07月`，按月首日保存）；组成 product 为 `72780`、`72781`、`72782`，链接为 `/product/index2/{id}/`。 |
| `str8boys2023/SBM-0511.html` | 番号 `SBM-0511`；公开日 `2025-07-05`；レーベル `STR8 BOYS`；MODEL NAME `涼真-RYOMA-`；SERIES `THE FIRST TAKE`；PLAY LIST `手コキ・フェラ`；MODEL TYPE 八项标签；封面为 `images/SBM-0511/0s.jpg`。 |
