import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Check, CircleHelp, Database, ExternalLink, RefreshCw, Search, Sparkles, Upload, X } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { apiClient, type MetadataCandidate, type MetadataQueueItem, type MetadataSearchResult } from '@/lib/api'

const fields = [
  ['Name', '名称'], ['OriginalTitle', '原标题'], ['Taglines', '宣传语'], ['Overview', '简介'],
  ['ProductionYear', '年份'], ['PremiereDate', '上映日期'], ['Genres', '类型'], ['Studios', '工作室'],
  ['People', '演员'], ['Tags', '标签'], ['CommunityRating', '社区评分'], ['OfficialRating', '家长评级'],
  ['CustomRating', '自定义评分'],
] as const

type FieldKey = typeof fields[number][0]
type Routing = { category: string; source: string }
const collectionFields = new Set<FieldKey>(['Genres', 'Studios', 'People', 'Tags'])

function candidateValues(candidate: MetadataCandidate): Record<FieldKey, string> {
  const join = (items: Array<{ name: string }>) => items.map((item) => item.name).join('、')
  return {
    Name: candidate.title, OriginalTitle: candidate.original_title, Taglines: candidate.taglines ?? '',
    Overview: candidate.overview ?? '', ProductionYear: candidate.year ? String(candidate.year) : '',
    PremiereDate: candidate.release_date ?? '', Genres: join(candidate.genres), Studios: join(candidate.studios),
    People: join(candidate.people), Tags: join(candidate.tags),
    CommunityRating: candidate.community_rating === undefined ? '' : String(candidate.community_rating),
    OfficialRating: candidate.official_rating ?? '', CustomRating: candidate.custom_rating ?? '',
  }
}

function updateCandidate(candidate: MetadataCandidate, field: FieldKey, value: string): MetadataCandidate {
  const items = value.split(/[、,，]/).map((name) => name.trim()).filter(Boolean).map((name) => ({ name }))
  if (field === 'Name') return { ...candidate, title: value }
  if (field === 'OriginalTitle') return { ...candidate, original_title: value }
  if (field === 'Taglines') return { ...candidate, taglines: value }
  if (field === 'Overview') return { ...candidate, overview: value }
  if (field === 'ProductionYear') return { ...candidate, year: Number(value) || undefined }
  if (field === 'PremiereDate') return { ...candidate, release_date: value }
  if (field === 'CommunityRating') return { ...candidate, community_rating: Number(value) || undefined }
  if (field === 'OfficialRating') return { ...candidate, official_rating: value }
  if (field === 'CustomRating') return { ...candidate, custom_rating: value }
  if (field === 'Genres') return { ...candidate, genres: items }
  if (field === 'Studios') return { ...candidate, studios: items }
  if (field === 'People') return { ...candidate, people: items }
  if (field === 'Tags') return { ...candidate, tags: items }
  return candidate
}

function ValueChips({ value }: { value: string }) {
  const values = value.split(/[、,，]/).map((item) => item.trim()).filter(Boolean)
  return <div className='flex max-h-20 flex-wrap content-start gap-1 overflow-y-auto'>
    {values.length ? values.map((item, index) => <span key={`${item}-${index}`} className='rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700'>{item}</span>) : <span className='text-sm text-slate-400'>—</span>}
  </div>
}

function CoverPreview({ candidate }: { candidate: MetadataCandidate }) {
  const currentImageUrl = candidate.current_image_url ?? null
  return <div className='mb-4 flex items-center gap-4 rounded-lg border bg-slate-50 p-3'>
    <div className='min-w-0 flex-1'><b className='mb-2 block text-sm'>当前 Emby 封面</b><div className='flex h-28 items-center justify-center overflow-hidden rounded bg-slate-200'>{currentImageUrl ? <img src={currentImageUrl} alt='当前 Emby 封面' className='size-full object-contain' /> : <Database className='size-7 text-slate-400' />}</div></div>
    <div className='min-w-0 flex-1'><b className='mb-2 block text-sm'>抓取封面</b><div className='flex h-28 items-center justify-center overflow-hidden rounded bg-slate-200'>{candidate.poster_url ? <img src={apiClient.metadataImageUrl(candidate.poster_url, candidate.raw_url)} alt='抓取封面' className='size-full object-contain' /> : <Database className='size-7 text-slate-400' />}</div></div>
  </div>
}

export function EmbyMetadataWorkspace() {
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [resultsByItem, setResultsByItem] = useState<Record<string, MetadataSearchResult[]>>({})
  const [candidate, setCandidate] = useState<MetadataCandidate | null>(null)
  const [beforeItem, setBeforeItem] = useState<Record<string, unknown>>({})
  const [selectedResult, setSelectedResult] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [fieldSelection, setFieldSelection] = useState<string[]>(fields.map(([key]) => key))
  const [overwrite, setOverwrite] = useState(false)
  const [statusFilter, setStatusFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [searchKeywords, setSearchKeywords] = useState<Record<string, string>>({})
  const [routing, setRouting] = useState<Record<string, Routing>>({})

  const queueQuery = useQuery({ queryKey: ['emby-metadata-queue'], queryFn: () => apiClient.getMetadataQueue() })
  const items = queueQuery.data?.items ?? []
  const active = items.find((item) => item.notification_id === activeId) ?? items[0]
  const results = active ? resultsByItem[active.notification_id] ?? [] : []
  const visibleItems = useMemo(() => items.filter((item) =>
    (statusFilter === 'all' || item.status === statusFilter) &&
    (categoryFilter === 'all' || item.category === categoryFilter) &&
    (!query || item.item_name.toLowerCase().includes(query.toLowerCase())),
  ), [items, query, statusFilter, categoryFilter])

  const routeFor = (item: MetadataQueueItem): Routing => routing[item.notification_id] ?? { category: item.category, source: item.source }
  const toggle = (id: string) => setSelectedIds((ids) => ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id])
  const clearActive = () => { setCandidate(null); setSelectedResult(null); setBeforeItem({}) }

  const searchSelected = async () => {
    if (!selectedIds.length) return toast.error('请先勾选要搜索的项目')
    const selections = selectedIds.map((notification_id) => {
      const item = items.find((value) => value.notification_id === notification_id)!
      const route = routeFor(item)
      return { notification_id, keyword: searchKeywords[notification_id] ?? item.search_keyword ?? '', ...route }
    })
    if (selections.some((item) => !item.source)) return toast.error('所选分类尚未配置数据源')
    try {
      const response = await apiClient.searchMetadataQueue(selections)
      const current = response.find((item) => item.notification_id === (activeId ?? selectedIds[0])) ?? response[0]
      setActiveId(current.notification_id)
      setResultsByItem((previous) => ({ ...previous, ...Object.fromEntries(response.map((item) => [item.notification_id, item.results])) }))
      clearActive()
    } catch (error) { toast.error(error instanceof Error ? error.message : '搜索失败') }
  }

  const selectCandidate = async (result: MetadataSearchResult) => {
    if (!active) return
    setSelectedResult(result.source_id)
    try {
      const response = await apiClient.getMetadataCandidate(active.notification_id, result.source, result.source_id)
      setCandidate(response.candidate); setBeforeItem(response.before_item)
    } catch (error) { toast.error(error instanceof Error ? error.message : '获取详情失败') }
  }

  const writeback = async () => {
    if (!active || !candidate) return toast.error('请先选择候选结果')
    try { await apiClient.writebackMetadata(active.notification_id, { candidate, fields: fieldSelection, overwrite, confirmed: true }); toast.success('元数据已写入 Emby'); void queueQuery.refetch() }
    catch (error) { toast.error(error instanceof Error ? error.message : '写入失败') }
  }

  return <main className='flex min-h-screen flex-col bg-slate-50 text-slate-800'>
    <header className='flex items-start justify-between border-b bg-white px-6 py-4'><div><h1 className='flex items-center gap-2 text-2xl font-bold'>Emby 元数据工作台 <Sparkles className='size-6 text-amber-500' /></h1><p className='mt-1 text-sm text-slate-500'>批量搜索、候选对比与写入 Emby</p></div><div className='flex items-center gap-3'><div className='rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700'><Check className='mr-1 inline size-4' />Emby 连接正常</div><Button variant='outline' onClick={() => void queueQuery.refetch()}><RefreshCw className='size-4' />刷新队列</Button></div></header>
    <section className='mx-5 mt-3 flex items-center gap-3 rounded-lg border bg-white p-2'><Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className='w-32'><SelectValue placeholder='全部状态' /></SelectTrigger><SelectContent><SelectItem value='all'>全部状态</SelectItem><SelectItem value='pending'>待搜索</SelectItem><SelectItem value='fetched'>已抓取</SelectItem></SelectContent></Select><Select value={categoryFilter} onValueChange={setCategoryFilter}><SelectTrigger className='w-32'><SelectValue placeholder='全部分类' /></SelectTrigger><SelectContent><SelectItem value='all'>全部分类</SelectItem><SelectItem value='japanese_korean'>日语动漫</SelectItem><SelectItem value='domestic'>国产</SelectItem><SelectItem value='western'>欧美</SelectItem></SelectContent></Select><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder='搜索词 / 番号 / 名称' className='max-w-sm' /><Button variant='outline' onClick={() => setQuery('')}><X className='size-4' />清空</Button></section>
    <section className='grid h-[calc(100vh-158px)] min-h-0 grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)_minmax(0,1.15fr)] gap-2 overflow-hidden px-5 py-2'>
      <QueuePanel items={items} visibleItems={visibleItems} active={active} selectedIds={selectedIds} routeFor={routeFor} searchKeywords={searchKeywords} setSearchKeywords={setSearchKeywords} setRouting={setRouting} setActiveId={(id) => { setActiveId(id); clearActive() }} toggle={toggle} searchSelected={searchSelected} setSelectedIds={setSelectedIds} />
      <ResultPanel results={results} active={active} selectedResult={selectedResult} selectCandidate={selectCandidate} clearResults={() => active && setResultsByItem((current) => ({ ...current, [active.notification_id]: [] }))} />
      <EditorPanel candidate={candidate} beforeItem={beforeItem} fieldSelection={fieldSelection} setFieldSelection={setFieldSelection} overwrite={overwrite} setOverwrite={setOverwrite} setCandidate={setCandidate} writeback={writeback} />
    </section>
  </main>
}

function QueuePanel({ items, visibleItems, active, selectedIds, routeFor, searchKeywords, setSearchKeywords, setRouting, setActiveId, toggle, searchSelected, setSelectedIds }: { items: MetadataQueueItem[]; visibleItems: MetadataQueueItem[]; active?: MetadataQueueItem; selectedIds: string[]; routeFor: (item: MetadataQueueItem) => Routing; searchKeywords: Record<string, string>; setSearchKeywords: (value: (current: Record<string, string>) => Record<string, string>) => void; setRouting: (value: (current: Record<string, Routing>) => Record<string, Routing>) => void; setActiveId: (id: string) => void; toggle: (id: string) => void; searchSelected: () => void; setSelectedIds: (ids: string[]) => void }) {
  return <div className='flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-white'><div className='flex justify-between border-b px-4 py-3'><b>待处理列表</b><span className='text-sm text-slate-500'>共 {items.length} 条</span></div><div className='grid grid-cols-[36px_minmax(0,1fr)_minmax(170px,.75fr)] items-center gap-2 border-b bg-slate-50 px-3 py-2 text-xs text-slate-500'><Checkbox className='justify-self-center' checked={!!items.length && selectedIds.length === items.length} onCheckedChange={() => setSelectedIds(selectedIds.length === items.length ? [] : items.map((item) => item.notification_id))} /><span>项目</span><span>搜索与数据源</span></div><div className='min-h-0 flex-1 overflow-y-auto overflow-x-hidden'>{visibleItems.map((item) => { const route = routeFor(item); const sourceOptions = item.source_options_by_category[route.category] ?? []; return <div role='button' tabIndex={0} key={item.notification_id} onClick={() => setActiveId(item.notification_id)} className={`relative grid grid-cols-[36px_minmax(0,1fr)_minmax(170px,.75fr)] items-center gap-2 border-b px-3 py-3 text-left ${active?.notification_id === item.notification_id ? 'bg-blue-50' : ''}`}><Checkbox className='justify-self-center' checked={selectedIds.includes(item.notification_id)} onClick={(event) => event.stopPropagation()} onCheckedChange={() => toggle(item.notification_id)} /><div className='flex min-w-0 items-center gap-3'>{item.image_url ? <img src={item.image_url} alt='' className='h-16 w-28 shrink-0 rounded object-cover' /> : <div className='flex h-16 w-28 shrink-0 items-center justify-center rounded bg-slate-100'><Database className='size-5 text-slate-400' /></div>}<div className='min-w-0'><button type='button' className='rounded bg-slate-100 px-1.5 py-0.5 text-[11px]' onClick={(event) => { event.stopPropagation(); void navigator.clipboard.writeText(item.item_id); toast.success(`已复制 Item ID：${item.item_id}`) }}>{item.item_id}</button><span className='mt-1 block line-clamp-3 text-sm font-medium' title={item.item_name}>{item.item_name}</span></div></div><div className='space-y-1 pr-12' onClick={(event) => event.stopPropagation()}><Input className='h-7' value={searchKeywords[item.notification_id] ?? item.search_keyword ?? ''} onChange={(event) => setSearchKeywords((current) => ({ ...current, [item.notification_id]: event.target.value }))} /><div className='flex gap-1'><Select value={route.category} onValueChange={(category) => setRouting((current) => ({ ...current, [item.notification_id]: { category, source: (item.source_options_by_category[category] ?? [])[0]?.value ?? '' } }))}><SelectTrigger className='h-7 min-w-0 flex-1 text-xs'><SelectValue /></SelectTrigger><SelectContent>{item.category_options.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent></Select><Select value={route.source || undefined} disabled={!sourceOptions.length} onValueChange={(source) => setRouting((current) => ({ ...current, [item.notification_id]: { ...route, source } }))}><SelectTrigger className='h-7 min-w-0 flex-1 text-xs'><SelectValue placeholder='未配置数据源' /></SelectTrigger><SelectContent>{sourceOptions.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent></Select></div></div><Status value={item.status} /></div> })}</div><div className='flex gap-2 border-t p-3'><span className='mr-auto text-sm text-blue-600'>已选择 {selectedIds.length} 项</span><Button onClick={searchSelected}><Search className='size-4' />批量搜索</Button><Button variant='outline' onClick={() => setSelectedIds([])}>取消选择</Button></div></div>
}

function ResultPanel({ results, active, selectedResult, selectCandidate, clearResults }: { results: MetadataSearchResult[]; active?: MetadataQueueItem; selectedResult: string | null; selectCandidate: (result: MetadataSearchResult) => void; clearResults: () => void }) {
  return <div className='flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-white'><div className='flex justify-between border-b px-4 py-3'><b>搜索结果</b><Button size='icon' variant='ghost' onClick={clearResults}><X className='size-4' /></Button></div><div className='min-h-0 flex-1 space-y-2 overflow-y-auto p-3'>{results.length ? results.map((result) => <div key={`${result.source}-${result.source_id}`} className='flex items-center gap-3 rounded-lg border p-3'><div className='flex h-24 w-40 shrink-0 items-center justify-center overflow-hidden rounded bg-slate-100'>{result.image_urls[0] ? <img src={apiClient.metadataImageUrl(result.image_urls[0], result.detail_url)} alt='' className='size-full object-contain' /> : <Database className='size-6 text-slate-400' />}</div><div className='min-w-0 flex-1'><b className='line-clamp-2 text-sm'>{result.title}</b><p className='mt-1 text-xs text-slate-500'>{result.release_date ?? '日期未知'} · {result.statuses.join(' · ')}</p></div><Button size='sm' className='shrink-0' variant={selectedResult === result.source_id ? 'default' : 'outline'} onClick={() => selectCandidate(result)}>{selectedResult === result.source_id ? '已选择' : '选择并抓取'} <ExternalLink className='ml-1 size-3' /></Button></div>) : <Empty title='尚未加载搜索结果' text={`勾选左侧项目后，点击“批量搜索”。${active ? '' : ''}`} />}</div></div>
}

function EditorPanel({ candidate, beforeItem, fieldSelection, setFieldSelection, overwrite, setOverwrite, setCandidate, writeback }: { candidate: MetadataCandidate | null; beforeItem: Record<string, unknown>; fieldSelection: string[]; setFieldSelection: (value: (current: string[]) => string[]) => void; overwrite: boolean; setOverwrite: (value: boolean) => void; setCandidate: (value: (current: MetadataCandidate | null) => MetadataCandidate | null) => void; writeback: () => void }) {
  return <div className='flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-white'><div className='border-b px-4 py-3'><b>编辑元数据</b></div><Tabs defaultValue='basic' className='flex min-h-0 flex-1 flex-col'><TabsList className='justify-start rounded-none border-b bg-white px-3'><TabsTrigger value='basic'>基本信息</TabsTrigger><TabsTrigger value='images'>演员图片</TabsTrigger><TabsTrigger value='history'>操作记录</TabsTrigger></TabsList><TabsContent value='basic' className='min-h-0 flex-1 overflow-y-auto p-4'>{candidate ? <><CoverPreview candidate={candidate} /><div className='mb-3 flex justify-between rounded border bg-slate-50 p-2 text-sm'><span>覆盖模式</span><button onClick={() => setOverwrite(!overwrite)}>{overwrite ? '覆盖已选字段' : '仅填充空字段'}</button></div><div className='grid grid-cols-[28px_110px_minmax(0,1fr)_minmax(0,1fr)] gap-2 border-b pb-2 text-xs text-slate-500'><span /><span>字段</span><span>当前 Emby 值</span><span>候选值</span></div><div className='divide-y'>{fields.map(([key, label]) => <FieldRow key={key} field={key} label={label} candidate={candidate} beforeItem={beforeItem} checked={fieldSelection.includes(key)} onCheck={() => setFieldSelection((current) => current.includes(key) ? current.filter((value) => value !== key) : [...current, key])} onChange={(value) => setCandidate((current) => current ? updateCandidate(current, key, value) : current)} />)}</div><div className='mt-4 rounded border bg-slate-50 p-3 text-xs'>数据源：{candidate.source}　编号：{candidate.source_id}<br />产品番号：{candidate.product_number ?? '—'}<br /><a href={candidate.raw_url} target='_blank' rel='noreferrer' className='text-blue-600'>打开来源页</a></div></> : <Empty title='等待候选详情' text='从中栏选择一条搜索结果。' />}</TabsContent><TabsContent value='images' className='min-h-0 flex-1 overflow-y-auto p-4 text-sm text-slate-500'>{candidate ? <div className='space-y-3'>{candidate.people.map((person, index) => <div key={`${person.name}-${index}`} className='flex items-center gap-3 rounded border p-2'><div className='flex size-12 items-center justify-center rounded bg-slate-100'><Database className='size-4 text-slate-400' /></div><span>{person.name}</span></div>)}</div> : <Empty title='等待候选详情' text='从中栏选择一条搜索结果。' />}</TabsContent><TabsContent value='history' className='p-4 text-sm text-slate-500'>写入完成后将在此展示本次字段变更记录。</TabsContent></Tabs><div className='flex justify-end gap-3 border-t p-3'><Button variant='outline' disabled={!candidate}>保存为草稿</Button><Button onClick={writeback} disabled={!candidate}><Upload className='size-4' />确认写入 Emby</Button></div></div>
}

function FieldRow({ field, label, candidate, beforeItem, checked, onCheck, onChange }: { field: FieldKey; label: string; candidate: MetadataCandidate; beforeItem: Record<string, unknown>; checked: boolean; onCheck: () => void; onChange: (value: string) => void }) {
  const value = candidateValues(candidate)[field]
  const embyField: Record<FieldKey, string> = { Name: 'Name', OriginalTitle: 'OriginalTitle', Taglines: 'Taglines', Overview: 'Overview', ProductionYear: 'ProductionYear', PremiereDate: 'PremiereDate', Genres: 'Genres', Studios: 'Studios', People: 'People', Tags: 'TagItems', CommunityRating: 'CommunityRating', OfficialRating: 'OfficialRating', CustomRating: 'CustomRating' }
  const current = beforeItem[embyField[field]]
  const currentText = Array.isArray(current) ? current.map((item) => typeof item === 'object' && item ? String((item as { Name?: string }).Name ?? '') : String(item)).filter(Boolean).join('、') : current === undefined || current === null ? '' : String(current)
  const rating = field === 'CommunityRating'
  return <div className='grid grid-cols-[28px_110px_minmax(0,1fr)_minmax(0,1fr)] items-center gap-2 py-2'><Checkbox checked={checked} onCheckedChange={onCheck} /><label className='text-sm'>{label}</label><div className='break-words text-sm text-slate-500'>{collectionFields.has(field) ? <ValueChips value={currentText} /> : currentText || '—'}</div><div className='min-w-0'>{field === 'Overview' ? <textarea className='h-24 max-h-24 w-full resize-y overflow-y-auto rounded border px-2 py-1 text-sm' value={value} onChange={(event) => onChange(event.target.value)} /> : <><Input type={rating ? 'number' : 'text'} min={rating ? 0 : undefined} max={rating ? 10 : undefined} step={rating ? '.1' : undefined} value={value} onChange={(event) => onChange(event.target.value)} />{collectionFields.has(field) && <div className='mt-1'><ValueChips value={value} /></div>}</>}</div></div>
}

function Status({ value }: { value: string }) { return <span className='absolute right-3 top-3 rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-600'>{value === 'pending' ? '待搜索' : value}</span> }
function Empty({ title, text }: { title: string; text: string }) { return <div className='flex h-full min-h-48 flex-col items-center justify-center text-center'><CircleHelp className='mb-3 size-8 text-slate-300' /><b className='text-sm'>{title}</b><p className='mt-1 text-sm text-slate-500'>{text}</p></div> }
