import type { ResumeStorage } from '#/lib/types'

const STORAGE_KEY = 'durus-resume-v1'

const EMPTY: ResumeStorage = {
  version: 1,
  lastTeachingId: null,
  positions: {},
}

export function loadResumeStorage(): ResumeStorage {
  if (typeof window === 'undefined') return { ...EMPTY }
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...EMPTY }
    const parsed = JSON.parse(raw) as ResumeStorage
    if (parsed.version !== 1) return { ...EMPTY }
    return {
      version: 1,
      lastTeachingId: parsed.lastTeachingId ?? null,
      positions: parsed.positions ?? {},
    }
  } catch {
    return { ...EMPTY }
  }
}

export function saveResumeStorage(data: ResumeStorage): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
}

export function getSavedPosition(
  teachingId: number,
  storage = loadResumeStorage(),
): number | null {
  const entry = storage.positions[String(teachingId)]
  return entry?.time ?? null
}

export function updatePosition(
  teachingId: number,
  time: number,
  storage = loadResumeStorage(),
): ResumeStorage {
  const next: ResumeStorage = {
    version: 1,
    lastTeachingId: teachingId,
    positions: {
      ...storage.positions,
      [String(teachingId)]: {
        time,
        updatedAt: new Date().toISOString(),
      },
    },
  }
  saveResumeStorage(next)
  return next
}
