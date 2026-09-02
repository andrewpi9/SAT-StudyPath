import { api, ApiError, authHeaders } from './client'
import type { AttemptResult, Difficulty } from './types'

export interface LogAttemptPayload {
  topic_id: number
  correct: boolean
  time_taken_seconds: number
  difficulty: Difficulty
}

export function logAttempt(payload: LogAttemptPayload): Promise<AttemptResult> {
  return api.post<AttemptResult>('/attempts', payload)
}

export interface BulkImportResult {
  imported: number
  failed: number
  errors: { row: number; message: string }[]
}

export const CSV_TEMPLATE_URL = '/api/attempts/template.csv'

export async function bulkImportAttempts(file: File): Promise<BulkImportResult> {
  const form = new FormData()
  form.append('file', file)
  // Not api.post: FormData needs the browser to set its own multipart boundary.
  const res = await fetch('/api/attempts/bulk', {
    method: 'POST',
    body: form,
    headers: authHeaders(),
  })
  if (!res.ok) {
    throw new ApiError(res.status, (await res.text().catch(() => '')) || res.statusText)
  }
  return res.json() as Promise<BulkImportResult>
}
