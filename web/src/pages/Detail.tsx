import { Anchor } from '@mantine/core'
import { Link, useParams } from 'react-router'

import LeadDetail from '../components/LeadDetail'

export default function Detail() {
  const id = Number(useParams().id)
  return (
    <>
      <Anchor component={Link} to="/" mb="md" display="block">&larr; All applications</Anchor>
      <LeadDetail id={id} />
    </>
  )
}
