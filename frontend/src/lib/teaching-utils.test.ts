import { describe, expect, it } from 'vitest'

import {
  buildCategoryFilters,
  computeResumeSeek,
  displayTitle,
  filterByCategory,
  filterPlayableTeachings,
  getMediaStatus,
} from '#/lib/teaching-utils'
import type { Category, Teaching } from '#/lib/types'

function makeTeaching(overrides: Partial<Teaching> = {}): Teaching {
  return {
    id: 1,
    telegram_message_id: 100,
    title_ar: '',
    title_fr: 'Titre français',
    media_type: 'audio',
    file_name: 'test.mp3',
    file_size: 1024,
    published_at: '2026-01-15T10:00:00Z',
    telegram_message_url: '',
    download_status: 'ready',
    category: null,
    ...overrides,
  }
}

describe('displayTitle', () => {
  it('prefers title_fr over title_ar', () => {
    expect(
      displayTitle(makeTeaching({ title_fr: 'FR', title_ar: 'AR' })),
    ).toBe('FR')
  })

  it('falls back to title_ar then id', () => {
    expect(displayTitle(makeTeaching({ title_fr: '', title_ar: 'عنوان' }))).toBe(
      'عنوان',
    )
    expect(displayTitle(makeTeaching({ title_fr: '', title_ar: '' }))).toBe(
      'Enseignement #1',
    )
  })
})

describe('filterPlayableTeachings', () => {
  it('keeps audio and voice only', () => {
    const items = [
      makeTeaching({ id: 1, media_type: 'audio' }),
      makeTeaching({ id: 2, media_type: 'voice' }),
      makeTeaching({ id: 3, media_type: 'document' }),
    ]
    expect(filterPlayableTeachings(items).map((t) => t.id)).toEqual([1, 2])
  })
})

describe('getMediaStatus', () => {
  it('maps download statuses to labels', () => {
    expect(getMediaStatus('ready').canPlay).toBe(true)
    expect(getMediaStatus('pending').label).toBe('Audio en préparation')
    expect(getMediaStatus('failed').label).toBe(
      'Audio indisponible pour le moment',
    )
  })
})

describe('buildCategoryFilters', () => {
  const categories: Category[] = [
    { id: 1, name: 'Fiqh', slug: 'fiqh', description: '', sort_order: 1 },
    { id: 2, name: 'Vide', slug: 'empty', description: '', sort_order: 2 },
  ]

  it('returns empty when only one implicit option', () => {
    expect(
      buildCategoryFilters(
        [makeTeaching({ category: null })],
        categories,
      ),
    ).toEqual([])
  })

  it('includes sans categorie when needed', () => {
    const filters = buildCategoryFilters(
      [
        makeTeaching({ category: categories[0] }),
        makeTeaching({ id: 2, category: null }),
      ],
      categories,
    )
    expect(filters.map((f) => f.value)).toEqual(['all', 'fiqh', 'none'])
  })
})

describe('filterByCategory', () => {
  const cat: Category = {
    id: 1,
    name: 'Fiqh',
    slug: 'fiqh',
    description: '',
    sort_order: 0,
  }
  const items = [
    makeTeaching({ id: 1, category: cat }),
    makeTeaching({ id: 2, category: null }),
  ]

  it('filters by slug and none', () => {
    expect(filterByCategory(items, 'fiqh').map((t) => t.id)).toEqual([1])
    expect(filterByCategory(items, 'none').map((t) => t.id)).toEqual([2])
  })
})

describe('computeResumeSeek', () => {
  it('seeks only in the valid window', () => {
    expect(computeResumeSeek(5, 600)).toBeNull()
    expect(computeResumeSeek(842, 900)).toBe(842)
    expect(computeResumeSeek(890, 900)).toBeNull()
  })
})
