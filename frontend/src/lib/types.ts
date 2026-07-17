export type MediaType = 'audio' | 'voice' | 'document' | ''

export type DownloadStatus =
  | 'pending'
  | 'processing'
  | 'ready'
  | 'failed'
  | 'skipped'
  | string

export interface Category {
  id: number
  name: string
  slug: string
  description: string
  sort_order: number
}

export interface Teaching {
  id: number
  telegram_message_id: number
  title_ar: string
  title_fr: string
  media_type: MediaType
  file_name: string
  file_size: number | null
  published_at: string | null
  telegram_message_url: string
  download_status: DownloadStatus
  category: Category | null
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface SignedMediaResponse {
  url: string
  expires_in: number
}

export interface MediaConflictResponse {
  detail: string
  download_status: DownloadStatus
}

export interface ResumePosition {
  time: number
  updatedAt: string
}

export interface ResumeStorage {
  version: 1
  lastTeachingId: number | null
  positions: Record<string, ResumePosition>
}
