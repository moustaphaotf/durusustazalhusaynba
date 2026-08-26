import { apiUrl } from '#/lib/config'

const REPORT_PATH = '/api/client-errors/'

type ErrorReport = {
  message: string
  stack?: string
  url?: string
  userAgent?: string
  component?: string
  statusCode?: number
}

let handlersInstalled = false
const recentKeys = new Map<string, number>()
const DEDUP_MS = 60_000

function dedupeKey(report: ErrorReport): string {
  return `${report.component ?? ''}|${report.message}|${report.stack?.slice(0, 200) ?? ''}`
}

function shouldSkip(key: string): boolean {
  const now = Date.now()
  for (const [k, ts] of recentKeys) {
    if (now - ts > DEDUP_MS) recentKeys.delete(k)
  }
  if (recentKeys.has(key)) return true
  recentKeys.set(key, now)
  return false
}

export async function reportClientError(
  report: ErrorReport,
): Promise<void> {
  const key = dedupeKey(report)
  if (shouldSkip(key)) return

  const payload = {
    message: report.message.slice(0, 2000),
    stack: report.stack?.slice(0, 4000),
    url: report.url?.slice(0, 500),
    userAgent: report.userAgent?.slice(0, 300),
    component: report.component?.slice(0, 100),
    statusCode: report.statusCode,
  }

  try {
    await fetch(apiUrl(REPORT_PATH), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true,
    })
  } catch {
    // Never break the app if reporting fails.
  }
}

function normalizeError(error: unknown): { message: string; stack?: string } {
  if (error instanceof Error) {
    return { message: error.message || error.name, stack: error.stack }
  }
  if (typeof error === 'string') {
    return { message: error }
  }
  try {
    return { message: JSON.stringify(error) }
  } catch {
    return { message: 'Unknown error' }
  }
}

export function reportCaughtError(
  error: unknown,
  component = 'frontend',
  statusCode?: number,
): void {
  const { message, stack } = normalizeError(error)
  void reportClientError({
    message,
    stack,
    url: typeof window !== 'undefined' ? window.location.href : undefined,
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
    component,
    statusCode,
  })
}

export function installGlobalErrorHandlers(): void {
  if (typeof window === 'undefined' || handlersInstalled) return
  handlersInstalled = true

  window.addEventListener('error', (event) => {
    reportCaughtError(
      event.error ?? event.message,
      'window.onerror',
    )
  })

  window.addEventListener('unhandledrejection', (event) => {
    reportCaughtError(event.reason, 'unhandledrejection')
  })
}
