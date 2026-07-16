import { Plus, TerminalWindow, UsersThree } from '@phosphor-icons/react'
import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { usePageHeader } from '../components/PageHeader'
import { Modal, SectionLabel } from '../components/ui'
import { api, ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'
import { relTime } from '../lib/format'
import { useMe } from '../lib/queries'
import '../styles/settings.css'

interface AdminUserRow {
  id: string
  username: string
  displayName: string
  role: string
  isActive: boolean
  tokenCount: number
  lastSeenAt: string | null
}

/**
 * Planned contract (multi-user plan, Phase 3.5): GET /api/admin/users.
 * Not built yet — a 404/405 here means "CLI only today" and the screen
 * degrades to the pending state by design.
 */
function useAdminUsers(enabled: boolean) {
  return useQuery({
    queryKey: ['admin-users'],
    queryFn: () => api.get<AdminUserRow[]>('/api/admin/users'),
    enabled,
    retry: false,
  })
}

function CreateUserModal({ onClose }: { onClose: () => void }) {
  const [displayName, setDisplayName] = useState('')
  const [username, setUsername] = useState('')
  const [isAdmin, setIsAdmin] = useState(false)

  const uname = username.trim() || displayName.trim().split(' ')[0]?.toLowerCase() || '<username>'
  const cli = [
    `docker compose exec backend \\`,
    `  python -m app.cli create-user ${uname}${isAdmin ? ' --admin' : ''} \\`,
    `  --display-name "${displayName.trim() || uname}"`,
  ].join('\n')

  return (
    <Modal onClose={onClose} width={460}>
      <div className="display" style={{ fontSize: 20, fontWeight: 600 }}>
        Create member
      </div>
      <div style={{ fontSize: 12.5, color: 'var(--muted)', margin: '5px 0 20px' }}>
        The HTTP endpoint is pending — this mirrors{' '}
        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-3)' }}>python -m app.cli create-user</span>
        , which prompts for the password so it never lands in shell history.
      </div>

      <div className="field-label">Display name</div>
      <input
        className="field-input"
        style={{ marginBottom: 14 }}
        placeholder="Sam Rivera"
        value={displayName}
        onChange={(e) => setDisplayName(e.target.value)}
      />

      <div style={{ display: 'flex', gap: 12, marginBottom: 18 }}>
        <div style={{ flex: 1 }}>
          <div className="field-label">Username</div>
          <input
            className="field-input"
            placeholder="sam"
            autoCapitalize="none"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        <div style={{ flex: 1 }}>
          <div className="field-label">Role</div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button className={`filter-chip${!isAdmin ? ' on' : ''}`} style={{ flex: 1 }} onClick={() => setIsAdmin(false)}>
              Member
            </button>
            <button className={`filter-chip${isAdmin ? ' on' : ''}`} style={{ flex: 1 }} onClick={() => setIsAdmin(true)}>
              Admin
            </button>
          </div>
        </div>
      </div>

      <div className="field-label" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <TerminalWindow size={13} />
        Run on ardencore (in ~/training-api)
      </div>
      <div className="cli-box" style={{ marginTop: 4 }}>
        {cli}
      </div>

      <div style={{ display: 'flex', gap: 10, marginTop: 22 }}>
        <button className="btn-ghost" style={{ flex: 1 }} onClick={onClose}>
          Close
        </button>
        <button
          className="btn-accent"
          style={{ flex: 1 }}
          onClick={() => {
            void navigator.clipboard?.writeText(cli.replace(/ \\\n {2}/g, ' '))
            onClose()
          }}
        >
          Copy command
        </button>
      </div>
    </Modal>
  )
}

export function Users() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const adminUsers = useAdminUsers(isAdmin)
  const me = useMe()
  const [modalOpen, setModalOpen] = useState(false)

  usePageHeader('User management', 'household accounts')

  if (!isAdmin) return <Navigate to="/" replace />

  const endpointPending =
    adminUsers.error instanceof ApiError &&
    (adminUsers.error.status === 404 || adminUsers.error.status === 405)

  const rows: AdminUserRow[] =
    adminUsers.data ??
    // Fallback while the admin endpoints are CLI-only: show at least yourself.
    (me.data
      ? [
          {
            id: me.data.user.id,
            username: me.data.user.username,
            displayName: me.data.user.displayName,
            role: me.data.user.role,
            isActive: true,
            tokenCount: me.data.tokens.length,
            lastSeenAt: new Date().toISOString(),
          },
        ]
      : [])

  return (
    <div className="users-wrap screen">
      <div className="users-head">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <SectionLabel>Household members</SectionLabel>
          {endpointPending && <span className="pending-banner">HTTP endpoints pending · CLI only today</span>}
        </div>
        <button className="btn-accent" style={{ padding: '9px 16px', fontSize: 13 }} onClick={() => setModalOpen(true)}>
          <Plus size={15} weight="bold" />
          Create user
        </button>
      </div>

      <div className="users-table">
        <div className="u-head">
          <span>Member</span>
          <span>Role</span>
          <span className="hide-sm">Tokens</span>
          <span className="hide-sm">Last seen</span>
          <span style={{ textAlign: 'right' }}>Status</span>
        </div>
        {rows.map((u) => (
          <div className="u-row" key={u.id}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
              <span
                className="avatar-lg"
                style={{ width: 38, height: 38, fontSize: 15, borderRadius: 11, color: u.role === 'admin' ? 'var(--accent)' : 'var(--blue)' }}
              >
                {(u.displayName || u.username).charAt(0).toUpperCase()}
              </span>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 14.5, fontWeight: 600 }}>{u.displayName || u.username}</div>
                <div className="mono-meta" style={{ fontSize: 10.5 }}>
                  {u.username}
                </div>
              </div>
            </div>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: u.role === 'admin' ? 'var(--accent)' : 'var(--text-3)' }}>
              {u.role === 'admin' ? 'Admin' : 'Member'}
            </span>
            <span className="mono-meta hide-sm" style={{ fontSize: 12.5 }}>
              {u.tokenCount}
            </span>
            <span className="mono-meta hide-sm" style={{ fontSize: 11.5 }}>
              {relTime(u.lastSeenAt)}
            </span>
            <span style={{ textAlign: 'right' }}>
              <span
                className="status-pill"
                style={{
                  color: u.isActive ? 'var(--green)' : 'var(--muted)',
                  background: u.isActive ? 'rgba(95,185,138,0.14)' : 'rgba(245,235,220,0.06)',
                }}
              >
                {u.isActive ? 'Active' : 'Off'}
              </span>
            </span>
          </div>
        ))}
      </div>

      {endpointPending && (
        <div style={{ marginTop: 14 }}>
          <div style={{ fontSize: 12, color: 'var(--faint)', lineHeight: 1.6 }}>
            Listing every member needs the planned admin endpoints (
            <span style={{ fontFamily: 'var(--font-mono)' }}>GET /api/admin/users</span>) — until then only your own
            account is shown. Manage members over SSH:
          </div>
          <div className="cli-box">
            {`python -m app.cli list-users\npython -m app.cli create-user <username> --display-name "Name" [--admin]\npython -m app.cli set-password <username>\npython -m app.cli create-token <username> --name "device"`}
          </div>
        </div>
      )}

      <div style={{ marginTop: 14, fontSize: 12, color: 'var(--faint)', lineHeight: 1.5, display: 'flex', gap: 8, alignItems: 'center' }}>
        <UsersThree size={15} />
        Deactivating a member revokes all their tokens — their devices stop authenticating immediately. No self-service
        registration exists by design.
      </div>

      {modalOpen && <CreateUserModal onClose={() => setModalOpen(false)} />}
    </div>
  )
}
