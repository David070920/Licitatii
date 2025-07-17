import React from 'react'
import { RiskDashboard } from '../components/charts/RiskVisualization'

export const RiskAnalysis: React.FC = () => {
  // Mock data for demonstration
  const mockRiskData = {
    overall_score: 45.2,
    risk_level: 'medium',
    trend: 'down' as const,
    indicators: {
      single_bidder: 25,
      price_anomaly: 18,
      geographic_risk: 12,
      frequency_risk: 8
    },
    distribution: [
      { risk_level: 'low', count: 120, percentage: 60 },
      { risk_level: 'medium', count: 50, percentage: 25 },
      { risk_level: 'high', count: 25, percentage: 12.5 },
      { risk_level: 'critical', count: 5, percentage: 2.5 }
    ],
    time_series: [
      { period: 'Ian', value: 52.3 },
      { period: 'Feb', value: 48.7 },
      { period: 'Mar', value: 45.2 },
      { period: 'Apr', value: 42.1 },
      { period: 'Mai', value: 39.8 }
    ],
    high_risk_tenders: []
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Analiza Riscurilor
          </h1>
          <p className="text-gray-600">
            Monitorizarea și analiza riscurilor de corupție în achizițiile publice
          </p>
        </div>
        
        <RiskDashboard
          data={mockRiskData}
          loading={false}
          onRefresh={() => {}}
          onExport={() => {}}
        />
      </div>
    </div>
  )
}