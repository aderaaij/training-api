import {
  Brain,
  ChatCircle,
  Eye,
  GitBranch,
  Heart,
  House,
  LockSimple,
  PencilSimple,
  Timer,
  Trash,
  WarningOctagon,
} from '@phosphor-icons/react'
import type { Icon } from '@phosphor-icons/react'
import { useMemo, useState } from 'react'
import { usePageHeader } from '../components/PageHeader'
import {
  ConfirmDialog,
  EmptyState,
  ErrorNote,
  ImportanceDots,
  Loading,
  Modal,
} from '../components/ui'
import { NOTE_KINDS } from '../lib/activity'
import { fmtDay, fmtDayYear } from '../lib/format'
import { useDeleteNote, useNoteContext, usePlanNotes, useUpdateNote } from '../lib/queries'
import type { NoteKind, PlanNote } from '../lib/types'
import '../styles/notes.css'

const KIND_ICONS: Record<string, Icon> = {
  decision: GitBranch,
  preference: Heart,
  constraint: LockSimple,
  life_context: House,
  observation: Eye,
  blocker: WarningOctagon,
}

function isExpired(n: PlanNote): boolean {
  return n.expiresAt != null && new Date(n.expiresAt).getTime() < Date.now()
}

function NoteEditModal({ note, onClose }: { note: PlanNote; onClose: () => void }) {
  const update = useUpdateNote()
  const [kind, setKind] = useState<NoteKind>(note.kind)
  const [importance, setImportance] = useState(note.importance)
  const [summary, setSummary] = useState(note.summary)
  const [body, setBody] = useState(note.body ?? '')
  const [expiresAt, setExpiresAt] = useState(note.expiresAt ? note.expiresAt.slice(0, 10) : '')

  const save = () => {
    update.mutate(
      {
        id: note.id,
        patch: {
          kind,
          importance,
          summary: summary.trim(),
          body: body.trim() || null,
          expiresAt: expiresAt ? new Date(`${expiresAt}T23:59:59`).toISOString() : null,
        },
      },
      { onSuccess: onClose },
    )
  }

  return (
    <Modal onClose={onClose} width={460}>
      <div className="display" style={{ fontSize: 19, fontWeight: 600 }}>
        Edit note
      </div>
      <div style={{ fontSize: 12.5, color: 'var(--muted)', margin: '5px 0 20px' }}>
        Correcting the coach’s memory is a first-class action — the LLM reads this back.
      </div>

      <div className="field-label">Kind</div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 14 }}>
        {(Object.keys(NOTE_KINDS) as NoteKind[]).map((k) => (
          <button
            key={k}
            className={`filter-chip${kind === k ? ' on' : ''}`}
            style={{ ['--chip-color' as string]: NOTE_KINDS[k].color, padding: '6px 11px', fontSize: 12 }}
            onClick={() => setKind(k)}
          >
            {NOTE_KINDS[k].label}
          </button>
        ))}
      </div>

      <div className="field-label">Summary · {280 - summary.length} left</div>
      <textarea
        className="field-input"
        style={{ marginBottom: 14, resize: 'vertical', minHeight: 60 }}
        maxLength={280}
        value={summary}
        onChange={(e) => setSummary(e.target.value)}
      />

      <div className="field-label">Body (optional)</div>
      <textarea
        className="field-input"
        style={{ marginBottom: 14, resize: 'vertical', minHeight: 80 }}
        value={body}
        onChange={(e) => setBody(e.target.value)}
      />

      <div style={{ display: 'flex', gap: 12, marginBottom: 22 }}>
        <div style={{ flex: 1 }}>
          <div className="field-label">Importance</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {[1, 2, 3].map((v) => (
              <button
                key={v}
                className={`filter-chip${importance === v ? ' on' : ''}`}
                style={{ flex: 1, textAlign: 'center', justifyContent: 'center' }}
                onClick={() => setImportance(v)}
              >
                {v}
              </button>
            ))}
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <div className="field-label">Expires (optional)</div>
          <input
            type="date"
            className="field-input"
            value={expiresAt}
            onChange={(e) => setExpiresAt(e.target.value)}
          />
        </div>
      </div>

      {update.error && (
        <div style={{ marginBottom: 12 }}>
          <ErrorNote error={update.error} />
        </div>
      )}

      <div style={{ display: 'flex', gap: 10 }}>
        <button className="btn-ghost" style={{ flex: 1 }} onClick={onClose}>
          Cancel
        </button>
        <button
          className="btn-accent"
          style={{ flex: 1 }}
          disabled={update.isPending || summary.trim().length === 0}
          onClick={save}
        >
          {update.isPending ? 'Saving…' : 'Save'}
        </button>
      </div>
    </Modal>
  )
}

function CoachPanel() {
  const { data, isLoading } = useNoteContext()
  if (isLoading || !data) {
    return (
      <div className="coach-panel">
        <Loading label="Loading context…" />
      </div>
    )
  }
  const fresh = data.last_note_age_days != null && data.last_note_age_days < 7

  return (
    <div className="coach-panel">
      <span className="cp-glow" />
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <Brain size={22} weight="bold" color="var(--accent)" />
        <div>
          <div className="cp-title">What your coach sees</div>
          <div className="cp-endpoint">GET /api/plan-notes/context</div>
        </div>
      </div>

      <div className={`cp-banner ${fresh ? 'fresh' : 'stale'}`}>
        <span
          className="dot"
          style={{
            background: fresh ? 'var(--green)' : 'var(--amber)',
            boxShadow: `0 0 7px ${fresh ? 'var(--green)' : 'var(--amber)'}`,
          }}
        />
        <span className="text" style={{ color: fresh ? '#B8D8C6' : '#E8D3AC' }}>
          {data.continuity_hint}
        </span>
      </div>

      <div className="mono-label" style={{ marginBottom: 8 }}>
        Resolved active plan
      </div>
      <div className="cp-plan">
        {data.plan ? (
          <>
            <div className="display" style={{ fontSize: 14, fontWeight: 600 }}>
              {data.plan.name}
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 3 }}>
              {fmtDay(data.plan.start_date)} — {data.plan.end_date ? fmtDay(data.plan.end_date) : 'open'} ·{' '}
              {data.plan.status}
            </div>
          </>
        ) : (
          <div style={{ fontSize: 12.5, color: 'var(--muted)' }}>No active plan resolved.</div>
        )}
      </div>

      <div className="mono-label" style={{ marginBottom: 10 }}>
        Ranked notes fed to LLM
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {data.notes.length === 0 && (
          <div style={{ fontSize: 12.5, color: 'var(--muted)' }}>No notes in the context window.</div>
        )}
        {data.notes.slice(0, 8).map((n) => {
          const k = NOTE_KINDS[n.kind]
          return (
            <div className="cp-note" key={n.id} style={{ borderLeftColor: k?.color ?? 'var(--accent)' }}>
              <span className="k" style={{ color: k?.color ?? 'var(--accent)' }}>
                {k?.label ?? n.kind}
              </span>
              <span className="t">{n.summary}</span>
            </div>
          )
        })}
      </div>

      <div style={{ fontSize: 11, color: 'var(--faint)', lineHeight: 1.5, marginTop: 16 }}>
        Expired &amp; low-importance notes are omitted. Edit or delete any note to correct what the coach remembers.
      </div>
    </div>
  )
}

export function Notes() {
  const [kindFilter, setKindFilter] = useState<string | undefined>(undefined)
  const { data: notes, isLoading, error } = usePlanNotes({ kind: kindFilter, includeExpired: true })
  const deleteNote = useDeleteNote()
  const [editing, setEditing] = useState<PlanNote | null>(null)
  const [deleting, setDeleting] = useState<PlanNote | null>(null)

  const activeCount = useMemo(() => (notes ?? []).filter((n) => !isExpired(n)).length, [notes])
  usePageHeader('Coach notes', notes ? `${activeCount} active · what your coach remembers` : undefined)

  return (
    <div className="screen">
      <div className="notes-grid">
        <div>
          <div className="note-filters">
            <button
              className={`filter-chip${kindFilter === undefined ? ' on' : ''}`}
              onClick={() => setKindFilter(undefined)}
            >
              All
            </button>
            {Object.entries(NOTE_KINDS).map(([k, meta]) => (
              <button
                key={k}
                className={`filter-chip${kindFilter === k ? ' on' : ''}`}
                style={{ ['--chip-color' as string]: meta.color }}
                onClick={() => setKindFilter(k)}
              >
                {meta.label}s
              </button>
            ))}
          </div>

          {error && <ErrorNote error={error} />}
          {isLoading && <Loading label="Loading notes…" />}

          {!isLoading && (notes ?? []).length === 0 && !error && (
            <div className="card">
              <EmptyState icon={Brain} title="No notes yet">
                As you talk to your LLM coach it distils decisions, preferences, constraints and
                observations into notes here — its memory between conversations.
              </EmptyState>
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {(notes ?? []).map((n) => {
              const k = NOTE_KINDS[n.kind]
              const KindIcon = KIND_ICONS[n.kind] ?? Eye
              const expired = isExpired(n)
              return (
                <div
                  className={`note-card${expired ? ' expired' : ''}`}
                  key={n.id}
                  style={{
                    borderColor: expired
                      ? 'rgba(245,235,220,0.05)'
                      : `color-mix(in srgb, ${k?.color ?? 'var(--accent)'} 22%, transparent)`,
                  }}
                >
                  <div className="n-head">
                    <span
                      className="note-kind"
                      style={{
                        color: k?.color,
                        background: `color-mix(in srgb, ${k?.color ?? 'var(--accent)'} 16%, transparent)`,
                      }}
                    >
                      <KindIcon size={12} weight="fill" />
                      {n.kind.replace('_', ' ')}
                    </span>
                    <ImportanceDots value={n.importance} color={k?.color ?? 'var(--accent)'} />
                    {expired && <span className="note-expired-tag">Expired</span>}
                    <span className="n-actions">
                      <button title="Edit" onClick={() => setEditing(n)}>
                        <PencilSimple size={15} />
                      </button>
                      <button title="Delete" onClick={() => setDeleting(n)}>
                        <Trash size={15} />
                      </button>
                    </span>
                  </div>
                  <div className="n-summary">{n.summary}</div>
                  {n.body && <div className="n-body">{n.body}</div>}
                  <div className="n-foot">
                    <span>{fmtDayYear(n.created_at)}</span>
                    {n.conversationId && (
                      <span className="f-item">
                        <ChatCircle size={12} />
                        {n.conversationId.slice(0, 8)}
                      </span>
                    )}
                    {n.expiresAt && (
                      <span className="f-item" style={{ color: 'var(--muted)' }}>
                        <Timer size={12} />
                        {expired ? 'expired' : 'expires'} {fmtDay(n.expiresAt)}
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <CoachPanel />
      </div>

      {editing && <NoteEditModal note={editing} onClose={() => setEditing(null)} />}
      {deleting && (
        <ConfirmDialog
          title="Delete this note?"
          body={
            <>
              “{deleting.summary}”
              <br />
              The coach will no longer see it in any future conversation.
            </>
          }
          confirmLabel="Delete"
          busy={deleteNote.isPending}
          onCancel={() => setDeleting(null)}
          onConfirm={() =>
            deleteNote.mutate(deleting.id, {
              onSuccess: () => setDeleting(null),
            })
          }
        />
      )}
    </div>
  )
}
