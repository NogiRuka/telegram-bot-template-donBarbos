# GV Data Capture 交接文档

更新时间：2026-08-12

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

