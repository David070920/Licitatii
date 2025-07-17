import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import { Layout } from './components/layout/Layout'
import { HomePage } from './pages/HomePage'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { RiskAnalysis } from './pages/RiskAnalysis'
import { GeographicAnalysis } from './pages/GeographicAnalysis'
import { TenderDetails } from './pages/TenderDetails'
import { NotFound } from './pages/NotFound'
import { BusinessDashboard } from './components/dashboards/BusinessDashboard'
import { TransparencyDashboard } from './components/dashboards/TransparencyDashboard'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { ErrorFallback } from './components/common/ErrorFallback'
import { ErrorBoundary } from 'react-error-boundary'

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      retry: 3,
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary FallbackComponent={ErrorFallback}>
        <Router>
          <div className="App">
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/transparency" element={<TransparencyDashboard />} />
              
              {/* Protected routes with layout */}
              <Route path="/" element={
                <Layout>
                  <Routes>
                    <Route index element={<HomePage />} />
                    <Route path="/business" element={
                      <ProtectedRoute>
                        <BusinessDashboard />
                      </ProtectedRoute>
                    } />
                    <Route path="/risk-analysis" element={
                      <ProtectedRoute>
                        <RiskAnalysis />
                      </ProtectedRoute>
                    } />
                    <Route path="/geographic" element={
                      <ProtectedRoute>
                        <GeographicAnalysis />
                      </ProtectedRoute>
                    } />
                    <Route path="/tender/:id" element={
                      <ProtectedRoute>
                        <TenderDetails />
                      </ProtectedRoute>
                    } />
                    <Route path="*" element={<NotFound />} />
                  </Routes>
                </Layout>
              } />
              
              {/* Catch all route */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </div>
        </Router>
      </ErrorBoundary>
    </QueryClientProvider>
  )
}

export default App