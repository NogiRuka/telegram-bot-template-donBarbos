import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Check, CircleHelp, Database, ExternalLink, LoaderCircle, RefreshCw, Search, Sparkles, Upload, X } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { apiClient, type MetadataCandidate, type MetadataSearchResult } from '@/lib/api'

const statusText: Record<string, string> = {
  pending: '待搜索', searching: '搜索中', searched: '已搜索', selection_required: '待选择',
  fetched: '已抓取', writing: '写入中', written: '已写入', failed: '失败',
}

const fields = [
  ['Name', '名称 (Name)'], ['Taglines', '宣传语 (Taglines)'], ['Overview', '简介 (Overview)'],
  ['ProductionYear', '年份 (ProductionYear)'], ['PremiereDate', '上映日期 (PremiereDate)'],
  ['Genres', '类型 (Genres)'], ['Studios', '制作方 (Studios)'], ['ProviderIds', '外部 ID (ProviderIds)'],
]

function resultImage(result: MetadataSearchResult) {
  return result.image_urls[0]
}

export function EmbyMetadataWorkspace() {
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [resultsByItem, setResultsByItem] = useState<Record<string, MetadataSearchResult[]>>({})
  const [candidate, setCandidate] = useState<MetadataCandidate | null>(null)
  const [selectedResult, setSelectedResult] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [fieldSelection, setFieldSelection] = useState<string[]>(fields.map(([key]) => key))
  const [overwrite, setOverwrite] = useState(false)
  const [statusFilter, setStatusFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [searchKeywords, setSearchKeywords] = useState<Record<string, string>>({})
  const [routing, setRouting] = useState<Record<string, { category: string; source: string }>>({})

  const queueQuery = useQuery({ queryKey: ['emby-metadata-queue'], queryFn: () => apiClient.getMetadataQueue() })
  const items = queueQuery.data?.items ?? []
  const active = items.find((item) => item.notification_id === activeId) ?? items[0]
  const results = active ? resultsByItem[active.notification_id] ?? [] : []
  const needsChoice = results.length > 1 && !candidate
  const visibleItems = useMemo(() => items.filter((item) =>
    (statusFilter === 'all' || item.status === statusFilter) &&
    (categoryFilter === 'all' || item.category === categoryFilter) &&
    (!query || `${item.item_name} ${item.path}`.toLowerCase().includes(query.toLowerCase()))
  ), [items, query, statusFilter, categoryFilter])

  const toggle = (id: string) => setSelectedIds((ids) => ids.includes(id) ? ids.filter((current) => current !== id) : [...ids, id])

  const searchSelected = async () => {
    if (!selectedIds.length) return toast.error('请先勾选要搜索的项目')
    try {
      const response = await apiClient.searchMetadataQueue(selectedIds, searchKeywords)
      const current = response.find((item) => item.notification_id === (activeId ?? selectedIds[0])) ?? response[0]
      setActiveId(current.notification_id)
      setResultsByItem((previous) => ({ ...previous, ...Object.fromEntries(response.map((item) => [item.notification_id, item.results])) }))
      setCandidate(null)
      setSelectedResult(null)
      const ambiguous = response.filter((item) => item.results.length > 1)
      if (ambiguous.length) toast.warning(`已完成搜索：${ambiguous.length} 个项目有多个候选结果，请在中栏选择。`)
      else toast.success(`已完成 ${response.length} 个项目的搜索`)
      if (current.results.length === 1) await selectCandidate(current.results[0])
    } catch (error) { toast.error(error instanceof Error ? error.message : '搜索失败') }
  }

  const selectCandidate = async (result: MetadataSearchResult) => {
    setSelectedResult(result.source_id)
    try {
      const detail = await apiClient.getMetadataCandidate(result.source, result.source_id)
      setCandidate(detail)
    } catch (error) { toast.error(error instanceof Error ? error.message : '获取详情失败') }
  }

  const writeback = async () => {
    if (!active || !candidate) return toast.error('请先选择并抓取一个候选结果')
    try {
      await apiClient.writebackMetadata(active.notification_id, { candidate, fields: fieldSelection, overwrite, confirmed: true })
      toast.success('元数据已写入 Emby')
      queueQuery.refetch()
    } catch (error) { toast.error(error instanceof Error ? error.message : '写入失败') }
  }

  return <main className='flex min-h-screen flex-col bg-slate-50 text-slate-800'>
    <header className='flex items-start justify-between border-b bg-white px-6 py-5'>
      <div><h1 className='flex items-center gap-2 text-2xl font-bold tracking-tight'>Emby 元数据工作台 <Sparkles className='size-6 text-amber-500' /></h1><p className='mt-2 text-sm text-slate-500'>自动补充动画电影元数据，支持批量搜索、候选选择与写入 Emby</p></div>
      <div className='flex items-center gap-4'><div className='rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700'><Check className='mr-1 inline size-4' />Emby 连接正常</div><Button variant='outline' onClick={() => queueQuery.refetch()}><RefreshCw className='size-4' /> 刷新队列</Button></div>
    </header>
    <section className='mx-5 mt-3 flex items-center gap-3 rounded-lg border bg-white p-2 shadow-sm'>
      <Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className='w-40'><SelectValue placeholder='处理状态' /></SelectTrigger><SelectContent><SelectItem value='all'>全部状态</SelectItem><SelectItem value='pending'>待搜索</SelectItem><SelectItem value='fetched'>已抓取</SelectItem></SelectContent></Select>
      <Select value={categoryFilter} onValueChange={setCategoryFilter}><SelectTrigger className='w-36'><SelectValue /></SelectTrigger><SelectContent><SelectItem value='all'>全部分类</SelectItem><SelectItem value='japanese_korean'>日语动漫</SelectItem><SelectItem value='domestic'>国产</SelectItem></SelectContent></Select>
      <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder='搜索词 / 番号 / 名称' className='max-w-sm' />
      <Button variant='outline' onClick={() => setQuery('')}><X className='size-4' /> 清空</Button>
    </section>
    <section className='grid h-[calc(100vh-170px)] min-h-0 grid-cols-[minmax(340px,1.05fr)_minmax(320px,.9fr)_minmax(420px,1.2fr)] gap-2 overflow-hidden px-5 py-2'>
      <div className='flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-white'>
        <div className='flex items-center justify-between border-b px-4 py-3'><b>待处理列表</b><span className='text-sm text-slate-500'>共 {items.length} 条</span></div>
        <div className='grid grid-cols-[28px_minmax(0,1.2fr)_minmax(0,1.1fr)_100px_55px] gap-2 border-b bg-slate-50 px-3 py-2 text-xs font-medium text-slate-500'><Checkbox checked={!!items.length && selectedIds.length === items.length} onCheckedChange={() => setSelectedIds(selectedIds.length === items.length ? [] : items.map((item) => item.notification_id))} /><span>项目</span><span>搜索词（可编辑）</span><span>分类 / 数据源</span><span>状态</span></div>
        <div className='min-h-0 flex-1 overflow-y-auto overflow-x-hidden'>{queueQuery.isLoading ? <Loading /> : visibleItems.map((item) => { const itemNeedsChoice = (resultsByItem[item.notification_id]?.length ?? 0) > 1; return <div role='button' tabIndex={0} key={item.notification_id} onClick={() => { setActiveId(item.notification_id); setCandidate(null); setSelectedResult(null) }} className={`grid w-full grid-cols-[28px_minmax(0,1.2fr)_minmax(0,1.1fr)_100px_55px] items-center gap-2 border-b px-3 py-3 text-left text-sm hover:bg-blue-50 ${active?.notification_id === item.notification_id ? 'bg-blue-50/70' : ''} ${itemNeedsChoice ? 'border-l-4 border-l-amber-400 bg-amber-50/40' : ''}`}>
          <Checkbox checked={selectedIds.includes(item.notification_id)} onClick={(event) => event.stopPropagation()} onCheckedChange={() => toggle(item.notification_id)} /><div className='min-w-0'><div className='flex items-center gap-1'><button type='button' className='rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600 hover:bg-blue-100' onClick={(event) => { event.stopPropagation(); void navigator.clipboard.writeText(item.item_id); toast.success(`已复制 Item ID：${item.item_id}`) }}>{item.item_id}</button>{item.image_url && <img src={item.image_url} alt='' className='size-6 rounded object-cover' />}</div><span className='mt-1 block truncate font-medium' title={item.item_name}>{item.item_name}</span></div><Input className='h-8 min-w-0' value={searchKeywords[item.notification_id] ?? item.search_keyword ?? ''} onClick={(event) => event.stopPropagation()} onChange={(event) => { event.stopPropagation(); setSearchKeywords((current) => ({ ...current, [item.notification_id]: event.target.value })) }} /><div className='min-w-0 space-y-1 text-xs' onClick={(event) => event.stopPropagation()}><Select value={routing[item.notification_id]?.category ?? item.category} onValueChange={(value) => setRouting((current) => ({ ...current, [item.notification_id]: { category: value, source: current[item.notification_id]?.source ?? item.source } }))}><SelectTrigger className='h-7 w-full text-xs'><SelectValue /></SelectTrigger><SelectContent><SelectItem value='domestic'>国产</SelectItem><SelectItem value='japanese_korean'>日语动漫</SelectItem><SelectItem value='western'>欧美</SelectItem></SelectContent></Select><Select value={routing[item.notification_id]?.source ?? item.source} onValueChange={(value) => setRouting((current) => ({ ...current, [item.notification_id]: { category: current[item.notification_id]?.category ?? item.category, source: value } }))}><SelectTrigger className='h-7 w-full text-xs'><SelectValue /></SelectTrigger><SelectContent><SelectItem value='ck-download'>ck-download</SelectItem><SelectItem value='tmdb'>TMDB</SelectItem></SelectContent></Select></div>{itemNeedsChoice ? <span className='rounded bg-amber-100 px-1.5 py-1 text-xs text-amber-700'>待选择</span> : <Status value={item.status} />}</div> })}</div>
        <div className='flex items-center gap-2 border-t bg-slate-50 p-3'><span className='mr-auto text-sm text-blue-600'>已选择 {selectedIds.length} 项</span><Button onClick={searchSelected}><Search className='size-4' /> 批量搜索</Button><Button variant='outline' onClick={() => setSelectedIds([])}>取消选择</Button></div>
      </div>
      <div className='flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-white'>
        <div className='flex items-center justify-between border-b px-4 py-3'><div><b>搜索结果{active ? `（${active.item_name}）` : ''}</b>{needsChoice && <span className='ml-2 rounded bg-amber-100 px-2 py-1 text-xs font-medium text-amber-700'>请选择一个候选结果</span>}</div><Button size='icon' variant='ghost' onClick={() => { setResultsByItem((current) => active ? { ...current, [active.notification_id]: [] } : current); setCandidate(null) }}><X className='size-4' /></Button></div>
        <div className='min-h-0 flex-1 space-y-2 overflow-y-auto overflow-x-hidden p-3'>{results.length ? results.map((result) => <div key={`${result.source}-${result.source_id}`} className={`flex w-full gap-3 rounded-lg border p-3 text-left transition ${selectedResult === result.source_id ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500' : ''}`}>
          <div className='flex size-20 shrink-0 items-center justify-center overflow-hidden rounded bg-slate-100 text-slate-400'>{resultImage(result) ? <img src={resultImage(result)} alt='' className='size-full object-cover' /> : <Database className='size-6' />}</div><div className='min-w-0 flex-1'><b className='line-clamp-2 text-sm'>{result.title}</b><p className='mt-1 text-xs text-slate-500'>{result.release_date ?? '日期未知'}　{result.statuses.join(' · ')}</p><p className='mt-1 text-xs text-slate-400'>{result.source}: {result.source_id}</p></div><Button size='sm' variant={selectedResult === result.source_id ? 'default' : 'outline'} className='mt-auto shrink-0' onClick={() => selectCandidate(result)}>{selectedResult === result.source_id ? '已选择' : '选择并抓取'} <ExternalLink className='ml-1 size-3' /></Button></div>) : <Empty title='尚未加载搜索结果' text='勾选左侧项目后，点击“批量搜索”。' />}</div>
      </div>
      <div className='flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-white'>
        <div className='border-b px-4 py-3'><b>编辑元数据</b><span className='ml-2 text-sm text-slate-500'>{candidate ? `当前项目：${candidate.title}` : '请选择候选结果'}</span></div>
        <Tabs defaultValue='basic' className='flex min-h-0 flex-1 flex-col'><TabsList className='justify-start rounded-none border-b bg-white px-3'><TabsTrigger value='basic'>基本信息</TabsTrigger><TabsTrigger value='images' disabled>封面 & 演员</TabsTrigger><TabsTrigger value='history' disabled>操作记录</TabsTrigger></TabsList>
          <div className='overflow-auto p-4'>{candidate ? <>
            <div className='mb-4 flex items-center justify-between rounded-md border bg-slate-50 p-2'><span className='text-sm font-medium'>覆盖模式</span><button onClick={() => setOverwrite(!overwrite)} className={`rounded px-3 py-1.5 text-sm ${overwrite ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 shadow-sm'}`}>{overwrite ? '覆盖已选字段' : '仅填充空字段（默认）'}</button></div>
            {overwrite && <div className='mb-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700'>覆盖模式会替换 Emby 中已存在的已选字段。</div>}
            <div className='grid grid-cols-[28px_130px_1fr] gap-x-3 border-b pb-2 text-xs text-slate-500'><span /><span>字段</span><span>候选值（可编辑）</span></div>
            <div className='divide-y'>{fields.map(([key, label]) => <div key={key} className='grid grid-cols-[28px_130px_1fr] items-center gap-x-3 py-2'><Checkbox checked={fieldSelection.includes(key)} onCheckedChange={() => setFieldSelection((current) => current.includes(key) ? current.filter((value) => value !== key) : [...current, key])} /><label className='text-sm'>{label}</label><CandidateValue candidate={candidate} field={key} onChange={(value) => setCandidate((current) => current ? updateCandidateField(current, key, value) : current)} /></div>)}</div>
            <div className='mt-4 rounded-md border bg-slate-50 p-3 text-xs leading-6 text-slate-600'><b className='text-slate-700'>来源信息</b><br />数据源：{candidate.source}　source_id：{candidate.source_id}<br />详情页：<a href={candidate.raw_url} target='_blank' className='text-blue-600'>打开来源页</a></div>
          </> : <Empty title='等待候选详情' text='从中栏选择一条搜索结果，系统将加载可编辑的元数据。' />}</div>
        </Tabs>
        <div className='flex justify-end gap-3 border-t p-3'><Button variant='outline' disabled={!candidate} onClick={() => toast.success('草稿已保存在当前浏览器会话中')}>保存为草稿</Button><Button onClick={writeback} disabled={!candidate}><Upload className='size-4' /> 确认写入 Emby</Button></div>
      </div>
    </section>
  </main>
}

function CandidateValue({ candidate, field, onChange }: { candidate: MetadataCandidate; field: string; onChange: (value: string) => void }) {
  const values: Record<string, string> = { Name: candidate.title, Taglines: candidate.taglines ?? '—', Overview: candidate.overview ?? '—', ProductionYear: String(candidate.year ?? '—'), PremiereDate: candidate.release_date ?? '—', Genres: candidate.genres.map((item) => item.name).join('、') || '—', Studios: candidate.studios.map((item) => item.name).join('、') || '—', ProviderIds: Object.entries(candidate.external_ids).map(([key, value]) => `${key}: ${value}`).join(' · ') || '—' }
  return field === 'Overview' ? <textarea className='min-h-16 w-full rounded border bg-white px-2 py-1.5 text-sm' value={values[field]} onChange={(event) => onChange(event.target.value)} /> : <Input value={values[field]} onChange={(event) => onChange(event.target.value)} />
}
function updateCandidateField(candidate: MetadataCandidate, field: string, value: string): MetadataCandidate {
  if (field === 'Name') return { ...candidate, title: value }
  if (field === 'Taglines') return { ...candidate, taglines: value }
  if (field === 'Overview') return { ...candidate, overview: value }
  if (field === 'ProductionYear') return { ...candidate, year: Number(value) || undefined }
  if (field === 'PremiereDate') return { ...candidate, release_date: value }
  if (field === 'Genres') return { ...candidate, genres: value.split(/[、,]/).filter(Boolean).map((name) => ({ name: name.trim() })) }
  if (field === 'Studios') return { ...candidate, studios: value.split(/[、,]/).filter(Boolean).map((name) => ({ name: name.trim() })) }
  if (field === 'ProviderIds') return { ...candidate, external_ids: Object.fromEntries(value.split('·').map((part) => part.split(':').map((text) => text.trim())).filter(([key, item]) => key && item)) }
  return candidate
}
function Status({ value }: { value: string }) { return <span className={`rounded px-1.5 py-1 text-xs ${value === 'written' || value === 'fetched' ? 'bg-emerald-50 text-emerald-600' : value === 'failed' ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'}`}>{statusText[value] ?? value}</span> }
function Loading() { return <div className='flex h-40 items-center justify-center text-slate-500'><LoaderCircle className='mr-2 size-5 animate-spin' />正在加载队列…</div> }
function Empty({ title, text }: { title: string; text: string }) { return <div className='flex h-full min-h-48 flex-col items-center justify-center px-8 text-center'><CircleHelp className='mb-3 size-8 text-slate-300' /><b className='text-sm'>{title}</b><p className='mt-1 text-sm text-slate-500'>{text}</p></div> }
