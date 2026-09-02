import type { ReactNode } from 'react'

import type { AsyncState } from '../hooks/useAsync'

function Spinner() {
  return (
    <div className="flex items-center gap-2 py-16 text-sm text-slate-500 dark:text-slate-400">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600 dark:border-slate-700 dark:border-t-slate-300" />
      Loading…
    </div>
  )
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300">
      <p className="font-medium">Couldn&rsquo;t reach the API</p>
      <p className="mt-1 font-mono text-xs">{message}</p>
      <p className="mt-2 text-red-700/90 dark:text-red-400/90">
        Check that the backend is running on <code>:8000</code> and the database has been
        seeded.
      </p>
    </div>
  )
}

interface Props<T> {
  state: AsyncState<T>
  children: (data: T) => ReactNode
  /** Return a node to short-circuit rendering (e.g. an empty state). */
  empty?: (data: T) => ReactNode
}

/** Renders loading / error / empty / data states from a {@link useAsync} result. */
export default function AsyncBoundary<T>({ state, children, empty }: Props<T>) {
  if (state.loading) return <Spinner />
  if (state.error) return <ErrorBox message={state.error} />
  if (state.data === null) return null

  const emptyNode = empty?.(state.data)
  if (emptyNode) return <>{emptyNode}</>

  return <>{children(state.data)}</>
}
