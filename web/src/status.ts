import type { Status } from './api'

// Filled Mantine colours: all readable in light and dark mode (no near-black 'dark').
export const STATUS_COLOR: Record<Status, string> = {
  lead: 'cyan',
  to_apply: 'blue',
  applied: 'indigo',
  interview: 'orange',
  offer: 'green',
  rejected: 'red',
  dismissed: 'gray',
  withdrawn: 'grape',
  ghosted: 'yellow',
}

export const statusLabel = (status: Status) => status.replace('_', ' ')
