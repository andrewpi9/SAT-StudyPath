import * as demoApi from '../demo/api'
import { DEMO } from '../lib/demo'
import { api } from './client'

export interface User {
  id: number
  email: string
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export const DEMO_CREDENTIALS = {
  email: 'demo@studypath.app',
  password: 'demopassword',
}

export function signup(email: string, password: string): Promise<AuthResponse> {
  return api.post<AuthResponse>('/auth/signup', { email, password })
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return api.post<AuthResponse>('/auth/login', { email, password })
}

export function getMe(): Promise<User> {
  return DEMO ? demoApi.getMe() : api.get<User>('/auth/me')
}
