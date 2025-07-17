import React from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, TrendingUp, TrendingDown, Shield, Eye } from 'lucide-react'
import { BaseChart } from './BaseChart'
import { PieChart, RiskDistributionPieChart } from './PieChart'
import { LineChart, RiskTrendChart } from './LineChart'
import { BarChart } from './BarChart'

interface RiskScoreProps {
  score: number
  level: string
  trend?: 'up' | 'down' | 'stable'
  size?: 'small' | 'medium' | 'large'
  showLabel?: boolean
}

export const RiskScore: React.FC<RiskScoreProps> = ({
  score,
  level,
  trend,
  size = 'medium',
  showLabel = true
}) => {
  const getRiskColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'low':
        return 'text-green-600 bg-green-100 border-green-200'
      case 'medium':
        return 'text-yellow-600 bg-yellow-100 border-yellow-200'
      case 'high':
        return 'text-red-600 bg-red-100 border-red-200'
      case 'critical':
        return 'text-red-800 bg-red-200 border-red-300'
      default:
        return 'text-gray-600 bg-gray-100 border-gray-200'
    }
  }

  const getSizeClasses = (size: string) => {
    switch (size) {
      case 'small':
        return 'w-16 h-16 text-lg'
      case 'large':
        return 'w-32 h-32 text-3xl'
      default:
        return 'w-24 h-24 text-xl'
    }
  }

  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-red-500" />
      case 'down':
        return <TrendingDown className="w-4 h-4 text-green-500" />
      default:
        return null
    }
  }

  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col items-center"
    >
      <div className={`
        ${getSizeClasses(size)}
        ${getRiskColor(level)}
        rounded-full border-2 flex items-center justify-center font-bold
        transition-all duration-300 hover:scale-105
      `}>
        {Math.round(score)}
      </div>
      
      {showLabel && (
        <div className="mt-2 text-center">
          <div className="flex items-center justify-center gap-1">
            <span className="text-sm font-medium capitalize">
              Risc {level === 'low' ? 'Scăzut' : level === 'medium' ? 'Mediu' : level === 'high' ? 'Ridicat' : 'Critic'}
            </span>
            {getTrendIcon()}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Scor: {score.toFixed(1)}
          </div>
        </div>
      )}
    </motion.div>
  )
}

interface RiskIndicatorProps {
  title: string
  value: number
  maxValue: number
  color: string
  icon: React.ReactNode
  description?: string
}

export const RiskIndicator: React.FC<RiskIndicatorProps> = ({
  title,
  value,
  maxValue,
  color,
  icon,
  description
}) => {
  const percentage = (value / maxValue) * 100

  return (
    <div className="p-4 bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={`p-2 rounded-lg ${color}`}>
            {icon}
          </div>
          <div>
            <h4 className="font-medium text-gray-900">{title}</h4>
            {description && (
              <p className="text-xs text-gray-500">{description}</p>
            )}
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900">{value}</div>
          <div className="text-xs text-gray-500">din {maxValue}</div>
        </div>
      </div>
      
      <div className="w-full bg-gray-200 rounded-full h-2">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className={`h-2 rounded-full ${color.replace('bg-', 'bg-').replace('-100', '-500')}`}
        />
      </div>
      
      <div className="mt-1 text-xs text-gray-500">
        {percentage.toFixed(1)}% din total
      </div>
    </div>
  )
}

interface RiskDashboardProps {
  data: {
    overall_score: number
    risk_level: string
    trend: 'up' | 'down' | 'stable'
    indicators: {
      single_bidder: number
      price_anomaly: number
      geographic_risk: number
      frequency_risk: number
    }
    distribution: any[]
    time_series: any[]
    high_risk_tenders: any[]
  }
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
}

export const RiskDashboard: React.FC<RiskDashboardProps> = ({
  data,
  loading = false,
  error,
  onRefresh,
  onExport
}) => {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="h-64 bg-gray-200 rounded-lg"></div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12 text-red-600">
        <AlertTriangle className="w-12 h-12 mx-auto mb-4" />
        <p>Eroare la încărcarea datelor de risc: {error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Overall Risk Score */}
      <div className="bg-white rounded-lg p-6 shadow-md border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Scorul General de Risc
          </h3>
          <Shield className="w-6 h-6 text-gray-600" />
        </div>
        
        <div className="flex items-center justify-center">
          <RiskScore
            score={data.overall_score}
            level={data.risk_level}
            trend={data.trend}
            size="large"
          />
        </div>
      </div>

      {/* Risk Indicators */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <RiskIndicator
          title="Ofertant Unic"
          value={data.indicators.single_bidder}
          maxValue={100}
          color="bg-red-100 text-red-600"
          icon={<Eye className="w-5 h-5" />}
          description="Licitații cu un singur ofertant"
        />
        
        <RiskIndicator
          title="Anomalii Preț"
          value={data.indicators.price_anomaly}
          maxValue={100}
          color="bg-orange-100 text-orange-600"
          icon={<TrendingUp className="w-5 h-5" />}
          description="Prețuri neobișnuite"
        />
        
        <RiskIndicator
          title="Risc Geografic"
          value={data.indicators.geographic_risk}
          maxValue={100}
          color="bg-yellow-100 text-yellow-600"
          icon={<AlertTriangle className="w-5 h-5" />}
          description="Concentrare geografică"
        />
        
        <RiskIndicator
          title="Risc Frecvență"
          value={data.indicators.frequency_risk}
          maxValue={100}
          color="bg-blue-100 text-blue-600"
          icon={<TrendingDown className="w-5 h-5" />}
          description="Câștigători frecvenți"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Distribution */}
        <RiskDistributionPieChart
          data={data.distribution}
          loading={loading}
          error={error}
          onRefresh={onRefresh}
          onExport={onExport}
        />

        {/* Risk Trend */}
        <RiskTrendChart
          data={data.time_series}
          loading={loading}
          error={error}
          onRefresh={onRefresh}
          onExport={onExport}
        />
      </div>

      {/* High Risk Tenders */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Licitații cu Risc Ridicat
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Ultimele licitații identificate cu risc ridicat
          </p>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Licitația
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Autoritate
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Valoare
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Scor Risc
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Factori Risc
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.high_risk_tenders.map((tender, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {tender.title?.substring(0, 50)}...
                    </div>
                    <div className="text-sm text-gray-500">
                      {tender.external_id}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {tender.authority_name}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {tender.estimated_value?.toLocaleString('ro-RO')} RON
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <RiskScore
                      score={tender.risk_score}
                      level={tender.risk_level}
                      size="small"
                      showLabel={false}
                    />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-wrap gap-1">
                      {tender.risk_factors?.map((factor: string, idx: number) => (
                        <span
                          key={idx}
                          className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800"
                        >
                          {factor}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// Heatmap for risk correlation
export const RiskHeatmap: React.FC<{
  data: any[]
  title?: string
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
}> = ({ data, title = "Harta Corelației Riscurilor", loading, error, onRefresh, onExport }) => {
  return (
    <BaseChart
      title={title}
      subtitle="Corelația între diferitele tipuri de risc"
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      height={400}
    >
      <div className="grid grid-cols-4 gap-1 h-full p-4">
        {data.map((row, rowIndex) => (
          row.map((cell: any, colIndex: number) => (
            <div
              key={`${rowIndex}-${colIndex}`}
              className={`
                flex items-center justify-center text-xs font-medium rounded
                ${cell.value > 0.7 ? 'bg-red-500 text-white' : 
                  cell.value > 0.4 ? 'bg-orange-300 text-gray-800' : 
                  cell.value > 0.1 ? 'bg-yellow-200 text-gray-800' : 
                  'bg-green-200 text-gray-800'}
              `}
              title={`${cell.x} vs ${cell.y}: ${cell.value.toFixed(2)}`}
            >
              {cell.value.toFixed(2)}
            </div>
          ))
        ))}
      </div>
    </BaseChart>
  )
}