/** Static demo mode: the whole app runs in the browser, no backend. */
export const DEMO = import.meta.env.VITE_DEMO === '1'

export const DEMO_USER = {
  id: 1,
  email: 'demo@studypath.app',
  created_at: new Date(Date.now() - 30 * 86_400_000).toISOString(),
}
