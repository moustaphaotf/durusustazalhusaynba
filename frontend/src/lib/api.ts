import { apiUrl } from '#/lib/config'
import type {
  Category,
  MediaConflictResponse,
  PaginatedResponse,
  SignedMediaResponse,
  Teaching,
} from '#/lib/types'

class ApiError extends Error {
  status: number
  body: unknown

  constructor(message: string, status: number, body: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

async function parseJson<T>(response: Response): Promise<T> {
  const text = await response.text()
  if (!text) return {} as T
  return JSON.parse(text) as T
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {
      Accept: 'application/json',
      ...init?.headers,
    },
  })

  if (!response.ok) {
    const body = await parseJson<unknown>(response)
    throw new ApiError(
      `API ${response.status}: ${response.statusText}`,
      response.status,
      body,
    )
  }

  return parseJson<T>(response)
}

export async function fetchTeachingsPage(
  pageUrl?: string | null,
): Promise<PaginatedResponse<Teaching>> {
  const path = pageUrl ?? '/api/teachings/?ordering=-published_at'
  if (pageUrl?.startsWith('http')) {
    const response = await fetch(pageUrl)
    if (!response.ok) {
      throw new ApiError(
        `API ${response.status}`,
        response.status,
        await parseJson(response),
      )
    }
    return parseJson<PaginatedResponse<Teaching>>(response)
  }
  return request<PaginatedResponse<Teaching>>(path)
}

export async function fetchCategories(): Promise<Category[]> {
  const data = await request<PaginatedResponse<Category> | Category[]>(
    '/api/categories/',
  )
  return Array.isArray(data) ? data : data.results
}

export async function fetchTeachingMedia(
  teachingId: number,
): Promise<SignedMediaResponse> {
  return request<SignedMediaResponse>(`/api/teachings/${teachingId}/media/`)
}

export function isMediaConflict(error: unknown): error is ApiError {
  return error instanceof ApiError && error.status === 409
}

export function getConflictStatus(error: ApiError): DownloadStatus | null {
  const body = error.body as MediaConflictResponse | undefined
  return body?.download_status ?? null
}

export { ApiError }
