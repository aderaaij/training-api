import { Brain, Desktop, DeviceMobile, Key, Plus, SignOut } from '@phosphor-icons/react'
import type { Icon } from '@phosphor-icons/react'
import { useState } from 'react'
import { usePageHeader } from '../components/PageHeader'
import { ConfirmDialog, ErrorNote, Loading, SectionLabel } from '../components/ui'
import { useAuth } from '../lib/auth'
import { fmtDayYear, relTime } from '../lib/format'
import { useMe, useRevokeToken } from '../lib/queries'
import type { ApiTokenInfo } from '../lib/types'
import '../styles/settings.css'

function tokenIcon(name: string): Icon {
  const n = name.toLowerCase()
  if (n.includes('iphone') || n.includes('phone') || n.includes('ios')) return DeviceMobile
  if (n.includes('mcp') || n.includes('coach')) return Brain
  if (n.includes('web') || n.includes('dashboard') || n.includes('browser')) return Desktop
  return Key
}

function tokenMeta(t: ApiTokenInfo): string {
  const parts = [`created ${fmtDayYear(t.createdAt)}`, `last used ${relTime(t.lastUsedAt)}`]
  if (t.expiresAt) {
    const expired = new Date(t.expiresAt).getTime() < Date.now()
    parts.push(`${expired ? 'expired' : 'expires'} ${fmtDayYear(t.expiresAt)}`)
  } else {
    parts.push('no expiry')
  }
  return parts.join(' · ')
}

export function Settings() {
  const { user, tokenId, logout } = useAuth()
  const { data, isLoading, error } = useMe()
  const revoke = useRevokeToken()
  const [revoking, setRevoking] = useState<ApiTokenInfo | null>(null)
  const [confirmLogout, setConfirmLogout] = useState(false)

  usePageHeader('Settings', data ? `${data.tokens.length} active tokens` : undefined)

  const me = data?.user ?? user
  const initial = (me?.displayName || me?.username || '?').charAt(0).toUpperCase()

  return (
    <div className="settings-wrap screen">
      <div style={{ marginBottom: 12 }}>
        <SectionLabel>Profile</SectionLabel>
      </div>
      <div className="profile-card">
        <span className="avatar-lg">{initial}</span>
        <div style={{ flex: 1, minWidth: 160 }}>
          <div className="display" style={{ fontSize: 18, fontWeight: 600 }}>
            {me?.displayName || me?.username}
          </div>
          <div className="mono-meta" style={{ marginTop: 3 }}>
            {me?.username} · {me?.role === 'admin' ? 'Admin' : 'Member'}
          </div>
        </div>
        <button
          className="pending-btn"
          title="The change-password endpoint isn't built yet — an admin can reset it via CLI."
          disabled
        >
          Change password
          <span className="pending-tag">BACKEND PENDING</span>
        </button>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <SectionLabel>Devices &amp; tokens</SectionLabel>
        <button
          className="pending-btn"
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 13px', fontSize: 12 }}
          title="Self-service token minting isn't built yet — today a token is created by login or CLI."
          disabled
        >
          <Plus size={14} />
          New token
          <span className="pending-tag" style={{ display: 'inline', marginTop: 0 }}>
            PENDING
          </span>
        </button>
      </div>

      {error && <ErrorNote error={error} />}
      {isLoading && <Loading label="Loading tokens…" />}

      {data && (
        <div className="token-list">
          {data.tokens.map((t) => {
            const TIcon = tokenIcon(t.name)
            const isCurrent = t.id === tokenId
            const expired = t.expiresAt != null && new Date(t.expiresAt).getTime() < Date.now()
            return (
              <div className="token-row" key={t.id}>
                <span
                  className="icon-tile"
                  style={{ width: 36, height: 36, color: expired ? 'var(--faint)' : isCurrent ? 'var(--accent)' : 'var(--text-3)' }}
                >
                  <TIcon size={19} />
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="t-name">
                    {t.name || 'Unnamed token'}
                    {isCurrent && <span className="t-this">This device</span>}
                  </div>
                  <div className="t-meta">{tokenMeta(t)}</div>
                </div>
                <button
                  className="t-action"
                  style={{ color: isCurrent ? 'var(--amber)' : 'var(--red)' }}
                  onClick={() => (isCurrent ? setConfirmLogout(true) : setRevoking(t))}
                >
                  {isCurrent ? 'Log out' : expired ? 'Remove' : 'Revoke'}
                </button>
              </div>
            )
          })}
        </div>
      )}

      <div style={{ marginTop: 26 }}>
        <button className="btn-danger-outline" style={{ padding: '12px 22px', fontSize: 14 }} onClick={() => setConfirmLogout(true)}>
          <SignOut size={17} />
          Log out · revoke this session
        </button>
      </div>

      {revoking && (
        <ConfirmDialog
          title={`Revoke “${revoking.name || 'this token'}”?`}
          body="The device using this token stops authenticating immediately. It can be re-added by logging in again on that device."
          confirmLabel="Revoke"
          busy={revoke.isPending}
          onCancel={() => setRevoking(null)}
          onConfirm={() =>
            revoke.mutate(revoking.id, {
              onSuccess: () => setRevoking(null),
            })
          }
        />
      )}

      {confirmLogout && (
        <ConfirmDialog
          title="Log out?"
          body="This revokes the web dashboard's token on the server and clears it from this browser."
          confirmLabel="Log out"
          onCancel={() => setConfirmLogout(false)}
          onConfirm={() => void logout()}
        />
      )}
    </div>
  )
}
