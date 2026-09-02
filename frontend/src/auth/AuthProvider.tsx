import { type ReactNode, useCallback, useEffect, useState } from 'react'

import { getMe, login as apiLogin, signup as apiSignup, type User } from '../api/auth'
import { getToken, setToken, setUnauthorizedHandler } from '../api/client'
import { AuthContext, type AuthStatus } from './context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<AuthStatus>(() =>
    getToken() ? 'loading' : 'anonymous',
  )

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    setStatus('anonymous')
  }, [])

  const finishLogin = useCallback((token: string, account: User) => {
    setToken(token)
    setUser(account)
    setStatus('authenticated')
  }, [])

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await apiLogin(email, password)
      finishLogin(res.access_token, res.user)
    },
    [finishLogin],
  )

  const signup = useCallback(
    async (email: string, password: string) => {
      const res = await apiSignup(email, password)
      finishLogin(res.access_token, res.user)
    },
    [finishLogin],
  )

  useEffect(() => {
    setUnauthorizedHandler(logout)
  }, [logout])

  // Validate a stored token once on load.
  useEffect(() => {
    if (!getToken()) return
    getMe().then(
      (account) => {
        setUser(account)
        setStatus('authenticated')
      },
      () => {
        setToken(null)
        setStatus('anonymous')
      },
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once on mount
  }, [])

  return (
    <AuthContext.Provider value={{ user, status, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
