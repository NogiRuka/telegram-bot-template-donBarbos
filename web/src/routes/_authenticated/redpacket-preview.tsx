import { createFileRoute } from '@tanstack/react-router'
import { RedpacketPreview } from '@/features/redpacket-preview'

export const Route = createFileRoute('/_authenticated/redpacket-preview/')({
  component: RedpacketPreview,
})

