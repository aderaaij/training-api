import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

export interface PageHeader {
  title: string
  subtitle?: string
  /** Route to navigate to for the back button; absent = no back button. */
  backTo?: string
}

interface HeaderCtx {
  header: PageHeader
  setHeader: (h: PageHeader) => void
}

const Ctx = createContext<HeaderCtx | null>(null)

export function PageHeaderProvider({ children }: { children: ReactNode }) {
  const [header, setHeader] = useState<PageHeader>({ title: '' })
  const value = useMemo(() => ({ header, setHeader }), [header])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function usePageHeaderValue(): PageHeader {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('usePageHeaderValue outside provider')
  return ctx.header
}

/** Screens declare their topbar content with this. */
export function usePageHeader(title: string, subtitle?: string, backTo?: string) {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('usePageHeader outside provider')
  const { setHeader } = ctx
  useEffect(() => {
    setHeader({ title, subtitle, backTo })
  }, [setHeader, title, subtitle, backTo])
}
