import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useQuery } from 'react-query'
import { apiService } from '../../services/api'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const location = useLocation()
  
  const { data: user, isLoading, error } = useQuery(
    'current-user',
    () => apiService.getCurrentUser(),
    {
      retry: false,
      staleTime: 10 * 60 * 1000, // 10 minutes
    }
  )

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Se verifică autentificarea...</p>
        </div>
      </div>
    )
  }

  if (error || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}