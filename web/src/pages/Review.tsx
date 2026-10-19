import { Alert, Button, Checkbox, Group, Kbd, List, Loader, Paper, Stack, Text, Textarea, Title } from '@mantine/core'
import { useHotkeys } from '@mantine/hooks'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { type ApplyResult, type Choice, applicationQuery, applicationsQuery, postReview, reviewQuery } from '../api'
import LeadDetail from '../components/LeadDetail'
import { type Pending, currentLead, loadPending, savePending, toBatch } from '../review'

const CHOICES: { decision: Choice; label: string; key: string; color: string }[] = [
  { decision: 'apply', label: 'Apply', key: 'Y', color: 'blue' },
  { decision: 'dismiss', label: 'Dismiss', key: 'N', color: 'red' },
  { decision: 'skip', label: 'Skip', key: 'S', color: 'gray' },
]

export default function Review() {
  const qc = useQueryClient()
  const queue = useQuery(reviewQuery)
  const apps = useQuery(applicationsQuery) // names for the summary and conflicts
  const [pending, setPending] = useState<Pending[]>(loadPending)
  const [ticked, setTicked] = useState<string[]>([])
  const [text, setText] = useState('')
  const [confirming, setConfirming] = useState(false)
  const [result, setResult] = useState<ApplyResult | null>(null)

  useEffect(() => savePending(pending), [pending])
  useEffect(() => {
    if (!pending.length) return
    const warn = (e: BeforeUnloadEvent) => e.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [pending.length])

  const leadIds = queue.data?.lead_ids ?? []
  const current = currentLead(leadIds, pending)
  const next = current === undefined ? undefined : currentLead(leadIds, [...pending, { id: current, decision: 'skip', ticked: [], text: '' }])
  useEffect(() => {
    if (next !== undefined) qc.prefetchQuery(applicationQuery(next))
  }, [qc, next])

  const apply = useMutation({
    mutationFn: () => postReview(toBatch(pending)),
    onSuccess: (data) => {
      setResult(data)
      setPending([])
      setConfirming(false)
      qc.invalidateQueries()
    },
  })

  const decide = (decision: Choice) => {
    if (current === undefined || confirming) return
    const skip = decision === 'skip' // a skip means "not now" and never carries a reason
    setPending([...pending, { id: current, decision, ticked: skip ? [] : ticked, text: skip ? '' : text }])
    setTicked([])
    setText('')
    window.scrollTo(0, 0)
  }
  const undo = () => {
    const last = pending.at(-1)
    if (!last || apply.isPending) return
    setPending(pending.slice(0, -1))
    setTicked(last.ticked)
    setText(last.text)
    setConfirming(false)
  }
  // Only the textarea swallows keys, so Y/N/S/U still work after ticking a checkbox.
  useHotkeys([['y', () => decide('apply')], ['n', () => decide('dismiss')], ['s', () => decide('skip')], ['u', undo]], ['TEXTAREA'])

  if (queue.isPending) return <Loader />
  if (queue.error) return <Alert color="red">{queue.error.message}</Alert>

  const reasons = queue.data.reasons
  const decided = new Set(pending.map((p) => p.id))
  const done = leadIds.filter((id) => decided.has(id)).length
  const name = (id: number) => {
    const a = apps.data?.find((x) => x.id === id)
    return a ? `${a.company} - ${a.role}` : `#${id}`
  }
  const count = (d: Choice) => pending.filter((p) => p.decision === d).length
  const writes = toBatch(pending).length // skips are pending only to keep the position

  return (
    <Stack>
      <Group justify="space-between">
        <Text fw={500}>{current !== undefined ? `Lead ${done + 1} of ${leadIds.length}` : 'No open leads left'}</Text>
        <Group>
          <Button variant="default" onClick={undo} disabled={!pending.length}>
            Undo <Kbd ml="xs">U</Kbd>
          </Button>
          <Button onClick={() => setConfirming(true)} disabled={!writes || confirming}>
            Write {writes} decisions
          </Button>
        </Group>
      </Group>

      {result && (
        <Alert color="green" withCloseButton onClose={() => setResult(null)}>
          Written: {result.applied.to_apply} to apply, {result.applied.dismissed} dismissed, {result.applied.notes} reasons.
          {result.conflicts.length > 0 && (
            <> Not written, changed elsewhere since: {result.conflicts.map(name).join('; ')}.</>
          )}
        </Alert>
      )}
      {apply.error && (
        <Alert color="red">{apply.error.message} Your decisions are still pending.</Alert>
      )}

      {confirming || (current === undefined && writes > 0) ? (
        <Paper withBorder p="md">
          <Title order={4}>Write these decisions?</Title>
          <Text my="sm">
            {count('apply')} apply, {count('dismiss')} dismiss, {count('skip')} skip
          </Text>
          {count('apply') > 0 && (
            <List mb="sm">
              {pending.filter((p) => p.decision === 'apply').map((p) => <List.Item key={p.id}>{name(p.id)}</List.Item>)}
            </List>
          )}
          <Group>
            <Button onClick={() => apply.mutate()} loading={apply.isPending}>Write to tracking DB</Button>
            {current !== undefined && (
              <Button variant="default" onClick={() => setConfirming(false)}>Keep reviewing</Button>
            )}
          </Group>
        </Paper>
      ) : current === undefined && pending.length > 0 ? (
        // Only skips left: nothing to write, so offer to clear them or they stay hidden next time too.
        <Group>
          <Text>All leads decided, {count('skip')} skipped.</Text>
          <Button variant="default" onClick={() => setPending([])}>Review skipped leads again</Button>
        </Group>
      ) : current === undefined ? (
        <Text>No leads to review.</Text>
      ) : (
        <>
          <Paper withBorder p="sm" style={{ position: 'sticky', top: 0, zIndex: 2 }}>
            <Stack gap="xs">
              {reasons.length > 0 && (
                <Checkbox.Group value={ticked} onChange={(v) => setTicked(reasons.filter((r) => v.includes(r)))}>
                  <Group gap="md">
                    {reasons.map((r) => <Checkbox key={r} value={r} label={r} />)}
                  </Group>
                </Checkbox.Group>
              )}
              <Textarea
                placeholder="Reason (optional)"
                aria-label="Reason"
                autosize
                minRows={1}
                value={text}
                onChange={(e) => setText(e.currentTarget.value)}
              />
              <Group>
                {CHOICES.map((c) => (
                  <Button key={c.decision} color={c.color} onClick={() => decide(c.decision)}>
                    {c.label} <Kbd ml="xs">{c.key}</Kbd>
                  </Button>
                ))}
              </Group>
            </Stack>
          </Paper>
          <LeadDetail key={current} id={current} />
        </>
      )}
    </Stack>
  )
}
