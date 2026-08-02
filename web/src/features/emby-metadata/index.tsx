import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Check, ChevronDown, CircleHelp, Database, ExternalLink, LoaderCircle, RefreshCw, Search, Sparkles, Upload, X } from 'lucide-react'
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
  const [results, setResults] = useState<MetadataSearchResult[]>([])
  const [candidate, setCandidate] = useState<MetadataCandidate | null>(null)
  const [selectedResult, setSelectedResult] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [fieldSelection, setFieldSelection] = useState<string[]>(fields.map(([key]) => key))
  const [overwrite, setOverwrite] = useState(false)

  const queueQuery = useQuery({ queryKey: ['emby-metadata-queue'], queryFn: () => apiClient.getMetadataQueue() })
  const items = queueQuery.data?.items ?? []
  const active = items.find((item) => item.notification_id === activeId) ?? items[0]
  const visibleItems = useMemo(() => items.filter((item) => !query || `${item.item_name} ${item.path}`.toLowerCase().includes(query.toLowerCase())), [items, query])

  const toggle = (id: string) => setSelectedIds((ids) => ids.includes(id) ? ids.filter((current) => current !== id) : [...ids, id])

  const searchSelected = async () => {
    if (!selectedIds.length) return toast.error('请先勾选要搜索的项目')
    try {
      const response = await apiClient.searchMetadataQueue(selectedIds)
      const current = response.find((item) => item.notification_id === (activeId ?? selectedIds[0])) ?? response[0]
      setActiveId(current.notification_id)
      setResults(current.results)
      setCandidate(null)
      setSelectedResult(null)
      toast.success(`已完成 ${response.length} 个项目的搜索`)
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
    <div className='border-b bg-white px-6 py-3'><div className='mx-auto flex max-w-2xl items-center justify-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 py-2 text-sm text-slate-600'><Check className='size-4 text-emerald-600' />搜索完成后，在中栏选择候选结果，再确认写入 Emby。</div></div>
    <section className='mx-5 mt-3 flex items-center gap-3 rounded-lg border bg-white p-2 shadow-sm'>
      <Select defaultValue='all'><SelectTrigger className='w-40'><SelectValue placeholder='处理状态' /></SelectTrigger><SelectContent><SelectItem value='all'>全部状态</SelectItem><SelectItem value='pending'>待搜索</SelectItem><SelectItem value='fetched'>已抓取</SelectItem></SelectContent></Select>
      <Select defaultValue='all'><SelectTrigger className='w-36'><SelectValue /></SelectTrigger><SelectContent><SelectItem value='all'>全部分类</SelectItem><SelectItem value='japanese_korean'>日语动漫</SelectItem><SelectItem value='domestic'>国产</SelectItem></SelectContent></Select>
      <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder='搜索词 / 番号 / 名称' className='max-w-sm' />
      <Button variant='outline' onClick={() => setQuery('')}><X className='size-4' /> 清空</Button>
    </section>
    <section className='grid min-h-0 flex-1 grid-cols-[minmax(390px,1.05fr)_minmax(340px,.9fr)_minmax(460px,1.2fr)] gap-2 px-5 py-2'>
      <div className='flex min-h-0 flex-col overflow-hidden rounded-lg border bg-white'>
        <div className='flex items-center justify-between border-b px-4 py-3'><b>待处理列表</b><span className='text-sm text-slate-500'>共 {items.length} 条</span></div>
        <div className='grid grid-cols-[28px_1.2fr_1.1fr_90px_55px] gap-2 border-b bg-slate-50 px-3 py-2 text-xs font-medium text-slate-500'><Checkbox checked={!!items.length && selectedIds.length === items.length} onCheckedChange={() => setSelectedIds(selectedIds.length === items.length ? [] : items.map((item) => item.notification_id))} /><span>项目</span><span>搜索词（可编辑）</span><span>分类 / 数据源</span><span>状态</span></div>
        <div className='flex-1 overflow-auto'>{queueQuery.isLoading ? <Loading /> : visibleItems.map((item) => <button type='button' key={item.notification_id} onClick={() => setActiveId(item.notification_id)} className={`grid w-full grid-cols-[28px_1.2fr_1.1fr_90px_55px] items-center gap-2 border-b px-3 py-3 text-left text-sm hover:bg-blue-50 ${active?.notification_id === item.notification_id ? 'bg-blue-50/70' : ''}`}>
          <Checkbox checked={selectedIds.includes(item.notification_id)} onClick={(event) => event.stopPropagation()} onCheckedChange={() => toggle(item.notification_id)} /><div><b className='block text-xs text-slate-500'>#{item.item_id}</b><span className='line-clamp-2 font-medium'>{item.item_name}</span><small className='block truncate text-slate-400'>{item.path}</small></div><Input className='h-8' defaultValue={item.search_keyword ?? item.item_name} onClick={(event) => event.stopPropagation()} /><div className='text-xs'><span className='block'>{item.category_label}</span><span className='text-slate-500'>{item.source}</span></div><Status value={item.status} /></button>)}</div>
        <div className='flex items-center gap-2 border-t bg-slate-50 p-3'><span className='mr-auto text-sm text-blue-600'>已选择 {selectedIds.length} 项</span><Button onClick={searchSelected}><Search className='size-4' /> 批量搜索</Button><Button variant='outline'>更多操作 <ChevronDown className='size-4' /></Button></div>
      </div>
      <div className='flex min-h-0 flex-col overflow-hidden rounded-lg border bg-white'>
        <div className='flex items-center justify-between border-b px-4 py-3'><b>搜索结果{active ? `（${active.item_name}）` : ''}</b><Button size='icon' variant='ghost' onClick={() => { setResults([]); setCandidate(null) }}><X className='size-4' /></Button></div>
        <div className='flex-1 space-y-2 overflow-auto p-3'>{results.length ? results.map((result) => <button type='button' onClick={() => selectCandidate(result)} key={`${result.source}-${result.source_id}`} className={`flex w-full gap-3 rounded-lg border p-3 text-left transition hover:border-blue-400 ${selectedResult === result.source_id ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500' : ''}`}>
          <div className='flex size-20 shrink-0 items-center justify-center overflow-hidden rounded bg-slate-100 text-slate-400'>{resultImage(result) ? <img src={resultImage(result)} alt='' className='size-full object-cover' /> : <Database className='size-6' />}</div><div className='min-w-0 flex-1'><b className='line-clamp-2 text-sm'>{result.title}</b><p className='mt-1 text-xs text-slate-500'>{result.release_date ?? '日期未知'}　{result.statuses.join(' · ')}</p><p className='mt-1 text-xs text-slate-400'>{result.source}: {result.source_id}</p><span className='mt-2 inline-flex items-center text-xs text-blue-600'>选择并抓取 <ExternalLink className='ml-1 size-3' /></span></div></button>) : <Empty title='尚未加载搜索结果' text='勾选左侧项目后，点击“批量搜索”。' />}</div>
      </div>
      <div className='flex min-h-0 flex-col overflow-hidden rounded-lg border bg-white'>
        <div className='border-b px-4 py-3'><b>编辑元数据</b><span className='ml-2 text-sm text-slate-500'>{candidate ? `当前项目：${candidate.title}` : '请选择候选结果'}</span></div>
        <Tabs defaultValue='basic' className='flex min-h-0 flex-1 flex-col'><TabsList className='justify-start rounded-none border-b bg-white px-3'><TabsTrigger value='basic'>基本信息</TabsTrigger><TabsTrigger value='images' disabled>封面 & 演员</TabsTrigger><TabsTrigger value='history' disabled>操作记录</TabsTrigger></TabsList>
          <div className='overflow-auto p-4'>{candidate ? <>
            <div className='mb-4 flex items-center justify-between rounded-md border bg-slate-50 p-2'><span className='text-sm font-medium'>覆盖模式</span><button onClick={() => setOverwrite(!overwrite)} className={`rounded px-3 py-1.5 text-sm ${overwrite ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 shadow-sm'}`}>{overwrite ? '覆盖已选字段' : '仅填充空字段（默认）'}</button></div>
            {overwrite && <div className='mb-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700'>覆盖模式会替换 Emby 中已存在的已选字段。</div>}
            <div className='grid grid-cols-[28px_130px_1fr] gap-x-3 border-b pb-2 text-xs text-slate-500'><span /><span>字段</span><span>候选值（可编辑）</span></div>
            <div className='divide-y'>{fields.map(([key, label]) => <div key={key} className='grid grid-cols-[28px_130px_1fr] items-center gap-x-3 py-2'><Checkbox checked={fieldSelection.includes(key)} onCheckedChange={() => setFieldSelection((current) => current.includes(key) ? current.filter((value) => value !== key) : [...current, key])} /><label className='text-sm'>{label}</label><CandidateValue candidate={candidate} field={key} /></div>)}</div>
            <div className='mt-4 rounded-md border bg-slate-50 p-3 text-xs leading-6 text-slate-600'><b className='text-slate-700'>来源信息</b><br />数据源：{candidate.source}　source_id：{candidate.source_id}<br />详情页：<a href={candidate.raw_url} target='_blank' className='text-blue-600'>打开来源页</a></div>
          </> : <Empty title='等待候选详情' text='从中栏选择一条搜索结果，系统将加载可编辑的元数据。' />}</div>
        </Tabs>
        <div className='flex justify-end gap-3 border-t p-3'><Button variant='outline'>保存为草稿</Button><Button onClick={writeback} disabled={!candidate}><Upload className='size-4' /> 确认写入 Emby</Button></div>
      </div>
    </section>
  </main>
}

function CandidateValue({ candidate, field }: { candidate: MetadataCandidate; field: string }) {
  const values: Record<string, string> = { Name: candidate.title, Taglines: candidate.taglines ?? '—', Overview: candidate.overview ?? '—', ProductionYear: String(candidate.year ?? '—'), PremiereDate: candidate.release_date ?? '—', Genres: candidate.genres.map((item) => item.name).join('、') || '—', Studios: candidate.studios.map((item) => item.name).join('、') || '—', ProviderIds: Object.entries(candidate.external_ids).map(([key, value]) => `${key}: ${value}`).join(' · ') || '—' }
  return field === 'Overview' ? <textarea className='min-h-16 w-full rounded border bg-white px-2 py-1.5 text-sm' defaultValue={values[field]} /> : <Input defaultValue={values[field]} />
}
function Status({ value }: { value: string }) { return <span className={`rounded px-1.5 py-1 text-xs ${value === 'written' || value === 'fetched' ? 'bg-emerald-50 text-emerald-600' : value === 'failed' ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'}`}>{statusText[value] ?? value}</span> }
function Loading() { return <div className='flex h-40 items-center justify-center text-slate-500'><LoaderCircle className='mr-2 size-5 animate-spin' />正在加载队列…</div> }
function Empty({ title, text }: { title: string; text: string }) { return <div className='flex h-full min-h-48 flex-col items-center justify-center px-8 text-center'><CircleHelp className='mb-3 size-8 text-slate-300' /><b className='text-sm'>{title}</b><p className='mt-1 text-sm text-slate-500'>{text}</p></div> }
