import '@mantine/core/styles.css'

import { Anchor, Container, Group, MantineProvider, Title } from '@mantine/core'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router'

import Applications from './pages/Applications'
import Detail from './pages/Detail'
import Review from './pages/Review'

// No refetch on focus: the review queue must not shift under the user mid-review.
const queryClient = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false } } })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MantineProvider defaultColorScheme="auto">
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Container size="lg" py="md">
            <Group mb="lg" gap="lg">
              <Title order={3}>Applications</Title>
              <Anchor component={NavLink} to="/" end>Table</Anchor>
              <Anchor component={NavLink} to="/review">Review leads</Anchor>
            </Group>
            <Routes>
              <Route path="/" element={<Applications />} />
              <Route path="/app/:id" element={<Detail />} />
              <Route path="/review" element={<Review />} />
            </Routes>
          </Container>
        </BrowserRouter>
      </QueryClientProvider>
    </MantineProvider>
  </StrictMode>,
)
