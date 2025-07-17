import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { Layout } from './components/layout/Layout'
import { HomePage } from './pages/HomePage'
import { BusinessDashboard } from './pages/BusinessDashboard'
import { TransparencyDashboard } from './pages/TransparencyDashboard'
import { RiskAnalysis } from './pages/RiskAnalysis'
import { GeographicAnalysis } from './pages/GeographicAnalysis'
import { TenderDetails } from './pages/TenderDetails'
import { CompanyProfile } from './pages/CompanyProfile'
import { AuthorityProfile } from './pages/AuthorityProfile'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { NotFound } from './pages/NotFound'
import { ProtectedRoute } from './components/auth/ProtectedRoute'

function App() {
  return (
    <>
      <Helmet>
        <title>Platforma Română de Achiziții Publice</title>
        <meta name="description" content="Platformă de transparență și monitorizare a achizițiilor publice din România" />
        <meta name="keywords" content="achiziții publice, transparență, România, SICAP, licitații, contracte" />
        <meta property="og:title" content="Platforma Română de Achiziții Publice" />
        <meta property="og:description" content="Platformă de transparență și monitorizare a achizițiilor publice din România" />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
      </Helmet>
      
      <Layout>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<HomePage />} />
          <Route path="/transparency" element={<TransparencyDashboard />} />
          <Route path="/risk-analysis" element={<RiskAnalysis />} />
          <Route path="/geographic" element={<GeographicAnalysis />} />
          <Route path="/tender/:id" element={<TenderDetails />} />
          <Route path="/company/:id" element={<CompanyProfile />} />
          <Route path="/authority/:id" element={<AuthorityProfile />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          {/* Protected routes */}
          <Route path="/business" element={
            <ProtectedRoute>
              <BusinessDashboard />
            </ProtectedRoute>
          } />
          
          {/* 404 page */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Layout>
    </>
  )
}

export default App