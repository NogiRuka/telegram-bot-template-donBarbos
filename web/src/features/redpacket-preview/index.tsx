import { useMemo, useState } from 'react'
import { Slider } from '@/components/ui/slider'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { ConfigDrawer } from '@/components/config-drawer'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'

type AlignValue = 'left' | 'center' | 'right'

type LayoutState = {
  titleFontSize: number
  messageFontSize: number
  amountFontSize: number
  watermarkFontSize: number
  avatarSize: number
  amountFromBottom: number
  titleAlign: AlignValue
  messageAlign: AlignValue
  amountAlign: AlignValue
  titleDx: number
  titleDy: number
  messageDx: number
  messageDy: number
  amountDx: number
  amountDy: number
  watermarkDx: number
  watermarkDy: number
  titleColor: string
  messageColor: string
  amountColor: string
  watermarkColor: string
  shadowEnabled: boolean
  shadowOffsetX: number
  shadowOffsetY: number
  shadowColor: string
  fontName: string
}

export function RedpacketPreview() {
  const [senderName, setSenderName] = useState('小桜')
  const [message, setMessage] = useState('恭喜发财，大吉大利')
  const [amount, setAmount] = useState<number>(100)
  const [count, setCount] = useState<number>(5)
  const [watermarkText, setWatermarkText] = useState('WeChat Team')

  const [layout, setLayout] = useState<LayoutState>({
    titleFontSize: 88,
    messageFontSize: 96,
    amountFontSize: 110,
    watermarkFontSize: 52,
    avatarSize: 200,
    amountFromBottom: 260,
    titleAlign: 'left',
    messageAlign: 'center',
    amountAlign: 'center',
    titleDx: 0,
    titleDy: 0,
    messageDx: 0,
    messageDy: 0,
    amountDx: 0,
    amountDy: 0,
    watermarkDx: 0,
    watermarkDy: 0,
    titleColor: '#ffffff',
    messageColor: '#ffffff',
    amountColor: '#ffffff',
    watermarkColor: '#ffffff',
    shadowEnabled: true,
    shadowOffsetX: 2,
    shadowOffsetY: 2,
    shadowColor: '#000000',
    fontName: '',
  })

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
    params.set('watermark_text', watermarkText)
    params.set('title_align', layout.titleAlign)
    params.set('message_align', layout.messageAlign)
    params.set('amount_align', layout.amountAlign)
    params.set('title_dx', String(layout.titleDx))
    params.set('title_dy', String(layout.titleDy))
    params.set('message_dx', String(layout.messageDx))
    params.set('message_dy', String(layout.messageDy))
    params.set('amount_dx', String(layout.amountDx))
    params.set('amount_dy', String(layout.amountDy))
    params.set('watermark_dx', String(layout.watermarkDx))
    params.set('watermark_dy', String(layout.watermarkDy))
    params.set('title_color', layout.titleColor)
    params.set('message_color', layout.messageColor)
    params.set('amount_color', layout.amountColor)
    params.set('watermark_color', layout.watermarkColor)
    params.set('shadow_enabled', String(layout.shadowEnabled))
    params.set('shadow_offset_x', String(layout.shadowOffsetX))
    params.set('shadow_offset_y', String(layout.shadowOffsetY))
    params.set('shadow_color', layout.shadowColor)
    if (layout.fontName) {
      params.set('font_name', layout.fontName)
    }
    const base = import.meta.env.VITE_API_URL || '/api'
    return `${base}/redpacket/preview?${params.toString()}`
  }, [senderName, message, amount, count, watermarkText, layout])

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

        <div className='flex-1 space-y-4'>
          <div>
            <h1 className='text-2xl font-bold tracking-tight'>红包样式调参</h1>
            <p className='text-muted-foreground'>
              调整红包上的所有文字、位置、颜色和阴影效果。
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
            <div className='space-y-2'>
              <Label htmlFor='watermarkText'>左上角水印</Label>
              <Input
                id='watermarkText'
                value={watermarkText}
                onChange={(e) => setWatermarkText(e.target.value)}
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

          <div className='grid gap-4 rounded-lg border p-4 md:grid-cols-2'>
            <AlignControl
              label='标题对齐'
              value={layout.titleAlign}
              onChange={(value) =>
                setLayout((prev) => ({
                  ...prev,
                  titleAlign: value,
                }))
              }
            />
            <AlignControl
              label='留言对齐'
              value={layout.messageAlign}
              onChange={(value) =>
                setLayout((prev) => ({
                  ...prev,
                  messageAlign: value,
                }))
              }
            />
            <AlignControl
              label='金额对齐'
              value={layout.amountAlign}
              onChange={(value) =>
                setLayout((prev) => ({
                  ...prev,
                  amountAlign: value,
                }))
              }
            />
            <SliderControl
              label='标题水平偏移'
              value={layout.titleDx}
              min={-200}
              max={200}
              onChange={handleSliderChange('titleDx')}
            />
            <SliderControl
              label='标题垂直偏移'
              value={layout.titleDy}
              min={-200}
              max={200}
              onChange={handleSliderChange('titleDy')}
            />
            <SliderControl
              label='留言水平偏移'
              value={layout.messageDx}
              min={-200}
              max={200}
              onChange={handleSliderChange('messageDx')}
            />
            <SliderControl
              label='留言垂直偏移'
              value={layout.messageDy}
              min={-200}
              max={200}
              onChange={handleSliderChange('messageDy')}
            />
            <SliderControl
              label='金额水平偏移'
              value={layout.amountDx}
              min={-200}
              max={200}
              onChange={handleSliderChange('amountDx')}
            />
            <SliderControl
              label='金额垂直偏移'
              value={layout.amountDy}
              min={-200}
              max={200}
              onChange={handleSliderChange('amountDy')}
            />
            <SliderControl
              label='水印水平偏移'
              value={layout.watermarkDx}
              min={-200}
              max={200}
              onChange={handleSliderChange('watermarkDx')}
            />
            <SliderControl
              label='水印垂直偏移'
              value={layout.watermarkDy}
              min={-200}
              max={200}
              onChange={handleSliderChange('watermarkDy')}
            />
          </div>

          <div className='grid gap-4 rounded-lg border p-4 md:grid-cols-2'>
            <ColorControl
              label='标题颜色'
              value={layout.titleColor}
              onChange={(value) =>
                setLayout((prev) => ({
                  ...prev,
                  titleColor: value,
                }))
              }
            />
            <ColorControl
              label='留言颜色'
              value={layout.messageColor}
              onChange={(value) =>
                setLayout((prev) => ({
                  ...prev,
                  messageColor: value,
                }))
              }
            />
            <ColorControl
              label='金额颜色'
              value={layout.amountColor}
              onChange={(value) =>
                setLayout((prev) => ({
                  ...prev,
                  amountColor: value,
                }))
              }
            />
            <ColorControl
              label='水印颜色'
              value={layout.watermarkColor}
              onChange={(value) =>
                setLayout((prev) => ({
                  ...prev,
                  watermarkColor: value,
                }))
              }
            />
            <div className='space-y-2'>
              <div className='flex items-center justify-between text-xs'>
                <span className='font-medium'>文字阴影</span>
                <span className='text-muted-foreground'>
                  {layout.shadowEnabled ? '已启用' : '已关闭'}
                </span>
              </div>
              <div className='flex items-center justify-between'>
                <span className='text-xs text-muted-foreground'>开关</span>
                <Switch
                  checked={layout.shadowEnabled}
                  onCheckedChange={(checked) =>
                    setLayout((prev) => ({
                      ...prev,
                      shadowEnabled: checked,
                    }))
                  }
                />
              </div>
              <div className='grid gap-2 md:grid-cols-2'>
                <SliderControl
                  label='阴影水平偏移'
                  value={layout.shadowOffsetX}
                  min={-20}
                  max={20}
                  onChange={handleSliderChange('shadowOffsetX')}
                />
                <SliderControl
                  label='阴影垂直偏移'
                  value={layout.shadowOffsetY}
                  min={-20}
                  max={20}
                  onChange={handleSliderChange('shadowOffsetY')}
                />
              </div>
            </div>
            <div className='space-y-2'>
              <div className='flex items-center justify-between text-xs'>
                <span className='font-medium'>阴影颜色</span>
                <span className='text-muted-foreground'>{layout.shadowColor}</span>
              </div>
              <Input
                type='color'
                value={layout.shadowColor}
                onChange={(e) =>
                  setLayout((prev) => ({
                    ...prev,
                    shadowColor: e.target.value,
                  }))
                }
                className='h-8 w-full p-1'
              />
            </div>
            <div className='space-y-2'>
              <Label>字体</Label>
              <Select
                value={layout.fontName || undefined}
                onValueChange={(value) =>
                  setLayout((prev) => ({
                    ...prev,
                    fontName: value,
                  }))
                }
              >
                <SelectTrigger className='w-full'>
                  <SelectValue placeholder='自动选择字体' />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value='msyh.ttc'>微软雅黑 (msyh.ttc)</SelectItem>
                  <SelectItem value='simhei.ttf'>黑体 (simhei.ttf)</SelectItem>
                  <SelectItem value='simsun.ttc'>宋体 (simsun.ttc)</SelectItem>
                </SelectContent>
              </Select>
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

type AlignControlProps = {
  label: string
  value: AlignValue
  onChange: (value: AlignValue) => void
}

function AlignControl({ label, value, onChange }: AlignControlProps) {
  return (
    <div className='space-y-2'>
      <div className='flex items-center justify-between text-xs'>
        <span className='font-medium'>{label}</span>
      </div>
      <RadioGroup
        value={value}
        onValueChange={(val) => onChange(val as AlignValue)}
        className='flex flex-row gap-4'
      >
        <div className='flex items-center gap-2'>
          <RadioGroupItem value='left' />
          <span className='text-xs text-muted-foreground'>左对齐</span>
        </div>
        <div className='flex items-center gap-2'>
          <RadioGroupItem value='center' />
          <span className='text-xs text-muted-foreground'>居中</span>
        </div>
        <div className='flex items-center gap-2'>
          <RadioGroupItem value='right' />
          <span className='text-xs text-muted-foreground'>右对齐</span>
        </div>
      </RadioGroup>
    </div>
  )
}

type ColorControlProps = {
  label: string
  value: string
  onChange: (value: string) => void
}

function ColorControl({ label, value, onChange }: ColorControlProps) {
  return (
    <div className='space-y-2'>
      <div className='flex items-center justify-between text-xs'>
        <span className='font-medium'>{label}</span>
        <span className='text-muted-foreground'>{value}</span>
      </div>
      <Input
        type='color'
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className='h-8 w-full p-1'
      />
    </div>
  )
}
