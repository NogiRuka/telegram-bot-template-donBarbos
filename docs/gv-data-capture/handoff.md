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

### Fixture 字段值校对记录

| 来源 / fixture | 解析后的关键值 |
|---|---|
| `ko-video/KSUI028.html` | 番号 `KSUI028`；原标题 `ある変態リーマンの淫猥な日常 4`；发行日 `2023-03-24`；厂家 `KO`；标签 `SUITS`、`ストーリー`、`普通・スジ筋`、`筋肉・ガチムチ`；封面 `/upload/save_image/SUITS/KSUI028_DVD/KSUI028_DVD.jpg`。 |
| `trance-video/TO-07-0011-01.html` | 番号 `TO-07-0011-01`；原标题 `【独占配信】ワケアリ part11`；掲載日 `2017-05-26`；表格值 `00:25:24`、`1040MB`、`1920×1080pixel`、`最大5Mbps`；详情标签包含 `ワケアリ`、`目隠し`、`手コキ・フェラ`、`拘束`、`MORE`；封面 `/picture/parent/TO-07-0011-01-14_1.jpg`。 |
| `ko-tube/70-01-0035-01.html` | 番号 `70-01-0035-01`；厂家/レーベル `赤面男子`；プレイ `アナルSEX`、`手コキ・フェラ・アナル責め`；モデル `標準・ムッチリ`；无 DVD発売值。 |
| `ko-tube/KT-25389.html` | package 外部 ID `KT-25389`；DVD 番号 `81-02-0001`；原标题 `【monster】 MONSTER 巨根中毒`；厂家 `KO EAST`；レーベル `monster`；DVD発売 `2016-07-01`（HTML 只有 `2016年07月`，按月首日保存）；组成 product 为 `72780`、`72781`、`72782`，链接为 `/product/index2/{id}/`。 |
| `str8boys2023/SBM-0511.html` | 番号 `SBM-0511`；公开日 `2025-07-05`；レーベル `STR8 BOYS`；MODEL NAME `涼真-RYOMA-`；SERIES `THE FIRST TAKE`；PLAY LIST `手コキ・フェラ`；MODEL TYPE 八项标签；封面为 `images/SBM-0511/0s.jpg`。 |
