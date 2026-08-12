import { useEffect, useId, useMemo, useState, type MouseEvent, type WheelEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Check, CircleHelp, Database, ExternalLink, Maximize2, RefreshCw, Search, Sparkles, Upload, X } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { apiClient, type MetadataCandidate, type MetadataPerson, type MetadataQueueItem, type MetadataSearchResult } from '@/lib/api'

const fields = [
  ['Name', '名称'], ['OriginalTitle', '原标题'], ['Taglines', '宣传语'], ['Overview', '简介'],
  ['ProductionYear', '年份'], ['PremiereDate', '上映日期'], ['Genres', '类型'], ['Studios', '工作室'],
  ['People', '演员'], ['Tags', '标签'], ['CommunityRating', '社区评分'], ['OfficialRating', '家长评分'],
  ['CustomRating', '自定义评分'], ['SortName', '排序标题'], ['ForcedSortName', '强制排序标题'],
  ['ExternalIds', '外部 ID'],
] as const

type FieldKey = typeof fields[number][0]
type Routing = { category: string; source: string }
type ResultGroup = { item: MetadataQueueItem; results: MetadataSearchResult[] }
const collectionFields = new Set<FieldKey>(['Genres', 'Studios', 'People', 'Tags'])
const ratingOptions = ['', 'TV-Y', 'APPROVED', 'G', 'E', 'EC', 'TV-G', 'TV-Y7', 'TV-Y7-FV', 'PG', 'TV-PG', 'PG-13', 'T', 'TV-14', 'R', 'M', 'TV-MA', 'NC-17', 'AO', 'RP', 'UR', 'X', 'XXX']

function Checkbox({ checked = false, onCheckedChange, className = '', onClick, disabled = false }: { checked?: boolean; onCheckedChange?: (checked: boolean) => void; className?: string; onClick?: (event: MouseEvent<HTMLDivElement>) => void; disabled?: boolean }) {
  const id = `check-${useId().replace(/:/g, '')}`
  return <div className={`checkbox-wrapper ${className}`} onClick={onClick}><input checked={checked} disabled={disabled} type='checkbox' className='check' id={id} onChange={(event) => onCheckedChange?.(event.target.checked)} /><label htmlFor={id} className='label' aria-label='选择'><svg width='45' height='45' viewBox='0 0 95 95' aria-hidden='true'><rect x='30' y='20' width='50' height='50' stroke='black' fill='none' /><g transform='translate(0,-952.36222)'><path d='m 56,963 c -102,122 6,9 7,9 17,-5 -66,69 -38,52 122,-77 -7,14 18,4 29,-11 45,-43 23,-4' stroke='black' strokeWidth='3' fill='none' className='path1' /></g></svg><span className='sr-only'>Checkbox</span></label></div>
}

function SourceIcon(_props: { source: string; className?: string }) {
  return null
}
function candidateValues(candidate: MetadataCandidate): Record<FieldKey, string> {
  const join = (items: Array<{ name: string }>) => items.map((item) => item.name).join('、')
  return {
    Name: candidate.title, OriginalTitle: candidate.original_title, Taglines: candidate.taglines ?? '',
    Overview: candidate.overview ?? '', ProductionYear: candidate.year ? String(candidate.year) : '',
    PremiereDate: candidate.release_date ?? '', Genres: join(candidate.genres), Studios: join(candidate.studios),
    People: join(candidate.people), Tags: join(candidate.tags),
    CommunityRating: candidate.community_rating === undefined ? '' : String(candidate.community_rating),
    OfficialRating: candidate.official_rating ?? '', CustomRating: candidate.custom_rating ?? '',
    SortName: candidate.sort_name, ForcedSortName: candidate.forced_sort_name,
    ExternalIds: JSON.stringify(candidate.external_ids, null, 2),
  }
}

type FieldValue = string | MetadataPerson[]

function updateCandidate(candidate: MetadataCandidate, field: FieldKey, value: FieldValue): MetadataCandidate {
  if (field === 'People' && Array.isArray(value)) return { ...candidate, people: value }
  if (typeof value !== 'string') return candidate
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
  if (field === 'SortName') return { ...candidate, sort_name: value }
  if (field === 'ForcedSortName') return { ...candidate, forced_sort_name: value }
  if (field === 'ExternalIds') {
    try { return { ...candidate, external_ids: JSON.parse(value) as Record<string, string> } }
    catch { return candidate }
  }
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

function CoverPreview({ candidate, onChange }: { candidate: MetadataCandidate; onChange?: (candidate: MetadataCandidate) => void }) {
  const currentImageUrl = candidate.current_image_url ?? null
  const scrapedImageUrl = candidate.poster_data
    ? `data:image/jpeg;base64,${candidate.poster_data}`
    : candidate.poster_url
      ? apiClient.metadataImageUrl(candidate.poster_url, candidate.raw_url)
      : null
  const selectPoster = (file: File) => {
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = String(reader.result)
      const nextCandidate = { ...candidate, poster_data: dataUrl.split(',', 2)[1] ?? '', poster_url: undefined }
      onChange?.(nextCandidate)
      window.dispatchEvent(new CustomEvent('metadata-poster-uploaded', { detail: nextCandidate }))
    }
    reader.readAsDataURL(file)
  }
  return <div className='mb-4 flex items-center gap-4 rounded-lg border bg-slate-50 p-3'>
    <div className='min-w-0 flex-1'><b className='mb-2 block text-sm'>当前 Emby 封面</b><div className='flex h-28 items-center justify-center overflow-hidden rounded bg-slate-200'>{currentImageUrl ? <img src={currentImageUrl} alt='当前 Emby 封面' className='size-full object-contain' /> : <Database className='size-7 text-slate-400' />}</div></div>
    <div className='min-w-0 flex-1'><b className='mb-2 block text-sm'>抓取封面</b><label className='flex h-28 cursor-pointer items-center justify-center overflow-hidden rounded bg-slate-200 hover:ring-2 hover:ring-blue-300'>{scrapedImageUrl ? <img src={scrapedImageUrl} alt='抓取封面' className='size-full object-contain' /> : <Database className='size-7 text-slate-400' />}<input type='file' accept='image/*' className='sr-only' onChange={(event) => { const file = event.target.files?.[0]; if (file) selectPoster(file); event.target.value = '' }} /></label></div>
  </div>
}

export function EmbyMetadataWorkspace() {
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [resultsByItem, setResultsByItem] = useState<Record<string, MetadataSearchResult[]>>({})
  const [candidatesByItem, setCandidatesByItem] = useState<Record<string, MetadataCandidate>>({})
  const [beforeItemsByItem, setBeforeItemsByItem] = useState<Record<string, Record<string, unknown>>>({})
  const [candidate, setCandidate] = useState<MetadataCandidate | null>(null)
  const [beforeItem, setBeforeItem] = useState<Record<string, unknown>>({})
  const [selectedResult, setSelectedResult] = useState<string | null>(null)
  const [selectedResultsByItem, setSelectedResultsByItem] = useState<Record<string, string>>({})
  const [query, setQuery] = useState('')
  const [fieldSelection, setFieldSelection] = useState<string[]>(fields.map(([key]) => key))
  const [statusFilter, setStatusFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [autoTranslate, setAutoTranslate] = useState(false)
  const [searchKeywords, setSearchKeywords] = useState<Record<string, string>>({})
  const [routing, setRouting] = useState<Record<string, Routing>>({})
  const [statusOverrides, setStatusOverrides] = useState<Record<string, string>>({})
  const [, setSearching] = useState(false)

  const queueQuery = useQuery({ queryKey: ['emby-metadata-queue'], queryFn: () => apiClient.getMetadataQueue() })
  const refreshQueue = async () => {
    try {
      await queueQuery.refetch()
      toast.success('队列已刷新')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '刷新队列失败')
    }
  }
  const items = queueQuery.data?.items ?? []
  useEffect(() => {
    const handleTitleTranslation = (event: Event) => {
      const translatedTitle = (event as CustomEvent<string>).detail
      if (typeof translatedTitle === 'string') {
        setCandidate((current) => current ? { ...current, taglines: translatedTitle } : current)
      }
    }
    window.addEventListener('metadata-title-translated', handleTitleTranslation)
    const handlePosterUpload = (event: Event) => {
      const nextCandidate = (event as CustomEvent<MetadataCandidate>).detail
      if (nextCandidate?.poster_data) setCandidate(nextCandidate)
    }
    window.addEventListener('metadata-poster-uploaded', handlePosterUpload)
    return () => {
      window.removeEventListener('metadata-title-translated', handleTitleTranslation)
      window.removeEventListener('metadata-poster-uploaded', handlePosterUpload)
    }
  }, [])
  useEffect(() => {
    const openItemInEmby = (event: globalThis.MouseEvent) => {
      const button = event.target instanceof Element ? event.target.closest('button') : null
      if (!button || !button.classList.contains('shrink-0') || !button.classList.contains('text-[10px]')) return
      const item = items.find((value) => value.item_id === button.textContent?.trim())
      if (!item?.emby_url) return
      event.preventDefault()
      event.stopPropagation()
      window.open(item.emby_url, '_blank', 'noopener,noreferrer')
    }
    document.addEventListener('click', openItemInEmby, true)
    return () => document.removeEventListener('click', openItemInEmby, true)
  }, [items])
  useEffect(() => {
    const layer = document.createElement('div')
    const preview = document.createElement('img')
    layer.style.cssText = 'position:fixed;z-index:1000;display:block;background:transparent!important;opacity:0;pointer-events:none;transition:opacity 150ms ease;'
    preview.style.cssText = 'display:block;width:min(55vw,720px);max-height:82vh;object-fit:contain;border-radius:.5rem;'
    layer.appendChild(preview)
    document.body.appendChild(layer)
    const showPreview = (event: Event) => {
      const image = event.target instanceof HTMLImageElement ? event.target : null
      if (!image || !image.closest('main')) return
      const placePreview = () => {
        const rect = image.getBoundingClientRect()
        const previewRect = preview.getBoundingClientRect()
        const gap = 12
        const left = rect.right + previewRect.width + gap <= window.innerWidth ? rect.right + gap : Math.max(gap, rect.left - previewRect.width - gap)
        const top = Math.min(Math.max(gap, rect.top), Math.max(gap, window.innerHeight - previewRect.height - gap))
        layer.style.left = `${left}px`
        layer.style.top = `${top}px`
      }
      preview.onload = placePreview
      preview.src = image.currentSrc || image.src
      preview.alt = image.alt
      placePreview()
      layer.style.opacity = '1'
    }
    const hidePreview = (event: Event) => {
      if (event.target instanceof HTMLImageElement) layer.style.opacity = '0'
    }
    document.addEventListener('mouseover', showPreview)
    document.addEventListener('mouseout', hidePreview)
    return () => {
      document.removeEventListener('mouseover', showPreview)
      document.removeEventListener('mouseout', hidePreview)
      layer.remove()
    }
  }, [])
  const active = items.find((item) => item.notification_id === activeId) ?? items[0]
  const resultGroups = Object.entries(resultsByItem)
    .map(([notificationId, itemResults]) => ({
      item: items.find((value) => value.notification_id === notificationId),
      results: itemResults,
    }))
    .filter((group): group is ResultGroup => Boolean(group.item))
  const visibleItems = useMemo(() => items
    .filter((item) =>
      (statusFilter === 'all' || (statusOverrides[item.notification_id] ?? item.status) === statusFilter) &&
      (categoryFilter === 'all' || item.category === categoryFilter) &&
      (!query || item.item_name.toLowerCase().includes(query.toLowerCase())),
    )
    .map((item) => ({ ...item, status: statusOverrides[item.notification_id] ?? item.status })),
  [items, query, statusFilter, categoryFilter, statusOverrides])

  const routeFor = (item: MetadataQueueItem): Routing => routing[item.notification_id] ?? { category: item.category, source: item.source }
  const toggle = (id: string) => setSelectedIds((ids) => ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id])
  const clearActive = () => { setCandidate(null); setSelectedResult(null); setBeforeItem({}) }
  const activateItem = (notificationId: string) => {
    setActiveId(notificationId)
    setCandidate(candidatesByItem[notificationId] ?? null)
    setBeforeItem(beforeItemsByItem[notificationId] ?? {})
    setSelectedResult(selectedResultsByItem[notificationId] ?? null)
  }

  useEffect(() => {
    if (activeId && candidate) setCandidatesByItem((current) => ({ ...current, [activeId]: candidate }))
  }, [activeId, candidate])

  const searchSelected = async () => {
    if (!selectedIds.length) return toast.error('请先勾选要搜索的项目')
    const selections = selectedIds.map((notification_id) => {
      const item = items.find((value) => value.notification_id === notification_id)!
      const route = routeFor(item)
      return { notification_id, keyword: searchKeywords[notification_id] ?? item.search_keyword ?? '', ...route }
    })
    if (selections.some((item) => !item.source)) return toast.error('所选分类尚未配置数据源')
    const toastId = toast.loading(`正在搜索 ${selections.length} 个项目，请稍候...`)
    setSearching(true)
    try {
      const response = await apiClient.searchMetadataQueue(selections)
      if (!response.length) throw new Error('搜索没有返回结果')
      const current = response.find((item) => item.notification_id === (activeId ?? selectedIds[0])) ?? response[0]
      setActiveId(current.notification_id)
      setResultsByItem((previous) => ({ ...previous, ...Object.fromEntries(response.map((item) => [item.notification_id, item.results])) }))
      setStatusOverrides((current) => ({ ...current, ...Object.fromEntries(response.map((item) => [item.notification_id, 'searched'])) }))
      setCandidatesByItem((previous) => Object.fromEntries(Object.entries(previous).filter(([notificationId]) => !selectedIds.includes(notificationId))))
      setBeforeItemsByItem((previous) => Object.fromEntries(Object.entries(previous).filter(([notificationId]) => !selectedIds.includes(notificationId))))
      setSelectedResultsByItem((previous) => Object.fromEntries(Object.entries(previous).filter(([notificationId]) => !selectedIds.includes(notificationId))))
      clearActive()
      toast.success('搜索完成，请在中间栏查看结果', { id: toastId })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '搜索失败，请稍后重试', { id: toastId })
    } finally { setSearching(false) }
  }

  const selectCandidate = async (result: MetadataSearchResult, resultOwnerId?: string) => {
    const ownerId = resultOwnerId ?? Object.entries(resultsByItem).find(([, itemResults]) =>
      itemResults.some((itemResult) => itemResult.source === result.source && itemResult.source_id === result.source_id),
    )?.[0] ?? active?.notification_id
    const owner = items.find((item) => item.notification_id === ownerId) ?? active
    if (!owner) return
    setActiveId(owner.notification_id)
    setSelectedResult(result.source_id)
    setSelectedResultsByItem((current) => ({ ...current, [owner.notification_id]: result.source_id }))
    const cachedCandidate = candidatesByItem[owner.notification_id]
    if (cachedCandidate && selectedResultsByItem[owner.notification_id] === result.source_id) {
      setCandidate(cachedCandidate)
      setBeforeItem(beforeItemsByItem[owner.notification_id] ?? {})
      return
    }
    try {
      const response = await apiClient.getMetadataCandidate(owner.notification_id, result.source, result.source_id)
      let nextCandidate = response.candidate
      if (autoTranslate && response.candidate.title?.trim()) {
        try {
          const translatedTitle = await apiClient.translateMetadata(response.candidate.title)
          nextCandidate = {
            ...nextCandidate,
            taglines: translatedTitle,
          }
        } catch (error) { toast.error(error instanceof Error ? error.message : '自动翻译标题失败') }
      }
      if (autoTranslate && response.candidate.overview?.trim()) {
        try {
          const translation = await apiClient.translateMetadata(response.candidate.overview)
          nextCandidate = { ...nextCandidate, overview: `${translation}\n\n---\n\n${response.candidate.overview}` }
        } catch (error) { toast.error(error instanceof Error ? error.message : '自动翻译简介失败') }
      }
      setCandidate(nextCandidate)
      setStatusOverrides((current) => ({ ...current, [owner.notification_id]: 'fetched' }))
      setCandidatesByItem((current) => ({ ...current, [owner.notification_id]: nextCandidate }))
      setBeforeItem(response.before_item)
      setBeforeItemsByItem((current) => ({ ...current, [owner.notification_id]: response.before_item }))
    } catch (error) { toast.error(error instanceof Error ? error.message : '获取详情失败') }
  }

  const writeback = async () => {
    if (!active || !candidate) return toast.error('请先选择候选结果')
    try { await apiClient.writebackMetadata(active.notification_id, { candidate, fields: fields.map(([key]) => key), overwrite: true, confirmed: true }); setStatusOverrides((current) => ({ ...current, [active.notification_id]: 'written' })); toast.success('元数据已写入 Emby'); void queueQuery.refetch() }
    catch (error) { toast.error(error instanceof Error ? error.message : '写入失败') }
  }

  const batchWriteback = async () => {
    const targets = selectedIds.map((notificationId) => ({ notificationId, candidate: candidatesByItem[notificationId] }))
    const unconfirmed = targets.filter((target) => !target.candidate).map((target) => target.notificationId)
    const ready = targets.filter((target): target is { notificationId: string; candidate: MetadataCandidate } => Boolean(target.candidate))
    if (!ready.length) return toast.error('所选项目都还没有确认候选结果')
    const failed: string[] = []
    const toastId = toast.loading(`正在写入 ${ready.length} 个项目...`)
    for (const target of ready) {
      try {
        await apiClient.writebackMetadata(target.notificationId, {
          candidate: target.candidate,
          fields: fields.map(([key]) => key),
          overwrite: true,
          confirmed: true,
        })
        setStatusOverrides((current) => ({ ...current, [target.notificationId]: 'written' }))
      } catch {
        failed.push(target.notificationId)
      }
    }
    void queueQuery.refetch()
    const summary = `写入成功 ${ready.length - failed.length} 项${failed.length ? `，失败 ${failed.length} 项` : ''}${unconfirmed.length ? `，未确认 ${unconfirmed.length} 项` : ''}`
    if (failed.length || unconfirmed.length) toast.warning(summary, { id: toastId })
    else toast.success(summary, { id: toastId })
  }

  return <main className='flex min-h-screen flex-col bg-slate-50 text-slate-800'>
    <header className='flex items-start justify-between border-b bg-white px-6 py-4'><div><h1 className='flex items-center gap-2 text-2xl font-bold'>Emby 元数据工作台 <Sparkles className='size-6 text-amber-500' /></h1><p className='mt-1 text-sm text-slate-500'>批量搜索、候选对比与写入 Emby</p></div><div className='flex items-center gap-3'><div className='rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700'><Check className='mr-1 inline size-4' />Emby 连接正常</div><Button variant='outline' disabled={queueQuery.isFetching} onClick={() => void refreshQueue()}><RefreshCw className={`size-4 ${queueQuery.isFetching ? 'animate-spin' : ''}`} />{queueQuery.isFetching ? '刷新中' : '刷新队列'}</Button></div></header>
    <section className='mx-5 mt-2 flex items-center gap-3 rounded-lg border bg-white p-2'><Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className='w-32'><SelectValue placeholder='全部状态' /></SelectTrigger><SelectContent><SelectItem value='all'>全部状态</SelectItem><SelectItem value='pending'>待搜索</SelectItem><SelectItem value='fetched'>已抓取</SelectItem></SelectContent></Select><Select value={categoryFilter} onValueChange={setCategoryFilter}><SelectTrigger className='w-32'><SelectValue placeholder='全部分类' /></SelectTrigger><SelectContent><SelectItem value='all'>全部分类</SelectItem><SelectItem value='japanese_korean'>日韩</SelectItem><SelectItem value='domestic'>国产</SelectItem><SelectItem value='western'>欧美</SelectItem></SelectContent></Select><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder='搜索词 / 番号 / 名称' className='max-w-sm' /><Button variant='outline' onClick={() => setQuery('')}><X className='size-4' />清空</Button></section>
    <section className='grid h-[calc(100vh-158px)] min-h-0 grid-cols-[minmax(220px,.78fr)_minmax(0,1fr)_minmax(0,1.35fr)] gap-2 overflow-hidden px-5 py-2'>
      <CompactQueuePanel items={items} visibleItems={visibleItems} active={active} selectedIds={selectedIds} statusOverrides={statusOverrides} routeFor={routeFor} searchKeywords={searchKeywords} setSearchKeywords={setSearchKeywords} setRouting={setRouting} setActiveId={activateItem} toggle={toggle} searchSelected={searchSelected} setSelectedIds={setSelectedIds} />
      <CompactGroupedResultPanel groups={resultGroups} activeId={active?.notification_id} selectedResult={selectedResult} setActiveId={activateItem} selectCandidate={selectCandidate} clearResults={() => active && setResultsByItem((current) => ({ ...current, [active.notification_id]: [] }))} />
      <MetadataEditorPanel candidate={candidate} beforeItem={beforeItem} autoTranslate={autoTranslate} setAutoTranslate={setAutoTranslate} fieldSelection={fieldSelection} setFieldSelection={setFieldSelection} setCandidate={setCandidate} writeback={writeback} batchWriteback={batchWriteback} batchCount={selectedIds.length} />
    </section>
  </main>
}

function CompactQueuePanel({ items, visibleItems, active, selectedIds, routeFor, searchKeywords, setSearchKeywords, setRouting, setActiveId, toggle, searchSelected, setSelectedIds }: { items: MetadataQueueItem[]; visibleItems: MetadataQueueItem[]; active?: MetadataQueueItem; selectedIds: string[]; statusOverrides: Record<string, string>; routeFor: (item: MetadataQueueItem) => Routing; searchKeywords: Record<string, string>; setSearchKeywords: (value: (current: Record<string, string>) => Record<string, string>) => void; setRouting: (value: (current: Record<string, Routing>) => Record<string, Routing>) => void; setActiveId: (id: string) => void; toggle: (id: string) => void; searchSelected: () => void; setSelectedIds: (ids: string[]) => void }) {
  return <div className='flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-white'><div className='flex justify-between border-b px-3 py-2'><b className='text-sm'>待处理列表</b><span className='text-xs text-slate-500'>共 {items.length} 条</span></div><div className='grid grid-cols-[28px_minmax(0,1fr)_minmax(150px,.65fr)] items-center gap-2 border-b bg-slate-50 px-2 py-1.5 text-[11px] text-slate-500'><Checkbox className='justify-self-center' checked={!!items.length && selectedIds.length === items.length} onCheckedChange={() => setSelectedIds(selectedIds.length === items.length ? [] : items.map((item) => item.notification_id))} /><span>项目</span><span>搜索与数据源</span></div><div className='min-h-0 flex-1 overflow-y-auto'>{visibleItems.map((item) => { const route = routeFor(item); const sourceOptions = item.source_options_by_category[route.category] ?? []; return <div role='button' tabIndex={0} key={item.notification_id} onClick={() => setActiveId(item.notification_id)} className={`relative grid grid-cols-[28px_minmax(0,1fr)_minmax(150px,.65fr)] items-center gap-2 border-b px-2 py-2 text-left ${active?.notification_id === item.notification_id ? 'bg-blue-50' : ''}`}><Checkbox className='justify-self-center' checked={selectedIds.includes(item.notification_id)} onClick={(event) => event.stopPropagation()} onCheckedChange={() => toggle(item.notification_id)} /><div className='flex min-w-0 items-center gap-2'>{item.image_url ? <img src={item.image_url} alt='' className='h-14 w-14 shrink-0 rounded object-cover' /> : <div className='flex h-14 w-14 shrink-0 items-center justify-center rounded bg-slate-100'><Database className='size-4 text-slate-400' /></div>}<div className='min-w-0'><div className='flex items-center gap-1'><button type='button' className='shrink-0 rounded bg-slate-100 px-1 py-0.5 text-[10px]' onClick={(event) => { event.stopPropagation(); void navigator.clipboard.writeText(item.item_id); toast.success(`已复制 Item ID：${item.item_id}`) }}>{item.item_id}</button><Status value={item.status} /></div><span className='mt-1 block h-[3.75rem] overflow-hidden text-sm font-medium leading-5 [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:3]' title={item.item_name}>{item.item_name}</span></div></div><div className='space-y-1' onClick={(event) => event.stopPropagation()}><Input className='h-7 text-xs' value={searchKeywords[item.notification_id] ?? item.search_keyword ?? ''} onChange={(event) => setSearchKeywords((current) => ({ ...current, [item.notification_id]: event.target.value }))} /><div className='flex gap-1'><Select value={route.category} onValueChange={(category) => setRouting((current) => ({ ...current, [item.notification_id]: { category, source: (item.source_options_by_category[category] ?? [])[0]?.value ?? '' } }))}><SelectTrigger className='h-7 min-w-0 flex-1 text-[11px]'><SelectValue /></SelectTrigger><SelectContent>{item.category_options.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent></Select><Select value={route.source || undefined} disabled={!sourceOptions.length} onValueChange={(source) => setRouting((current) => ({ ...current, [item.notification_id]: { ...route, source } }))}><SelectTrigger className='h-7 min-w-0 flex-1 text-[11px]'><SelectValue placeholder='未配置' /></SelectTrigger><SelectContent>{sourceOptions.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent></Select></div></div></div> })}</div><div className='flex gap-2 border-t p-2'><span className='mr-auto self-center text-xs text-blue-600'>已选择 {selectedIds.length} 项</span><Button size='sm' onClick={searchSelected}><Search className='size-3' />批量搜索</Button><Button size='sm' variant='outline' onClick={() => setSelectedIds([])}>取消选择</Button></div></div>
}

function QueuePanel({ items, visibleItems, active, selectedIds, routeFor, searchKeywords, setSearchKeywords, setRouting, setActiveId, toggle, searchSelected, setSelectedIds }: { items: MetadataQueueItem[]; visibleItems: MetadataQueueItem[]; active?: MetadataQueueItem; selectedIds: string[]; routeFor: (item: MetadataQueueItem) => Routing; searchKeywords: Record<string, string>; setSearchKeywords: (value: (current: Record<string, string>) => Record<string, string>) => void; setRouting: (value: (current: Record<string, Routing>) => Record<string, Routing>) => void; setActiveId: (id: string) => void; toggle: (id: string) => void; searchSelected: () => void; setSelectedIds: (ids: string[]) => void }) {
  return <div className='flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-white'><div className='flex justify-between border-b px-4 py-3'><b>待处理列表</b><span className='text-sm text-slate-500'>共 {items.length} 条</span></div><div className='grid grid-cols-[36px_minmax(0,1fr)_minmax(170px,.75fr)] items-center gap-2 border-b bg-slate-50 px-3 py-2 text-xs text-slate-500'><Checkbox className='justify-self-center' checked={!!items.length && selectedIds.length === items.length} onCheckedChange={() => setSelectedIds(selectedIds.length === items.length ? [] : items.map((item) => item.notification_id))} /><span>项目</span><span>搜索与数据源</span></div><div className='min-h-0 flex-1 overflow-y-auto overflow-x-hidden'>{visibleItems.map((item) => { const route = routeFor(item); const sourceOptions = item.source_options_by_category[route.category] ?? []; return <div role='button' tabIndex={0} key={item.notification_id} onClick={() => setActiveId(item.notification_id)} className={`relative grid grid-cols-[36px_minmax(0,1fr)_minmax(170px,.75fr)] items-center gap-2 border-b px-3 py-3 text-left ${active?.notification_id === item.notification_id ? 'bg-blue-50' : ''}`}><Checkbox className='justify-self-center' checked={selectedIds.includes(item.notification_id)} onClick={(event) => event.stopPropagation()} onCheckedChange={() => toggle(item.notification_id)} /><div className='flex min-w-0 items-center gap-3'>{item.image_url ? <img src={item.image_url} alt='' className='h-16 w-28 shrink-0 rounded object-cover' /> : <div className='flex h-16 w-28 shrink-0 items-center justify-center rounded bg-slate-100'><Database className='size-5 text-slate-400' /></div>}<div className='min-w-0'><button type='button' className='rounded bg-slate-100 px-1.5 py-0.5 text-[11px]' onClick={(event) => { event.stopPropagation(); void navigator.clipboard.writeText(item.item_id); toast.success(`已复制 Item ID：${item.item_id}`) }}>{item.item_id}</button><span className='mt-1 block line-clamp-3 text-sm font-medium' title={item.item_name}>{item.item_name}</span></div></div><div className='space-y-1 pr-12' onClick={(event) => event.stopPropagation()}><Input className='h-7' value={searchKeywords[item.notification_id] ?? item.search_keyword ?? ''} onChange={(event) => setSearchKeywords((current) => ({ ...current, [item.notification_id]: event.target.value }))} /><div className='flex gap-1'><Select value={route.category} onValueChange={(category) => setRouting((current) => ({ ...current, [item.notification_id]: { category, source: (item.source_options_by_category[category] ?? [])[0]?.value ?? '' } }))}><SelectTrigger className='h-7 min-w-0 flex-1 text-xs'><SelectValue /></SelectTrigger><SelectContent>{item.category_options.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent></Select><Select value={route.source || undefined} disabled={!sourceOptions.length} onValueChange={(source) => setRouting((current) => ({ ...current, [item.notification_id]: { ...route, source } }))}><SelectTrigger className='h-7 min-w-0 flex-1 text-xs'><SelectValue placeholder='未配置数据源' /></SelectTrigger><SelectContent>{sourceOptions.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent></Select></div></div><Status value={item.status} /></div> })}</div><div className='flex gap-2 border-t p-3'><span className='mr-auto text-sm text-blue-600'>已选择 {selectedIds.length} 项</span><Button onClick={searchSelected}><Search className='size-4' />批量搜索</Button><Button variant='outline' onClick={() => setSelectedIds([])}>取消选择</Button></div></div>
}

function CompactGroupedResultPanel({ groups, activeId, selectedResult, setActiveId, selectCandidate, clearResults }: { groups: ResultGroup[]; activeId?: string; selectedResult: string | null; setActiveId: (id: string) => void; selectCandidate: (result: MetadataSearchResult, resultOwnerId?: string) => void; clearResults: () => void }) {
  return <div className='flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-white'><div className='flex justify-between border-b px-3 py-2'><b className='text-sm'>搜索结果</b><Button size='icon' variant='ghost' onClick={clearResults}><X className='size-4' /></Button></div><div className='min-h-0 flex-1 space-y-2 overflow-y-auto p-2'>{groups.length ? groups.map((group) => <details key={group.item.notification_id} open={group.item.notification_id === activeId} className={`rounded-lg border ${group.item.notification_id === activeId ? 'border-blue-400 bg-blue-50/40' : 'bg-white'}`} onToggle={(event) => { if ((event.currentTarget as HTMLDetailsElement).open) setActiveId(group.item.notification_id) }}><summary className='cursor-pointer list-none px-2 py-1.5 text-xs font-semibold'>{group.item.item_id} {group.item.item_name}<span className='ml-1 font-normal text-slate-500'>（{group.results.length}）</span></summary><div className='grid grid-cols-2 gap-2 border-t p-2'>{group.results.length ? group.results.map((result) => <div key={`${group.item.notification_id}-${result.source}-${result.source_id}`} className='flex flex-col overflow-hidden rounded-md border bg-white shadow-sm'><div className='flex h-36 items-center justify-center overflow-hidden bg-slate-100'>{result.image_urls[0] ? <img src={apiClient.metadataImageUrl(result.image_urls[0], result.detail_url)} alt='' className='size-full object-contain' /> : <Database className='size-7 text-slate-400' />}</div><div className='flex min-w-0 flex-1 flex-col p-2'><div className='mb-1 flex min-h-5 flex-wrap gap-1'>{result.statuses.length ? result.statuses.map((status) => <span key={status} className='rounded border bg-slate-50 px-1 py-0.5 text-[10px] text-slate-600'>{status}</span>) : <span className='text-[10px] text-slate-400'>无状态</span>}</div><div className='mb-1 flex items-center gap-1 text-[10px] text-slate-500'><SourceIcon source={result.source} className='size-3' />{result.source}</div><b className='line-clamp-3 text-xs leading-4'>{result.title}</b><div className='mt-auto flex items-center justify-between gap-1 pt-2 text-[11px]'><span className='text-slate-500'>{result.release_date ?? '日期未知'}</span><span className='font-semibold text-emerald-700'>{result.price_yen ? `¥${result.price_yen.toLocaleString()}` : '价格未知'}</span></div><Button size='sm' className='mt-2 w-full' variant={selectedResult === result.source_id && group.item.notification_id === activeId ? 'default' : 'outline'} onClick={() => { setActiveId(group.item.notification_id); selectCandidate(result, group.item.notification_id) }}>{selectedResult === result.source_id && group.item.notification_id === activeId ? '已选择' : '选择并抓取'} <ExternalLink className='ml-1 size-3' /></Button></div></div>) : <p className='col-span-2 p-2 text-sm text-slate-500'>该项目没有匹配结果。</p>}</div></details>) : <Empty title='尚未加载搜索结果' text='勾选左侧项目后，点击“批量搜索”。' />}</div></div>
}

export function GroupedResultPanel({ groups, activeId, selectedResult, setActiveId, selectCandidate, clearResults }: { groups: ResultGroup[]; activeId?: string; selectedResult: string | null; setActiveId: (id: string) => void; selectCandidate: (result: MetadataSearchResult, resultOwnerId?: string) => void; clearResults: () => void }) {
  return <div className='flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-white'><div className='flex justify-between border-b px-4 py-3'><b>搜索结果</b><Button size='icon' variant='ghost' onClick={clearResults}><X className='size-4' /></Button></div><div className='min-h-0 flex-1 space-y-2 overflow-y-auto p-3'>{groups.length ? groups.map((group) => <details key={group.item.notification_id} open={group.item.notification_id === activeId} className={`rounded-lg border ${group.item.notification_id === activeId ? 'border-blue-400 bg-blue-50/40' : 'bg-white'}`} onToggle={(event) => { if ((event.currentTarget as HTMLDetailsElement).open) setActiveId(group.item.notification_id) }}><summary className='cursor-pointer list-none px-3 py-2 text-sm font-semibold'>{group.item.item_name}<span className='ml-2 text-xs font-normal text-slate-500'>（{group.results.length} 条结果）</span></summary><div className='space-y-2 border-t p-2'>{group.results.length ? group.results.map((result) => <div key={`${group.item.notification_id}-${result.source}-${result.source_id}`} className='flex items-center gap-2 rounded border bg-white p-2'><div className='flex h-16 w-24 shrink-0 items-center justify-center overflow-hidden rounded bg-slate-100'>{result.image_urls[0] ? <img src={apiClient.metadataImageUrl(result.image_urls[0], result.detail_url)} alt='' className='size-full object-contain' /> : <Database className='size-5 text-slate-400' />}</div><div className='min-w-0 flex-1'><b className='line-clamp-2 text-xs'>{result.title}</b><p className='mt-1 line-clamp-2 text-[11px] text-slate-500'>{result.release_date ?? '日期未知'} · {result.statuses.join(' · ')}</p></div><Button size='sm' className='shrink-0' variant={selectedResult === result.source_id && group.item.notification_id === activeId ? 'default' : 'outline'} onClick={() => { setActiveId(group.item.notification_id); selectCandidate(result, group.item.notification_id) }}>{selectedResult === result.source_id && group.item.notification_id === activeId ? '已选择' : '选择并抓取'} <ExternalLink className='ml-1 size-3' /></Button></div>) : <p className='p-2 text-sm text-slate-500'>该项目没有匹配结果。</p>}</div></details>) : <Empty title='尚未加载搜索结果' text='勾选左侧项目后，点击“批量搜索”。' />}</div></div>
}

function MetadataEditorPanel({ candidate, beforeItem, autoTranslate, setAutoTranslate, setCandidate, writeback, batchWriteback, batchCount }: { candidate: MetadataCandidate | null; beforeItem: Record<string, unknown>; autoTranslate: boolean; setAutoTranslate: (value: boolean) => void; fieldSelection?: string[]; setFieldSelection?: (value: (current: string[]) => string[]) => void; setCandidate: (value: (current: MetadataCandidate | null) => MetadataCandidate | null) => void; writeback: () => void; batchWriteback: () => void; batchCount: number }) {
  return <MetadataEditorPanelNoTabs candidate={candidate} beforeItem={beforeItem} autoTranslate={autoTranslate} setAutoTranslate={setAutoTranslate} setCandidate={setCandidate} writeback={writeback} batchWriteback={batchWriteback} batchCount={batchCount} />
}

function MetadataEditorPanelLegacy({ candidate, beforeItem, autoTranslate, setAutoTranslate, setCandidate, writeback, batchWriteback, batchCount }: { candidate: MetadataCandidate | null; beforeItem: Record<string, unknown>; autoTranslate: boolean; setAutoTranslate: (value: boolean) => void; fieldSelection?: string[]; setFieldSelection?: (value: (current: string[]) => string[]) => void; setCandidate: (value: (current: MetadataCandidate | null) => MetadataCandidate | null) => void; writeback: () => void; batchWriteback: () => void; batchCount: number }) {
  return <div className='flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-white'><div className='border-b px-4 py-3'><b>编辑元数据</b></div><Tabs defaultValue='basic' className='flex min-h-0 flex-1 flex-col'><TabsList className='justify-start rounded-none border-b bg-white px-3'><TabsTrigger value='basic'>基本信息</TabsTrigger><TabsTrigger value='images'>演员图片</TabsTrigger><TabsTrigger value='history'>操作记录</TabsTrigger></TabsList><TabsContent value='basic' className='min-h-0 flex-1 overflow-y-auto p-4'>{candidate ? <><CoverPreview candidate={candidate} /><div className='grid grid-cols-[76px_minmax(0,1fr)_minmax(0,1fr)] gap-2 border-b pb-2 text-xs text-slate-500'><span>字段</span><span>当前 Emby 值</span><span>候选值</span></div><div className='divide-y'>{fields.map(([key, label]) => <FieldRow key={key} field={key} label={label} candidate={candidate} beforeItem={beforeItem} hideCheckbox onChange={(value) => setCandidate((current) => current ? updateCandidate(current, key, value) : current)} />)}</div><details className='mt-4 rounded border bg-amber-50 p-3 text-xs'><summary className='cursor-pointer font-semibold text-amber-800'>解析结果回报（请逐项核对）</summary><div className='mt-2 space-y-1'>{Object.entries(candidate.parse_report ?? candidateValues(candidate)).map(([key, value]) => <div key={key} className='grid grid-cols-[120px_minmax(0,1fr)] gap-2 border-b border-amber-100 py-1'><span className='font-medium text-amber-900'>{key}</span><span className='break-all whitespace-pre-wrap'>{typeof value === 'object' ? JSON.stringify(value) : String(value ?? '—')}</span></div>)}</div></details><div className='mt-4 rounded border bg-slate-50 p-3 text-xs'>数据源：{candidate.source}　编号：{candidate.source_id}<br />产品番号：{candidate.product_number ?? '—'}<br /><a href={candidate.raw_url} target='_blank' rel='noreferrer' className='text-blue-600'>打开来源页</a></div></> : <Empty title='等待候选详情' text='从中栏选择一条搜索结果。' />}</TabsContent><TabsContent value='images' className='min-h-0 flex-1 overflow-y-auto p-4 text-sm text-slate-500'>{candidate ? <div className='space-y-3'>{candidate.people.map((person, index) => <div key={`${person.name}-${index}`} className='flex items-center gap-3 rounded border p-2'><div className='flex size-12 items-center justify-center rounded bg-slate-100'><Database className='size-4 text-slate-400' /></div><span>{person.name}</span></div>)}</div> : <Empty title='等待候选详情' text='从中栏选择一条搜索结果。' />}</TabsContent><TabsContent value='history' className='p-4 text-sm text-slate-500'>写入完成后将在此展示本次字段变更记录。</TabsContent></Tabs><div className='flex items-center justify-end gap-2 border-t p-3'><div className='mr-auto flex items-center gap-2 text-sm'><span>自动翻译简介</span><Button type='button' size='sm' variant={autoTranslate ? 'default' : 'outline'} onClick={() => setAutoTranslate(!autoTranslate)}>{autoTranslate ? '已开启' : '已关闭'}</Button></div><Button variant='outline' disabled={!candidate}>保存为草稿</Button><Button variant='outline' disabled={batchCount < 2} onClick={batchWriteback}>批量写入 Emby</Button><Button onClick={writeback} disabled={!candidate}><Upload className='size-4' />确认写入 Emby</Button></div></div>
}

function ResultPanel({ results, active, selectedResult, selectCandidate, clearResults }: { results: MetadataSearchResult[]; active?: MetadataQueueItem; selectedResult: string | null; selectCandidate: (result: MetadataSearchResult) => void; clearResults: () => void }) {
  return <div className='flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-white'><div className='flex justify-between border-b px-4 py-3'><b>搜索结果</b><Button size='icon' variant='ghost' onClick={clearResults}><X className='size-4' /></Button></div><div className='min-h-0 flex-1 space-y-2 overflow-y-auto p-3'>{results.length ? results.map((result) => <div key={`${result.source}-${result.source_id}`} className='flex items-center gap-3 rounded-lg border p-3'><div className='flex h-24 w-40 shrink-0 items-center justify-center overflow-hidden rounded bg-slate-100'>{result.image_urls[0] ? <img src={apiClient.metadataImageUrl(result.image_urls[0], result.detail_url)} alt='' className='size-full object-contain' /> : <Database className='size-6 text-slate-400' />}</div><div className='min-w-0 flex-1'><b className='line-clamp-2 text-sm'>{result.title}</b><p className='mt-1 text-xs text-slate-500'>{result.release_date ?? '日期未知'} · {result.statuses.join(' · ')}</p></div><Button size='sm' className='shrink-0' variant={selectedResult === result.source_id ? 'default' : 'outline'} onClick={() => selectCandidate(result)}>{selectedResult === result.source_id ? '已选择' : '选择并抓取'} <ExternalLink className='ml-1 size-3' /></Button></div>) : <Empty title='尚未加载搜索结果' text={`勾选左侧项目后，点击“批量搜索”。${active ? '' : ''}`} />}</div></div>
}

function EditorPanel({ candidate, beforeItem, fieldSelection, setFieldSelection, overwrite, setOverwrite, setCandidate, writeback }: { candidate: MetadataCandidate | null; beforeItem: Record<string, unknown>; fieldSelection: string[]; setFieldSelection: (value: (current: string[]) => string[]) => void; overwrite: boolean; setOverwrite: (value: boolean) => void; setCandidate: (value: (current: MetadataCandidate | null) => MetadataCandidate | null) => void; writeback: () => void }) {
  return <div className='flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-white'><div className='border-b px-4 py-3'><b>编辑元数据</b></div><Tabs defaultValue='basic' className='flex min-h-0 flex-1 flex-col'><TabsList className='justify-start rounded-none border-b bg-white px-3'><TabsTrigger value='basic'>基本信息</TabsTrigger><TabsTrigger value='images'>演员图片</TabsTrigger><TabsTrigger value='history'>操作记录</TabsTrigger></TabsList><TabsContent value='basic' className='min-h-0 flex-1 overflow-y-auto p-4'>{candidate ? <><CoverPreview candidate={candidate} /><div className='mb-3 flex justify-between rounded border bg-slate-50 p-2 text-sm'><span>覆盖模式</span><button onClick={() => setOverwrite(!overwrite)}>{overwrite ? '覆盖已选字段' : '仅填充空字段'}</button></div><div className='grid grid-cols-[28px_110px_minmax(0,1fr)_minmax(0,1fr)] gap-2 border-b pb-2 text-xs text-slate-500'><span /><span>字段</span><span>当前 Emby 值</span><span>候选值</span></div><div className='divide-y'>{fields.map(([key, label]) => <FieldRow key={key} field={key} label={label} candidate={candidate} beforeItem={beforeItem} checked={fieldSelection.includes(key)} onCheck={() => setFieldSelection((current) => current.includes(key) ? current.filter((value) => value !== key) : [...current, key])} onChange={(value) => setCandidate((current) => current ? updateCandidate(current, key, value) : current)} />)}</div><div className='mt-4 rounded border bg-slate-50 p-3 text-xs'>数据源：{candidate.source}　编号：{candidate.source_id}<br />产品番号：{candidate.product_number ?? '—'}<br /><a href={candidate.raw_url} target='_blank' rel='noreferrer' className='text-blue-600'>打开来源页</a></div></> : <Empty title='等待候选详情' text='从中栏选择一条搜索结果。' />}</TabsContent><TabsContent value='images' className='min-h-0 flex-1 overflow-y-auto p-4 text-sm text-slate-500'>{candidate ? <div className='space-y-3'>{candidate.people.map((person, index) => <div key={`${person.name}-${index}`} className='flex items-center gap-3 rounded border p-2'><div className='flex size-12 items-center justify-center rounded bg-slate-100'><Database className='size-4 text-slate-400' /></div><span>{person.name}</span></div>)}</div> : <Empty title='等待候选详情' text='从中栏选择一条搜索结果。' />}</TabsContent><TabsContent value='history' className='p-4 text-sm text-slate-500'>写入完成后将在此展示本次字段变更记录。</TabsContent></Tabs><div className='flex justify-end gap-3 border-t p-3'><Button variant='outline' disabled={!candidate}>保存为草稿</Button><Button onClick={writeback} disabled={!candidate}><Upload className='size-4' />确认写入 Emby</Button></div></div>
}

function ExternalIdsView({ value }: { value: unknown }) {
  const entries = value && typeof value === 'object' ? Object.entries(value as Record<string, unknown>) : []
  return <div className='space-y-1 text-xs'>{entries.length ? entries.map(([key, item]) => <div key={key} className='grid grid-cols-[100px_minmax(0,1fr)] gap-2'><span className='font-medium text-slate-500'>{key}</span><span className='break-all'>{String(item ?? '') || '—'}</span></div>) : <span className='text-slate-400'>—</span>}</div>
}

function ExternalIdsEditor({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  let entries: Array<[string, string]> = []
  try {
    const parsed = JSON.parse(value) as Record<string, unknown>
    entries = Object.entries(parsed).map(([key, item]) => [key, String(item ?? '')])
  } catch {
    return <textarea className='h-20 w-full rounded border px-2 py-1 text-xs' value={value} onChange={(event) => onChange(event.target.value)} />
  }
  return <div className='space-y-1 rounded border bg-slate-50 p-2'>{entries.map(([key, item]) => <div key={key} className='grid grid-cols-[100px_minmax(0,1fr)] items-center gap-2'><span className='text-xs font-medium text-slate-600'>{key}</span><Input className='h-7 text-xs' value={item} onChange={(event) => { const next = Object.fromEntries(entries.map(([entryKey, entryValue]) => [entryKey, entryKey === key ? event.target.value : entryValue])); onChange(JSON.stringify(next, null, 2)) }} /></div>)}</div>
}

function TagEditor({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [draft, setDraft] = useState('')
  const values = value.split(/[、,，]/).map((item) => item.trim()).filter(Boolean)
  const add = () => { const next = draft.trim(); if (!next) return; onChange([...values, next].filter((item, index, list) => list.indexOf(item) === index).join('、')); setDraft('') }
  return <div className='flex min-h-9 flex-wrap items-center gap-1 rounded border p-2'>{values.map((tag) => <span key={tag} className='inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700'>{tag}<button type='button' className='text-blue-500 hover:text-red-600' onClick={() => onChange(values.filter((item) => item !== tag).join('、'))}><X className='size-3' /></button></span>)}<input className='min-w-20 flex-1 bg-transparent text-xs outline-none' value={draft} placeholder={values.length ? '回车添加' : '输入后回车添加'} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); add() } }} /></div>
}

export function OverviewEditorLegacy({ value, currentValue, onChange, onTranslate }: { value: string; currentValue: string; onChange: (value: string) => void; onTranslate: (text: string) => Promise<string> }) {
  const separator = '\n\n---\n\n'
  const splitValue = (input: string) => { const index = input.indexOf(separator); return index >= 0 ? { translation: input.slice(0, index), original: input.slice(index + separator.length) } : { translation: '', original: input } }
  const [parts, setParts] = useState(() => splitValue(value))
  const [translating, setTranslating] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [showFinalValue, setShowFinalValue] = useState(false)
  useEffect(() => setParts(splitValue(value)), [value])
  useEffect(() => { if (!expanded) setShowFinalValue(false) }, [expanded])
  const commit = (translation: string, original: string) => { setParts({ translation, original }); onChange(translation.trim() ? `${translation.trim()}${separator}${original}` : original) }
  const translate = async () => { if (!parts.original.trim()) return; setTranslating(true); try { commit(await onTranslate(parts.original), parts.original) } catch (error) { toast.error(error instanceof Error ? error.message : '翻译失败') } finally { setTranslating(false) } }
  return <><div className='overview-editor flex h-full min-h-0 w-full flex-col gap-1'><div className='flex shrink-0 items-center justify-between text-[11px] text-slate-500'><span>翻译</span><div className='flex items-center gap-1'><Button type='button' size='sm' variant='outline' className='h-6 px-2 text-[11px]' disabled={translating || !parts.original.trim()} onClick={() => void translate()}>{translating ? '翻译中…' : '翻译'}</Button><Button type='button' size='icon' variant='ghost' className='size-6' title='放大查看当前 Emby 值和候选值' onClick={() => setExpanded(true)}><Maximize2 className='size-3.5' /></Button></div></div><textarea className='overview-editor-textarea resize-none rounded border px-2 py-1 text-sm' value={parts.translation} placeholder='点击“翻译”生成中文，也可以手动修改' onChange={(event) => commit(event.target.value, parts.original)} /><div className='shrink-0 text-[11px] text-slate-500'>原文</div><textarea className='overview-editor-textarea resize-none rounded border px-2 py-1 text-sm ' value={parts.original} placeholder='原文' onChange={(event) => commit(parts.translation, event.target.value)} /></div><Dialog open={expanded} onOpenChange={setExpanded}><DialogContent className='h-[85vh] w-[92vw] max-w-[1500px] sm:max-w-[1500px]'><DialogHeader><div className='flex items-center justify-between pr-8'><DialogTitle>简介对比</DialogTitle><Button type='button' size='sm' variant='outline' onClick={() => setShowFinalValue((visible) => !visible)}>{showFinalValue ? '返回翻译和原文' : '查看最终写入值'}</Button></div></DialogHeader><div className='grid min-h-0 flex-1 grid-cols-1 gap-4 md:grid-cols-3'><div className='min-w-0'><div className='mb-1 text-sm font-medium'>当前 Emby 值</div><textarea className='h-[68vh] w-full resize-none rounded border p-3 text-sm' value={currentValue} readOnly /></div>{showFinalValue ? <div className='min-w-0 md:col-span-2'><div className='mb-1 text-sm font-medium'>最终写入值</div><textarea className='h-[68vh] w-full resize-none rounded border bg-amber-50 p-3 text-sm' value={value} readOnly /></div> : <><div className='min-w-0'><div className='mb-1 flex items-center justify-between text-sm font-medium'><span>翻译</span><Button type='button' size='sm' variant='outline' className='h-7 px-2 text-xs' disabled={translating || !parts.original.trim()} onClick={() => void translate()}>{translating ? '翻译中…' : '翻译'}</Button></div><textarea className='h-[68vh] w-full resize-none rounded border p-3 text-sm' value={parts.translation} onChange={(event) => commit(event.target.value, parts.original)} /></div><div className='min-w-0'><div className='mb-1 text-sm font-medium'>原文</div><textarea className='h-[68vh] w-full resize-none rounded border p-3 text-sm' value={parts.original} onChange={(event) => commit(parts.translation, event.target.value)} /></div></>}</div></DialogContent></Dialog></>
}

function OverviewEditor({ value, currentValue, title, onChange, onTranslate, onTitleTranslated }: { value: string; currentValue: string; title: string; onChange: (value: string) => void; onTranslate: (text: string) => Promise<string>; onTitleTranslated: (value: string) => void }) {
  const separator = '\n\n---\n\n'
  const splitValue = (input: string) => { const index = input.indexOf(separator); return index >= 0 ? { translation: input.slice(0, index), original: input.slice(index + separator.length) } : { translation: '', original: input } }
  const [parts, setParts] = useState(() => splitValue(value))
  const [translating, setTranslating] = useState(false)
  const [titleTranslating, setTitleTranslating] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [showFinalValue, setShowFinalValue] = useState(false)
  useEffect(() => setParts(splitValue(value)), [value])
  useEffect(() => { if (!expanded) setShowFinalValue(false) }, [expanded])
  const commit = (translation: string, original: string) => { setParts({ translation, original }); onChange(translation.trim() ? `${translation.trim()}${separator}${original}` : original) }
  const translate = async () => { if (!parts.original.trim()) return; setTranslating(true); try { commit(await onTranslate(parts.original), parts.original) } catch (error) { toast.error(error instanceof Error ? error.message : '翻译失败') } finally { setTranslating(false) } }
  const translateTitle = async () => { const titleWithoutPrefix = title.replace(/^【[^】]*】\s*/, '').trim(); if (!titleWithoutPrefix) return; setTitleTranslating(true); try { onTitleTranslated(await onTranslate(titleWithoutPrefix)) } catch (error) { toast.error(error instanceof Error ? error.message : '标题翻译失败') } finally { setTitleTranslating(false) } }
  return <><div className='overview-editor flex h-full min-h-0 w-full flex-col gap-1'><div className='flex shrink-0 items-center justify-between text-[11px] text-slate-500'><span>翻译</span><div className='flex items-center gap-1'><Button type='button' size='sm' variant='outline' className='h-6 px-2 text-[11px]' disabled={titleTranslating || !title.trim()} onClick={() => void translateTitle()}>{titleTranslating ? '标题翻译中…' : '标题翻译'}</Button><Button type='button' size='sm' variant='outline' className='h-6 px-2 text-[11px]' disabled={translating || !parts.original.trim()} onClick={() => void translate()}>{translating ? 'AI翻译中…' : 'AI翻译'}</Button><Button type='button' size='icon' variant='ghost' className='size-6' title='放大查看当前 Emby 值和候选值' onClick={() => setExpanded(true)}><Maximize2 className='size-3.5' /></Button></div></div><textarea className='overview-editor-textarea resize-none rounded border px-2 py-1 text-sm' value={parts.translation} placeholder='点击“AI翻译”生成中文，也可以手动修改' onChange={(event) => commit(event.target.value, parts.original)} /><div className='shrink-0 text-[11px] text-slate-500'>原文</div><textarea className='overview-editor-textarea resize-none rounded border px-2 py-1 text-sm' value={parts.original} placeholder='原文' onChange={(event) => commit(parts.translation, event.target.value)} /></div><Dialog open={expanded} onOpenChange={setExpanded}><DialogContent className='h-[85vh] w-[92vw] max-w-[1500px] sm:max-w-[1500px]'><DialogHeader><div className='flex items-center justify-between pr-8'><DialogTitle>简介对比</DialogTitle><div className='flex items-center gap-2'><Button type='button' size='sm' variant='outline' disabled={titleTranslating || !title.trim()} onClick={() => void translateTitle()}>{titleTranslating ? '标题翻译中…' : '标题翻译'}</Button><Button type='button' size='sm' variant='outline' disabled={translating || !parts.original.trim()} onClick={() => void translate()}>{translating ? 'AI翻译中…' : 'AI翻译'}</Button><Button type='button' size='sm' variant='outline' onClick={() => setShowFinalValue((visible) => !visible)}>{showFinalValue ? '返回翻译和原文' : '查看最终写入值'}</Button></div></div></DialogHeader><div className='grid min-h-0 flex-1 grid-cols-1 gap-4 md:grid-cols-3'><div className='min-w-0'><div className='mb-1 text-sm font-medium'>当前 Emby 值</div><textarea className='h-[68vh] w-full resize-none rounded border p-3 text-sm' value={currentValue} readOnly /></div>{showFinalValue ? <div className='min-w-0 md:col-span-2'><div className='mb-1 text-sm font-medium'>最终写入值</div><textarea className='h-[68vh] w-full resize-none rounded border bg-amber-50 p-3 text-sm' value={value} readOnly /></div> : <><div className='min-w-0'><div className='mb-1 text-sm font-medium'>翻译</div><textarea className='h-[68vh] w-full resize-none rounded border p-3 text-sm' value={parts.translation} onChange={(event) => commit(event.target.value, parts.original)} /></div><div className='min-w-0'><div className='mb-1 text-sm font-medium'>原文</div><textarea className='h-[68vh] w-full resize-none rounded border p-3 text-sm' value={parts.original} onChange={(event) => commit(parts.translation, event.target.value)} /></div></>}</div></DialogContent></Dialog></>
}

type PersonCardData = MetadataPerson & { image_url?: string; ImageUrl?: string; PrimaryImageUrl?: string }

function normalizePeople(value: unknown): PersonCardData[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((item) => {
    if (!item || typeof item !== 'object') return []
    const person = item as Record<string, unknown>
    const name = String(person.Name ?? person.name ?? '').trim()
    if (!name) return []
    return [{
      name,
      id: typeof person.Id === 'string' ? person.Id : typeof person.id === 'string' ? person.id : undefined,
      role: typeof person.Role === 'string' ? person.Role : typeof person.role === 'string' ? person.role : undefined,
      type: typeof person.Type === 'string' ? person.Type : typeof person.type === 'string' ? person.type : undefined,
      image_url: typeof person.ImageUrl === 'string' ? person.ImageUrl : typeof person.image_url === 'string' ? person.image_url : undefined,
      ImageUrl: typeof person.ImageUrl === 'string' ? person.ImageUrl : undefined,
      PrimaryImageUrl: typeof person.PrimaryImageUrl === 'string' ? person.PrimaryImageUrl : undefined,
      PrimaryImageTag: typeof person.PrimaryImageTag === 'string' ? person.PrimaryImageTag : undefined,
    }]
  })
}

function PersonImage({ person, referer, editable, onImageChange }: { person: PersonCardData; referer?: string; editable?: boolean; onImageChange?: (imageData: string) => void }) {
  const source = person.image_data ? `data:image/jpeg;base64,${person.image_data}` : person.ImageUrl ?? person.PrimaryImageUrl ?? person.image_url
  const imageUrl = source && /^https?:\/\//i.test(source) ? apiClient.metadataImageUrl(source, referer ?? '') : source
  const selectImage = async (file: File) => {
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result))
      reader.onerror = () => reject(reader.error)
      reader.readAsDataURL(file)
    })
    onImageChange?.(dataUrl.split(',', 2)[1] ?? '')
  }
  return <label className={`relative flex h-32 w-24 shrink-0 items-center justify-center overflow-hidden rounded border bg-slate-100 ${editable ? 'cursor-pointer hover:border-blue-400 hover:ring-2 hover:ring-blue-100' : ''}`} title={editable ? '点击上传演员图片' : undefined}>
    {imageUrl ? <img src={imageUrl} alt={person.name} className='size-full object-cover' /> : <span className='text-xs text-slate-400'>无图片</span>}
    {editable && <input type='file' accept='image/*' className='sr-only' onChange={(event) => { const file = event.target.files?.[0]; if (file) void selectImage(file); event.target.value = '' }} />}
  </label>
}

function PersonCard({ person, referer, removable, editable, onRemove, onImageChange, onNameChange }: { person: PersonCardData; referer?: string; removable?: boolean; editable?: boolean; onRemove?: () => void; onImageChange?: (imageData: string) => void; onNameChange?: (name: string) => void }) {
  return <div className='group relative flex w-36 shrink-0 flex-col items-center gap-2 rounded-lg border bg-white p-2 shadow-sm'>
    {removable && <button type='button' aria-label={`移除${person.name}`} className='pointer-events-none absolute right-1 top-1 z-10 rounded-full bg-white p-1 text-slate-500 opacity-0 shadow transition-opacity group-hover:pointer-events-auto group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:opacity-100 hover:text-red-500' onClick={onRemove}><X className='size-3.5' /></button>}
    {editable ? <input value={person.name} aria-label={`编辑${person.name}`} className='w-full min-w-0 border-0 border-b border-solid border-slate-400 bg-transparent px-1 text-center text-sm font-semibold outline-none focus:border-blue-500' onChange={(event) => onNameChange?.(event.target.value)} /> : <div className='max-w-full truncate px-1 text-sm font-semibold' title={person.name}>{person.name}</div>}
    <PersonImage person={person} referer={referer} editable={editable} onImageChange={onImageChange} />
  </div>
}

function PeoplePreview({ people, currentPeople = [], referer, editable, onChange }: { people: PersonCardData[]; currentPeople?: PersonCardData[]; referer?: string; editable?: boolean; onChange?: (people: MetadataPerson[]) => void }) {
  const [name, setName] = useState('')
  const addPerson = () => {
    const nextName = name.trim()
    if (!nextName || !onChange) return
    const existingPerson = currentPeople.find((person) => person.name.trim().toLocaleLowerCase() === nextName.toLocaleLowerCase())
    onChange([...people, existingPerson ? { ...existingPerson, name: nextName, type: 'Actor' } : { name: nextName, type: 'Actor' }])
    setName('')
  }
  const scrollHorizontally = (event: WheelEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    const delta = event.deltaY || event.deltaX
    if (!delta) return
    event.currentTarget.scrollLeft += delta
  }
  return <div onWheelCapture={scrollHorizontally} className='flex min-h-52 w-full min-w-0 overscroll-none gap-3 overflow-x-auto overflow-y-hidden rounded-lg border border-slate-200 bg-slate-50/60 p-3'>
    {people.map((person, index) => <PersonCard key={`${person.id ?? index}`} person={person} referer={referer} removable={editable} editable={editable} onRemove={() => onChange?.(people.filter((_, itemIndex) => itemIndex !== index))} onNameChange={(name) => onChange?.(people.map((item, itemIndex) => itemIndex === index ? { ...item, name } : item))} onImageChange={(imageData) => onChange?.(people.map((item, itemIndex) => itemIndex === index ? { ...item, image_data: imageData, image_url: undefined } : item))} />)}
    {editable && <div className='group flex w-36 shrink-0 flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-blue-300 bg-gradient-to-b from-blue-50 to-white p-3 shadow-sm transition hover:border-blue-500 hover:shadow-md'>
      <div className='flex size-10 items-center justify-center rounded-full bg-blue-100 text-2xl font-light leading-none text-blue-600 transition group-hover:scale-105'>＋</div>
      <Input value={name} placeholder='输入演员名字' className='h-8 border-blue-200 bg-white text-xs shadow-none focus-visible:ring-blue-200' onChange={(event) => setName(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); addPerson() } }} />
      <button type='button' className='text-xs font-medium text-blue-600 hover:text-blue-700 disabled:text-slate-300' disabled={!name.trim()} onClick={addPerson}>添加演员</button>
    </div>}
    {!people.length && !editable && <span className='self-center text-sm text-slate-400'>暂无演员</span>}
  </div>
}

function FieldRow({ field, label, candidate, beforeItem, checked, onCheck, hideCheckbox = false, onChange }: { field: FieldKey; label: string; candidate: MetadataCandidate; beforeItem: Record<string, unknown>; checked?: boolean; onCheck?: () => void; hideCheckbox?: boolean; onChange: (value: FieldValue) => void }) {
  const value = candidateValues(candidate)[field]
  const embyField: Record<FieldKey, string> = { Name: 'Name', OriginalTitle: 'OriginalTitle', Taglines: 'Taglines', Overview: 'Overview', ProductionYear: 'ProductionYear', PremiereDate: 'PremiereDate', Genres: 'Genres', Studios: 'Studios', People: 'People', Tags: 'TagItems', CommunityRating: 'CommunityRating', OfficialRating: 'OfficialRating', CustomRating: 'CustomRating', SortName: 'SortName', ForcedSortName: 'ForcedSortName', ExternalIds: 'ProviderIds' }
  const current = beforeItem[embyField[field]]
  const currentText = Array.isArray(current) ? current.map((item) => typeof item === 'object' && item ? String((item as { Name?: string }).Name ?? '') : String(item)).filter(Boolean).join('、') : typeof current === 'object' && current ? JSON.stringify(current, null, 2) : current === undefined || current === null ? '' : String(current)
  const multiline = field === 'Name' || field === 'OriginalTitle' || field === 'Taglines' || field === 'Overview'
  const people = field === 'People' ? normalizePeople(current) : []
  const candidatePeople = field === 'People' ? candidate.people : []
  const cellClass = field === 'People' ? 'h-54 max-h-54' : field === 'Overview' ? 'h-52 max-h-52' : multiline ? 'h-20 max-h-20' : 'min-h-9'
  const editor = field === 'People' ? <PeoplePreview people={candidatePeople} currentPeople={people} referer={candidate.raw_url} editable onChange={onChange} /> : collectionFields.has(field) ? <TagEditor value={value} onChange={onChange} /> : field === 'Overview' ? <OverviewEditor value={value} currentValue={currentText} title={candidate.original_title} onChange={onChange} onTranslate={(text) => apiClient.translateMetadata(text)} onTitleTranslated={(translatedTitle) => window.dispatchEvent(new CustomEvent('metadata-title-translated', { detail: translatedTitle }))} /> : multiline ? <textarea className='h-full max-h-20 w-full resize-none overflow-y-auto rounded border px-2 py-1 text-sm' value={value} onChange={(event) => onChange(event.target.value)} /> : field === 'ExternalIds' ? <ExternalIdsEditor value={value} onChange={onChange} /> : field === 'OfficialRating' || field === 'CustomRating' ? <Select value={value || '__empty__'} onValueChange={(next) => onChange(next === '__empty__' ? '' : next)}><SelectTrigger className='h-9'><SelectValue placeholder='选择评分' /></SelectTrigger><SelectContent>{ratingOptions.map((option) => <SelectItem key={option || '__empty__'} value={option || '__empty__'}>{option || '未设置'}</SelectItem>)}</SelectContent></Select> : <Input className='h-9' type={field === 'CommunityRating' ? 'number' : 'text'} value={value} onChange={(event) => onChange(event.target.value)} />
  const gridClass = hideCheckbox ? 'grid-cols-[76px_minmax(0,1fr)_minmax(0,1fr)]' : 'grid-cols-[28px_76px_minmax(0,1fr)_minmax(0,1fr)]'
  const row = <div className={`grid ${gridClass} items-stretch gap-2 py-2`}>{!hideCheckbox && <Checkbox checked={checked} onCheckedChange={onCheck} />}<label className='self-center text-sm'>{label}</label><div className={`${cellClass} ${field === 'People' ? 'min-w-0' : multiline ? '' : 'flex items-center'} overflow-x-hidden overflow-y-auto break-words whitespace-pre-wrap text-sm text-slate-500`}>{field === 'People' ? <PeoplePreview people={people} referer={candidate.raw_url} /> : field === 'ExternalIds' ? <ExternalIdsView value={current} /> : collectionFields.has(field) ? <ValueChips value={currentText} /> : currentText || '—'}</div><div className={`${cellClass} ${field === 'People' ? 'min-w-0' : multiline ? '' : 'flex items-center'} min-w-0 overflow-hidden`}>{editor}</div></div>
  return field === 'SortName' || field === 'ForcedSortName' || field === 'ExternalIds' ? <details className='rounded border-b px-2'><summary className='cursor-pointer py-2 text-sm font-medium text-slate-600'>{label}</summary>{row}</details> : row
}

export function FieldRowLegacy({ field, label, candidate, beforeItem, checked, onCheck, hideCheckbox = false, onChange }: { field: FieldKey; label: string; candidate: MetadataCandidate; beforeItem: Record<string, unknown>; checked?: boolean; onCheck?: () => void; hideCheckbox?: boolean; onChange: (value: string) => void }) {
  const value = candidateValues(candidate)[field]
  const embyField: Record<FieldKey, string> = { Name: 'Name', OriginalTitle: 'OriginalTitle', Taglines: 'Taglines', Overview: 'Overview', ProductionYear: 'ProductionYear', PremiereDate: 'PremiereDate', Genres: 'Genres', Studios: 'Studios', People: 'People', Tags: 'TagItems', CommunityRating: 'CommunityRating', OfficialRating: 'OfficialRating', CustomRating: 'CustomRating', SortName: 'SortName', ForcedSortName: 'ForcedSortName', ExternalIds: 'ProviderIds' }
  const current = beforeItem[embyField[field]]
  const currentText = Array.isArray(current) ? current.map((item) => typeof item === 'object' && item ? String((item as { Name?: string }).Name ?? '') : String(item)).filter(Boolean).join('、') : typeof current === 'object' && current ? JSON.stringify(current, null, 2) : current === undefined || current === null ? '' : String(current)
  const multiline = field === 'Name' || field === 'OriginalTitle' || field === 'Taglines' || field === 'Overview'
  const gridClass = hideCheckbox ? 'grid-cols-[76px_minmax(0,1fr)_minmax(0,1fr)]' : 'grid-cols-[28px_76px_minmax(0,1fr)_minmax(0,1fr)]'
  const cellClass = multiline ? 'h-20 max-h-20' : 'min-h-9'
  const row = <div className={`grid ${gridClass} items-center gap-2 py-2`}>{!hideCheckbox && <Checkbox checked={checked} onCheckedChange={onCheck} />}<label className='text-sm'>{label}</label><div className={`${cellClass} overflow-hidden break-words whitespace-pre-wrap text-sm text-slate-500`}>{field === 'ExternalIds' ? <ExternalIdsView value={current} /> : collectionFields.has(field) ? <ValueChips value={currentText} /> : currentText || '—'}</div><div className={`${cellClass} min-w-0 overflow-hidden`}>{collectionFields.has(field) ? <TagEditor value={value} onChange={onChange} /> : multiline ? <textarea className='h-full max-h-20 w-full resize-none overflow-y-auto rounded border px-2 py-1 text-sm' value={value} onChange={(event) => onChange(event.target.value)} /> : field === 'ExternalIds' ? <ExternalIdsEditor value={value} onChange={onChange} /> : field === 'OfficialRating' || field === 'CustomRating' ? <Select value={value || '__empty__'} onValueChange={(next) => onChange(next === '__empty__' ? '' : next)}><SelectTrigger className='h-9'><SelectValue placeholder='选择评分' /></SelectTrigger><SelectContent>{ratingOptions.map((option) => <SelectItem key={option || '__empty__'} value={option || '__empty__'}>{option || '未设置'}</SelectItem>)}</SelectContent></Select> : <Input className='h-9' type={field === 'CommunityRating' ? 'number' : 'text'} min={field === 'CommunityRating' ? 0 : undefined} max={field === 'CommunityRating' ? 10 : undefined} step={field === 'CommunityRating' ? '.1' : undefined} value={value} onChange={(event) => onChange(event.target.value)} />}</div></div>
  return field === 'SortName' || field === 'ForcedSortName' || field === 'ExternalIds' ? <details className='rounded border-b px-2'><summary className='cursor-pointer py-2 text-sm font-medium text-slate-600'>{label}</summary>{row}</details> : row
}

function MetadataEditorPanelNoTabs({ candidate, beforeItem, autoTranslate, setAutoTranslate, setCandidate, writeback, batchWriteback, batchCount }: { candidate: MetadataCandidate | null; beforeItem: Record<string, unknown>; autoTranslate: boolean; setAutoTranslate: (value: boolean) => void; setCandidate: (value: (current: MetadataCandidate | null) => MetadataCandidate | null) => void; writeback: () => void; batchWriteback: () => void; batchCount: number }) {
  return <div className='flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-white'><div className='border-b px-4 py-3'><b>编辑元数据</b></div><div className='min-h-0 flex-1 overflow-y-auto p-4'>{candidate ? <><CoverPreview candidate={candidate} /><div className='mb-3 flex justify-between rounded border bg-slate-50 p-2 text-sm'><span>覆盖模式</span><button onClick={() => setAutoTranslate(!autoTranslate)}>{autoTranslate ? '自动翻译已开启' : '自动翻译已关闭'}</button></div><div className='grid grid-cols-[76px_minmax(0,1fr)_minmax(0,1fr)] gap-2 border-b pb-2 text-xs text-slate-500'><span>字段</span><span>当前 Emby 值</span><span>候选值</span></div><div className='divide-y'>{fields.map(([key, label]) => <FieldRow key={key} field={key} label={label} candidate={candidate} beforeItem={beforeItem} hideCheckbox onChange={(value) => setCandidate((current) => current ? updateCandidate(current, key, value) : current)} />)}</div><div className='mt-4 rounded border bg-slate-50 p-3 text-xs'>数据源：{candidate.source}　编号：{candidate.source_id}<br />产品番号：{candidate.product_number ?? '—'}<br /><a href={candidate.raw_url} target='_blank' rel='noreferrer' className='text-blue-600'>打开来源页</a></div></> : <Empty title='等待候选详情' text='从中栏选择一条搜索结果。' />}</div><div className='flex items-center justify-end gap-2 border-t p-3'><Button variant='outline' disabled={!candidate}>保存为草稿</Button><Button variant='outline' disabled={batchCount < 2} onClick={batchWriteback}>批量写入 Emby</Button><Button onClick={writeback} disabled={!candidate}><Upload className='size-4' />确认写入 Emby</Button></div></div>
}

function Status({ value }: { value: string }) {
  const labels: Record<string, string> = { pending: '待搜索', searched: '已搜索', fetched: '已抓取', written: '已写入', failed: '失败' }
  return <span className={`queue-status queue-status-${value}`}>{labels[value] ?? value}</span>
}
function Empty({ title, text }: { title: string; text: string }) { return <div className='flex h-full min-h-48 flex-col items-center justify-center text-center'><CircleHelp className='mb-3 size-8 text-slate-300' /><b className='text-sm'>{title}</b><p className='mt-1 text-sm text-slate-500'>{text}</p></div> }

export { EditorPanel, QueuePanel, ResultPanel }
