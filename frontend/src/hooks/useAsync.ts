import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '../api/client'

export interface AsyncState<T> {
  data: T | null
  error: string | null
  loading: boolean
  /** Re-run the fetcher (e.g. after a mutation elsewhere on the page). */
  reload: () => void
}

const toMessage = (err: unknown): string =>
  err instanceof ApiError ? `${err.status} · ${err.message}` : String(err)

/**
 * Fetch on mount, tracking loading / error / data. A response that lands after
 * unmount (or after a `reload`) is ignored.
 */
export function useAsync<T>(fetcher: () => Promise<T>): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [nonce, setNonce] = useState(0)

  const reload = useCallback(() => setNonce((n) => n + 1), [])

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    fetcher().then(
      (result) => {
        if (active) {
          setData(result)
          setLoading(false)
        }
      },
      (err: unknown) => {
        if (active) {
          setError(toMessage(err))
          setLoading(false)
        }
      },
    )
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- fetcher is passed inline; nonce drives re-fetch
  }, [nonce])

  return { data, error, loading, reload }
}
