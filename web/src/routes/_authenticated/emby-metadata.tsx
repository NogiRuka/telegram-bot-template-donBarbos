import { createFileRoute } from '@tanstack/react-router'
import { EmbyMetadataWorkspace } from '@/features/emby-metadata'

export const Route = createFileRoute('/_authenticated/emby-metadata')({ component: EmbyMetadataWorkspace })
