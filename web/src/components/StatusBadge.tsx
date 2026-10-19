import { Badge } from '@mantine/core'

import type { Status } from '../api'
import { STATUS_COLOR, statusLabel } from '../status'

export default function StatusBadge({ status }: { status: Status }) {
  return (
    <Badge color={STATUS_COLOR[status]} variant="filled" autoContrast miw="max-content">
      {statusLabel(status)}
    </Badge>
  )
}
