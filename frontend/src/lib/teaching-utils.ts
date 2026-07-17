import type { Category, DownloadStatus, Teaching } from '#/lib/types'

const PLAYABLE_MEDIA = new Set(['audio', 'voice'])

export function isPlayableMedia(teaching: Teaching): boolean {
  return PLAYABLE_MEDIA.has(teaching.media_type)
}

export function filterPlayableTeachings(teachings: Teaching[]): Teaching[] {
  return teachings.filter(isPlayableMedia)
}

export function displayTitle(teaching: Teaching): string {
  const fr = teaching.title_fr?.trim()
  const ar = teaching.title_ar?.trim()
  if (fr) return fr
  if (ar) return ar
  return `Enseignement #${teaching.id}`
}

export function hasArabicTitle(teaching: Teaching): boolean {
  return Boolean(teaching.title_ar?.trim()) && !teaching.title_fr?.trim()
}

export interface MediaStatusInfo {
  label: string
  tone: 'ready' | 'pending' | 'muted' | 'unknown'
  canPlay: boolean
}

export function getMediaStatus(status: DownloadStatus): MediaStatusInfo {
  switch (status) {
    case 'ready':
      return { label: 'Prêt', tone: 'ready', canPlay: true }
    case 'pending':
    case 'processing':
      return {
        label: 'Audio en préparation',
        tone: 'pending',
        canPlay: false,
      }
    case 'failed':
      return {
        label: 'Audio indisponible pour le moment',
        tone: 'muted',
        canPlay: false,
      }
    case 'skipped':
      return {
        label: 'Audio non disponible',
        tone: 'muted',
        canPlay: false,
      }
    default:
      return {
        label: 'État audio inconnu',
        tone: 'unknown',
        canPlay: false,
      }
  }
}

export function formatPublishedDate(iso: string | null): string | null {
  if (!iso) return null
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    }).format(new Date(iso))
  } catch {
    return null
  }
}

export function formatFileSize(bytes: number | null): string | null {
  if (bytes == null || bytes <= 0) return null
  const units = ['o', 'Ko', 'Mo', 'Go']
  let size = bytes
  let unit = 0
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024
    unit += 1
  }
  return `${size < 10 && unit > 0 ? size.toFixed(1) : Math.round(size)} ${units[unit]}`
}

export type CategoryFilterValue = 'all' | 'none' | string

export interface CategoryFilterOption {
  value: CategoryFilterValue
  label: string
}

export function buildCategoryFilters(
  teachings: Teaching[],
  categories: Category[],
): CategoryFilterOption[] {
  const slugCounts = new Map<string, number>()
  let uncategorized = 0

  for (const teaching of teachings) {
    if (teaching.category?.slug) {
      slugCounts.set(
        teaching.category.slug,
        (slugCounts.get(teaching.category.slug) ?? 0) + 1,
      )
    } else {
      uncategorized += 1
    }
  }

  const options: CategoryFilterOption[] = [{ value: 'all', label: 'Tous' }]

  const sorted = [...categories].sort(
    (a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name, 'fr'),
  )

  let hasNamedCategory = false
  for (const category of sorted) {
    if ((slugCounts.get(category.slug) ?? 0) > 0) {
      hasNamedCategory = true
      options.push({ value: category.slug, label: category.name })
    }
  }

  if (!hasNamedCategory) {
    return []
  }

  if (uncategorized > 0) {
    options.push({ value: 'none', label: 'Sans catégorie' })
  }

  return options.length > 1 ? options : []
}

export function filterByCategory(
  teachings: Teaching[],
  filter: CategoryFilterValue,
): Teaching[] {
  if (filter === 'all') return teachings
  if (filter === 'none') {
    return teachings.filter((t) => !t.category)
  }
  return teachings.filter((t) => t.category?.slug === filter)
}

export function computeResumeSeek(
  savedTime: number,
  duration: number,
): number | null {
  if (!Number.isFinite(savedTime) || !Number.isFinite(duration) || duration <= 0) {
    return null
  }
  if (savedTime <= 10) return null
  if (savedTime >= duration - 15) return null
  return savedTime
}
