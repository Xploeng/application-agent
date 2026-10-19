import { Alert, Anchor, Group, Loader, Stack, Text, Title, Typography } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { applicationQuery } from '../api'
import StatusBadge from './StatusBadge'

export default function LeadDetail({ id }: { id: number }) {
  const { data: app, error, isPending } = useQuery(applicationQuery(id))
  if (isPending) return <Loader />
  if (error) return <Alert color="red">{error.message}</Alert>

  const meta = [app.location, app.source, app.posting_captured_at && `found ${app.posting_captured_at.slice(0, 10)}`]
  return (
    <Stack gap="xs">
      <Group gap="sm">
        <Title order={2}>{app.company} - {app.role}</Title>
        <StatusBadge status={app.status} />
      </Group>
      <Text c="dimmed">{meta.filter(Boolean).join(' - ')}</Text>
      {app.url && (
        <Anchor href={app.url} target="_blank" rel="noreferrer" style={{ overflowWrap: 'anywhere' }}>
          {app.url}
        </Anchor>
      )}
      {app.evaluator_reason && <Text><b>Why kept:</b> {app.evaluator_reason}</Text>}
      {app.posting_text ? (
        // react-markdown ignores raw HTML by default, so scraped text cannot inject markup
        <Typography mt="md">
          <Markdown remarkPlugins={[remarkGfm]}>{app.posting_text}</Markdown>
        </Typography>
      ) : (
        <Alert mt="md">No posting text stored. See the link.</Alert>
      )}
    </Stack>
  )
}
