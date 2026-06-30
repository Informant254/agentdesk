'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { setAuthToken } from '@/lib/api'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://agentdesk-mzx6.onrender.com'

export default function AuthCallback() {
  const [status, setStatus] = useState('Completing sign in...')

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const params = new URLSearchParams(window.location.search)
        const code = params.get('code')
        if (code) {
          const { error } = await supabase.auth.exchangeCodeForSession(code)
          if (error) throw error
        }
        const { data: { session }, error: sessionError } = await supabase.auth.getSession()
        if (sessionError || !session) throw sessionError || new Error('No session')

        const res = await fetch(`${API_URL}/api/auth/social`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ supabase_token: session.access_token }),
        })
        if (res.ok) {
          const data = await res.json()
          setAuthToken(data.access_token)
        }
        setStatus('Signed in! Redirecting...')
        setTimeout(() => { window.location.href = '/' }, 600)
      } catch {
        setStatus('Sign in failed. Redirecting...')
        setTimeout(() => { window.location.href = '/' }, 2000)
      }
    }
    handleCallback()
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-slate-100">
      <div className="text-center">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-slate-600">{status}</p>
      </div>
    </div>
  )
}
