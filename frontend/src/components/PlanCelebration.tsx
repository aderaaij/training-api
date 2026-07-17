import { ChatCircleText, Star, Trophy } from '@phosphor-icons/react'
import { useMemo, useState } from 'react'
import { activityMeta } from '../lib/activity'
import { fmtDay } from '../lib/format'
import { useCompletePlan, usePlans } from '../lib/queries'
import type { Plan, PlanCompleteResponse } from '../lib/types'
import { ErrorNote, Modal } from './ui'

const CONFETTI_COLORS = ['#ff6a3d', '#5fb98a', '#6e91ff', '#d9a93e', '#7c5cff', '#48c7c7']

function Confetti() {
  const pieces = useMemo(
    () =>
      Array.from({ length: 44 }, (_, i) => ({
        left: Math.random() * 100,
        delay: Math.random() * 2.5,
        duration: 2.8 + Math.random() * 2.2,
        tilt: Math.floor(Math.random() * 360),
        size: 6 + Math.random() * 5,
        color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
      })),
    [],
  )
  return (
    <div className="confetti" aria-hidden>
      {pieces.map((p, i) => (
        <span
          key={i}
          style={
            {
              left: `${p.left}%`,
              width: p.size,
              height: p.size * 1.6,
              background: p.color,
              animationDelay: `${p.delay}s`,
              animationDuration: `${p.duration}s`,
              '--tilt': `${p.tilt}deg`,
            } as React.CSSProperties
          }
        />
      ))}
    </div>
  )
}

function planWeeks(plan: Plan): number | null {
  if (!plan.end_date) return null
  const ms = new Date(plan.end_date).getTime() - new Date(plan.start_date).getTime()
  return ms > 0 ? Math.max(1, Math.round(ms / (7 * 86400_000))) : null
}

export function PlanCelebrationModal({ plan, onClose }: { plan: Plan; onClose: () => void }) {
  const [rating, setRating] = useState(0)
  const [feedback, setFeedback] = useState('')
  const [result, setResult] = useState<PlanCompleteResponse | null>(null)
  const complete = useCompletePlan()

  const meta = activityMeta(plan.activity_type)
  const weeks = planWeeks(plan)
  const done = plan.progress?.runs_completed ?? 0
  const skipped = plan.progress?.runs_skipped ?? 0

  const submit = () =>
    complete.mutate(
      { id: plan.id, feedback: feedback.trim() || undefined, rating: rating || undefined },
      { onSuccess: setResult },
    )

  return (
    <Modal onClose={onClose} width={460}>
      <div className="celebrate">
        <Confetti />
        <div className="cel-trophy">
          <Trophy size={30} weight="fill" />
        </div>
        <div className="display cel-title">Plan complete!</div>
        <div className="cel-plan">{plan.name}</div>
        <div className="mono-meta">
          {fmtDay(plan.start_date).toUpperCase()} — {plan.end_date ? fmtDay(plan.end_date).toUpperCase() : 'NOW'}
        </div>

        <div className="cel-stats">
          {done > 0 && (
            <div className="cel-stat">
              <div className="v">{done}</div>
              <div className="k">Sessions done</div>
            </div>
          )}
          {skipped > 0 && (
            <div className="cel-stat">
              <div className="v">{skipped}</div>
              <div className="k">Skipped</div>
            </div>
          )}
          {weeks && (
            <div className="cel-stat">
              <div className="v">{weeks}</div>
              <div className="k">Weeks</div>
            </div>
          )}
        </div>

        {result === null ? (
          <>
            <div className="field-label" style={{ marginTop: 20 }}>
              How was this block?
            </div>
            <div className="rating-row">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  type="button"
                  className={n <= rating ? 'on' : ''}
                  aria-label={`${n} of 5`}
                  onClick={() => setRating(n === rating ? 0 : n)}
                >
                  <Star size={26} weight={n <= rating ? 'fill' : 'regular'} />
                </button>
              ))}
            </div>
            <textarea
              className="field-input"
              rows={4}
              style={{ marginTop: 12, resize: 'vertical', textAlign: 'left' }}
              placeholder="What worked, what didn't? Your coach reads this when shaping the next block."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
            />
            {complete.isError && (
              <div style={{ marginTop: 12, textAlign: 'left' }}>
                <ErrorNote error={complete.error} />
              </div>
            )}
            <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
              <button className="btn-ghost" style={{ flex: 1, justifyContent: 'center' }} onClick={onClose}>
                Not now
              </button>
              <button
                className="btn-accent"
                style={{ flex: 1.4, justifyContent: 'center' }}
                disabled={complete.isPending}
                onClick={submit}
              >
                {complete.isPending ? 'Wrapping up…' : 'Complete plan'}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="cel-next">
              <ChatCircleText size={20} weight="fill" color="var(--accent)" style={{ flexShrink: 0, marginTop: 2 }} />
              <div style={{ textAlign: 'left' }}>
                {result.next_plan ? (
                  <>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>
                      Next up: {result.next_plan.name}
                    </div>
                    <div style={{ fontSize: 12.5, color: 'var(--muted)', marginTop: 3 }}>
                      Starts {fmtDay(result.next_plan.start_date)} — already on your plans.
                    </div>
                  </>
                ) : (
                  <>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>
                      No {meta.label.toLowerCase()} plan lined up yet
                    </div>
                    <div style={{ fontSize: 12.5, color: 'var(--muted)', marginTop: 3 }}>
                      Start a conversation with your coach to shape the next block
                      {feedback.trim() || rating ? ' — your feedback is already saved for them.' : '.'}
                    </div>
                  </>
                )}
              </div>
            </div>
            <button
              className="btn-accent"
              style={{ width: '100%', justifyContent: 'center', marginTop: 18 }}
              onClick={onClose}
            >
              Done
            </button>
          </>
        )}
      </div>
    </Modal>
  )
}

export function FinishBanner({ plan }: { plan: Plan }) {
  const [open, setOpen] = useState(false)
  const done = plan.progress?.runs_completed ?? 0

  // Completing the plan refetches it and drops `finishable`, hiding the
  // banner — but the modal must survive that to show its success panel,
  // so visibility is decided here, not by the parent.
  if (!plan.finishable && !open) return null

  return (
    <>
      {plan.finishable && (
        <div className="finish-banner">
          <span className="fb-trophy">
            <Trophy size={22} weight="fill" />
          </span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="fb-title">{plan.name} is complete 🎉</div>
            <div className="fb-sub">
              {done > 0 ? `All ${done} sessions are in the books.` : 'The plan window has wrapped up.'}
            </div>
          </div>
          <button className="btn-accent" onClick={() => setOpen(true)}>
            Celebrate & wrap up
          </button>
        </div>
      )}
      {open && <PlanCelebrationModal plan={plan} onClose={() => setOpen(false)} />}
    </>
  )
}

/** Finish banners for every finishable plan — drop-in for Overview and Plans.
 * Maps over ALL plans (each banner hides itself) so a just-completed plan's
 * modal isn't unmounted mid-celebration. */
export function FinishBanners() {
  const { data } = usePlans()
  return (
    <>
      {(data ?? []).map((p) => (
        <FinishBanner plan={p} key={p.id} />
      ))}
    </>
  )
}
