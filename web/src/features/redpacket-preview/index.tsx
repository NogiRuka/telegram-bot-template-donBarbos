import { useEffect, useMemo, useState } from 'react'
import { getRouteApi } from '@tanstack/react-router'
import { Slider } from '@/components/ui/slider'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { ConfigDrawer } from '@/components/config-drawer'
import { ProfileDropdown } from '@/components/profile-dropdown'

const route = getRouteApi('/_authenticated/redpacket-preview/')

type LayoutState = {
  titleFontSize: number
  messageFontSize: number
  amountFontSize: number
  watermarkFontSize: number
  avatarSize: number
  amountFromBottom: number
}

export function RedpacketPreview() {
  const search = route.useSearch()
  const navigate = route.useNavigate()

  const [senderName, setSenderName] = useState(search.senderName ?? '小桜')
  const [message, setMessage] = useState(search.message ?? '恭喜发财，大吉大利')
  const [amount, setAmount] = useState<number>(search.amount ?? 100)
  const [count, setCount] = useState<number>(search.count ?? 5)

  const [layout, setLayout] = useState<LayoutState>({
    titleFontSize: search.titleFontSize ?? 88,
    messageFontSize: search.messageFontSize ?? 96,
    amountFontSize: search.amountFontSize ?? 110,
    watermarkFontSize: search.watermarkFontSize ?? 52,
    avatarSize: search.avatarSize ?? 200,
    amountFromBottom: search.amountFromBottom ?? 260,
  })

  useEffect(() => {
    navigate({
      search: {
        senderName,
        message,
        amount,
        count,
        ...layout,
      },
      replace: true,
    })
  }, [senderName, message, amount, count, layout, navigate])

  const previewUrl = useMemo(() => {
    const params = new URLSearchParams()
    params.set('sender_name', senderName)
    params.set('message', message)
    params.set('amount', String(amount))
    params.set('count', String(count))
    params.set('title_font_size', String(layout.titleFontSize))
    params.set('message_font_size', String(layout.messageFontSize))
    params.set('amount_font_size', String(layout.amountFontSize))
    params.set('watermark_font_size', String(layout.watermarkFontSize))
    params.set('avatar_size', String(layout.avatarSize))
    params.set('amount_from_bottom', String(layout.amountFromBottom))
    params.set('avatar_image_name', 'sakura.png')
    params.set('watermark_text', 'WeChat Team')
    // 加上时间戳避免缓存
    params.set('_t', String(Date.now()))
    const base = import.meta.env.VITE_API_URL || '/api'
    return `${base}/redpacket/preview?${params.toString()}`
  }, [senderName, message, amount, count, layout])

  const handleSliderChange =
    (key: keyof LayoutState) =>
    (value: number[]) => {
      const v = value[0]
      setLayout((prev) => ({ ...prev, [key]: v }))
    }

  return (
    <>
      <Header>
        <Search />
        <div className='ms-auto flex items-center gap-4'>
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      <Main fixed className='flex flex-col gap-4 lg:flex-row'>
        <div className='flex-1 space-y-4'>
          <div>
            <h1 className='text-2xl font-bold tracking-tight'>红包样式调参</h1>
            <p className='text-muted-foreground'>
              调整文字和头像大小，实时预览红包封面效果。
            </p>
          </div>

          <div className='grid gap-4 rounded-lg border p-4 md:grid-cols-2'>
            <div className='space-y-2'>
              <Label htmlFor='senderName'>谁的红包</Label>
              <Input
                id='senderName'
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
              />
            </div>
            <div className='space-y-2'>
              <Label htmlFor='message'>留言</Label>
              <Input
                id='message'
                value={message}
                onChange={(e) => setMessage(e.target.value)}
              />
            </div>
            <div className='space-y-2'>
              <Label htmlFor='amount'>金额</Label>
              <Input
                id='amount'
                type='number'
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value || 0))}
              />
            </div>
            <div className='space-y-2'>
              <Label htmlFor='count'>份数</Label>
              <Input
                id='count'
                type='number'
                value={count}
                onChange={(e) => setCount(Number(e.target.value || 1))}
              />
            </div>
          </div>

          <div className='grid gap-4 rounded-lg border p-4 md:grid-cols-2'>
            <SliderControl
              label='标题字体大小（谁的红包）'
              value={layout.titleFontSize}
              min={40}
              max={200}
              onChange={handleSliderChange('titleFontSize')}
            />
            <SliderControl
              label='留言字体大小'
              value={layout.messageFontSize}
              min={40}
              max={220}
              onChange={handleSliderChange('messageFontSize')}
            />
            <SliderControl
              label='金额字体大小'
              value={layout.amountFontSize}
              min={40}
              max={240}
              onChange={handleSliderChange('amountFontSize')}
            />
            <SliderControl
              label='水印字体大小'
              value={layout.watermarkFontSize}
              min={20}
              max={160}
              onChange={handleSliderChange('watermarkFontSize')}
            />
            <SliderControl
              label='头像尺寸'
              value={layout.avatarSize}
              min={80}
              max={360}
              onChange={handleSliderChange('avatarSize')}
            />
            <SliderControl
              label='金额距底部像素'
              value={layout.amountFromBottom}
              min={80}
              max={400}
              onChange={handleSliderChange('amountFromBottom')}
            />
          </div>
        </div>

        <div className='flex-1 rounded-lg border p-4'>
          <div className='mb-2 flex items-center justify-between'>
            <span className='text-sm font-medium text-muted-foreground'>
              实时预览
            </span>
            <span className='text-xs text-muted-foreground'>
              957 × 1584 像素（等比例缩放展示）
            </span>
          </div>
          <div className='flex h-full items-center justify-center'>
            <div className='max-h-[80vh] max-w-full overflow-auto rounded-lg bg-muted p-2'>
              <img
                src={previewUrl}
                alt='红包预览'
                className='h-[792px] w-[478px] object-contain'
              />
            </div>
          </div>
        </div>
      </Main>
    </>
  )
}

type SliderControlProps = {
  label: string
  value: number
  min: number
  max: number
  onChange: (value: number[]) => void
}

function SliderControl({ label, value, min, max, onChange }: SliderControlProps) {
  return (
    <div className='space-y-2'>
      <div className='flex items-center justify-between text-xs'>
        <span className='font-medium'>{label}</span>
        <span className='text-muted-foreground'>{value}</span>
      </div>
      <Slider
        value={[value]}
        min={min}
        max={max}
        step={2}
        onValueChange={onChange}
      />
    </div>
  )
}

