import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { reportClientError } from '#/lib/error-reporting'

describe('reportClientError', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts sanitized payload to the client-errors API', async () => {
    await reportClientError({
      message: 'Test failure',
      stack: 'Error: Test failure\n    at Home',
      component: 'test',
      url: 'http://localhost:3000/',
    })

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/client-errors/'),
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('Test failure'),
      }),
    )
  })

  it('deduplicates identical reports within 60s', async () => {
    await reportClientError({ message: 'dup', component: 'test' })
    await reportClientError({ message: 'dup', component: 'test' })

    expect(fetch).toHaveBeenCalledTimes(1)
  })
})
