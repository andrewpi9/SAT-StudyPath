import { useEffect, useState } from 'react'

import { ApiError } from '../api/client'

export interface AsyncState<T> {
  data: T | null
  error: string | null
  loading: boolean
}

const toMessage = (err: unknown): string =>
  err instanceof ApiError ? `${err.status} · ${err.message}` : String(err)

/**
 * Fetch once on mount, tracking loading / error / data. A response that lands
 * after unmount is ignored. Pages here load their data once and don't refetch,
 * so there is deliberately no dependency array or manual reload.
 */
export function useAsync<T>(fetcher: () => Promise<T>): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    error: null,
    loading: true,
  })

  useEffect(() => {
    let active = true
    fetcher().then(
      (data) => {
        if (active) setState({ data, error: null, loading: false })
      },
      (err: unknown) => {
        if (active) setState({ data: null, error: toMessage(err), loading: false })
      },
    )
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount-only by design
  }, [])

  return state
}
