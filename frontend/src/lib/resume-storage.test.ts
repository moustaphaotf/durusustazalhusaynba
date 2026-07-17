import { beforeEach, describe, expect, it } from 'vitest'

import {
  getSavedPosition,
  loadResumeStorage,
  updatePosition,
} from '#/lib/resume-storage'

describe('resume-storage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('starts empty', () => {
    expect(loadResumeStorage()).toEqual({
      version: 1,
      lastTeachingId: null,
      positions: {},
    })
  })

  it('persists positions', () => {
    updatePosition(42, 120.5)
    expect(getSavedPosition(42)).toBe(120.5)
    expect(loadResumeStorage().lastTeachingId).toBe(42)
  })
})
