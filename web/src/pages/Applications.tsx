import { Alert, Anchor, Chip, Group, Loader, Table, Text } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { STATUSES, applicationsQuery } from '../api'
import StatusBadge from '../components/StatusBadge'
import { STATUS_COLOR, statusLabel } from '../status'

const host = (url: string) => {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

// width 1% + nowrap: the column shrinks to its content, the rest goes to role and company
const fit = { width: '1%', whiteSpace: 'nowrap' } as const

export default function Applications() {
  const navigate = useNavigate()
  const [statuses, setStatuses] = useState<string[]>([...STATUSES]) // all shown; untick one to hide it
  const { data, error, isPending } = useQuery(applicationsQuery)
  if (isPending) return <Loader />
  if (error) return <Alert color="red">{error.message}</Alert>

  const rows = data.filter((a) => statuses.includes(a.status))
  return (
    <>
      <Group mb="md" gap="xs">
        <Chip.Group multiple value={statuses} onChange={setStatuses}>
          {STATUSES.map((s) => (
            <Chip key={s} value={s} color={STATUS_COLOR[s]} size="xs">{statusLabel(s)}</Chip>
          ))}
        </Chip.Group>
        <Text c="dimmed" size="sm" ml="sm">{rows.length} applications</Text>
      </Group>
      <Table highlightOnHover striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th style={fit}>Status</Table.Th>
            <Table.Th>Role</Table.Th>
            <Table.Th>Company</Table.Th>
            <Table.Th style={fit}>URL</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((a) => (
            <Table.Tr key={a.id} onClick={() => navigate(`/app/${a.id}`)} style={{ cursor: 'pointer' }}>
              <Table.Td style={fit}><StatusBadge status={a.status} /></Table.Td>
              <Table.Td>{a.role}</Table.Td>
              <Table.Td>{a.company}</Table.Td>
              <Table.Td style={fit}>
                {a.url && (
                  <Anchor href={a.url} target="_blank" rel="noreferrer" title={a.url} onClick={(e) => e.stopPropagation()}>
                    {host(a.url)}
                  </Anchor>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </>
  )
}
