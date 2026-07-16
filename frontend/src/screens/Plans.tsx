import { FlagBanner } from '@phosphor-icons/react'
import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePageHeader } from '../components/PageHeader'
import { EmptyState, ErrorNote, Loading, SectionLabel, StatusPill } from '../components/ui'
import { activityMeta } from '../lib/activity'
import { fmtDay, todayKey } from '../lib/format'
import { usePlans } from '../lib/queries'
import type { Plan } from '../lib/types'
import '../styles/plans.css'

function planProgress(plan: Plan): number | null {
  if (!plan.end_date) return null
  const start = new Date(plan.start_date).getTime()
  const end = new Date(plan.end_date).getTime()
  if (end <= start) return null
  return Math.min(1, Math.max(0, (Date.now() - start) / (end - start)))
}

function PlanCard({ plan }: { plan: Plan }) {
  const navigate = useNavigate()
  const meta = activityMeta(plan.activity_type)
  const active = plan.status === 'active'
  const frac = planProgress(plan)
  const SEGS = 12
  const done = frac != null ? Math.floor(frac * SEGS) : 0
  const range = `${fmtDay(plan.start_date)} — ${plan.end_date ? fmtDay(plan.end_date) : 'open'}`

  return (
    <button className={`plan-card${active ? ' active' : ''}`} onClick={() => navigate(`/plans/${plan.id}`)}>
      {active && <span className="pc-glow" />}
      <div className="pc-top">
        <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
          <span className="icon-tile" style={{ color: meta.color }}>
            <meta.icon size={21} />
          </span>
          <div>
            <div className="pc-name">{plan.name}</div>
            <div className="pc-range">{range.toUpperCase()}</div>
          </div>
        </div>
        <StatusPill status={plan.status} />
      </div>
      {plan.description && <div className="pc-desc">{plan.description}</div>}
      {active && frac != null && (
        <div className="pc-segs">
          {Array.from({ length: SEGS }, (_, i) => (
            <span
              key={i}
              style={{
                background: i < done ? 'var(--green)' : i === done ? 'var(--accent)' : '#2A2520',
              }}
            />
          ))}
        </div>
      )}
    </button>
  )
}

export function Plans() {
  const { data, isLoading, error } = usePlans()

  const groups = useMemo(() => {
    const plans = data ?? []
    const today = todayKey()
    const current = plans.filter((p) => p.status === 'active')
    const upcoming = plans.filter((p) => p.status !== 'active' && p.start_date > today)
    const past = plans.filter((p) => p.status !== 'active' && p.start_date <= today)
    return [
      { label: 'Current', count: `${current.length} active`, plans: current },
      { label: 'Upcoming', count: `${upcoming.length} future`, plans: upcoming },
      { label: 'Archived', count: String(past.length), plans: past },
    ].filter((g) => g.plans.length > 0)
  }, [data])

  usePageHeader('Plans', data ? `${data.length} plans · ${data.filter((p) => p.status === 'active').length} active` : undefined)

  if (isLoading) return <Loading label="Loading plans…" />
  if (error) return <ErrorNote error={error} />

  if (groups.length === 0) {
    return (
      <div className="card screen">
        <EmptyState icon={FlagBanner} title="No plans yet">
          Training plans are created by your LLM coach in conversation — goals, guardrails,
          phases, and a weekly schedule all land here.
        </EmptyState>
      </div>
    )
  }

  return (
    <div className="screen">
      {groups.map((g) => (
        <div className="plan-group" key={g.label}>
          <div className="group-head">
            <SectionLabel>{g.label}</SectionLabel>
            <span className="mono-meta" style={{ color: 'var(--faint)' }}>
              {g.count}
            </span>
          </div>
          <div className="plan-grid">
            {g.plans.map((p) => (
              <PlanCard plan={p} key={p.id} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
