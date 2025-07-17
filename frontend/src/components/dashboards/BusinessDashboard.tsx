import React, { useState, useEffect } from 'react'
import { useQuery } from 'react-query'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, DollarSign, FileText, Users, AlertCircle, Calendar, Filter } from 'lucide-react'
import { apiService } from '../../services/api'
import { TenderVolumeChart, GeographicDistributionChart, CompanyPerformanceChart } from '../charts/BarChart'
import { TenderVolumeTimeSeriesChart, MultiMetricChart } from '../charts/LineChart'
import { RiskDistributionPieChart, CPVDistributionChart } from '../charts/PieChart'
import { TenderGeographicMap } from '../maps/RomanianMap'
import { RiskDashboard } from '../charts/RiskVisualization'

interface MetricCardProps {
  title: string
  value: string | number
  change?: number
  trend?: 'up' | 'down' | 'stable'
  icon: React.ReactNode
  color: string
  loading?: boolean
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  change,
  trend,
  icon,
  color,
  loading = false
}) => {
  const getTrendIcon = () => {
    if (trend === 'up') return <TrendingUp className="w-4 h-4 text-green-500" />
    if (trend === 'down') return <TrendingDown className="w-4 h-4 text-red-500" />
    return null
  }

  const formatValue = (val: string | number) => {
    if (typeof val === 'number') {
      if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`
      if (val >= 1000) return `${(val / 1000).toFixed(1)}K`
      return val.toLocaleString('ro-RO')
    }
    return val
  }

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="bg-white rounded-lg p-6 shadow-md border border-gray-200"
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600 mb-1">{title}</p>
          <div className="flex items-center gap-2">
            {loading ? (
              <div className="h-8 w-24 bg-gray-200 animate-pulse rounded" />
            ) : (
              <h3 className="text-2xl font-bold text-gray-900">
                {formatValue(value)}
              </h3>
            )}
            {change !== undefined && (
              <div className="flex items-center gap-1">
                {getTrendIcon()}
                <span className={`text-sm ${trend === 'up' ? 'text-green-500' : trend === 'down' ? 'text-red-500' : 'text-gray-500'}`}>
                  {change > 0 ? '+' : ''}{change.toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          {icon}
        </div>
      </div>
    </motion.div>
  )
}

interface FilterControlsProps {
  onFilterChange: (filters: any) => void
  loading?: boolean
}

const FilterControls: React.FC<FilterControlsProps> = ({ onFilterChange, loading = false }) => {
  const [filters, setFilters] = useState({
    dateRange: '30d',
    county: '',
    cpvCode: '',
    riskLevel: '',
    minValue: '',
    maxValue: ''
  })

  const handleFilterChange = (key: string, value: string) => {
    const newFilters = { ...filters, [key]: value }
    setFilters(newFilters)
    onFilterChange(newFilters)
  }

  return (
    <div className="bg-white rounded-lg p-4 shadow-md border border-gray-200 mb-6">
      <div className="flex items-center gap-2 mb-4">
        <Filter className="w-5 h-5 text-gray-600" />
        <h3 className="text-lg font-semibold text-gray-900">Filtre</h3>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Perioada
          </label>
          <select
            value={filters.dateRange}
            onChange={(e) => handleFilterChange('dateRange', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          >
            <option value="7d">Ultima săptămână</option>
            <option value="30d">Ultima lună</option>
            <option value="90d">Ultimele 3 luni</option>
            <option value="1y">Ultimul an</option>
            <option value="all">Toate</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Județ
          </label>
          <select
            value={filters.county}
            onChange={(e) => handleFilterChange('county', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          >
            <option value="">Toate județele</option>
            <option value="Bucuresti">București</option>
            <option value="Cluj">Cluj</option>
            <option value="Timis">Timiș</option>
            <option value="Constanta">Constanța</option>
            <option value="Iasi">Iași</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Nivel risc
          </label>
          <select
            value={filters.riskLevel}
            onChange={(e) => handleFilterChange('riskLevel', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          >
            <option value="">Toate nivelele</option>
            <option value="low">Risc scăzut</option>
            <option value="medium">Risc mediu</option>
            <option value="high">Risc ridicat</option>
            <option value="critical">Risc critic</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Valoare min (RON)
          </label>
          <input
            type="number"
            value={filters.minValue}
            onChange={(e) => handleFilterChange('minValue', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="0"
            disabled={loading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Valoare max (RON)
          </label>
          <input
            type="number"
            value={filters.maxValue}
            onChange={(e) => handleFilterChange('maxValue', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="∞"
            disabled={loading}
          />
        </div>

        <div className="flex items-end">
          <button
            onClick={() => {
              setFilters({
                dateRange: '30d',
                county: '',
                cpvCode: '',
                riskLevel: '',
                minValue: '',
                maxValue: ''
              })
              onFilterChange({})
            }}
            className="w-full px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
            disabled={loading}
          >
            Resetează
          </button>
        </div>
      </div>
    </div>
  )
}

export const BusinessDashboard: React.FC = () => {
  const [filters, setFilters] = useState({})
  const [refreshKey, setRefreshKey] = useState(0)

  // Fetch dashboard metrics
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useQuery(
    ['dashboard-metrics', filters, refreshKey],
    () => apiService.getDashboardMetrics(filters),
    {
      refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
      staleTime: 2 * 60 * 1000, // Data is fresh for 2 minutes
    }
  )

  // Fetch chart data
  const { data: tenderVolume, isLoading: volumeLoading } = useQuery(
    ['tender-volume', filters, refreshKey],
    () => apiService.getTenderVolumeData({ period: 'monthly', ...filters }),
    { enabled: !!metrics }
  )

  const { data: geographic, isLoading: geoLoading } = useQuery(
    ['geographic-data', filters, refreshKey],
    () => apiService.getGeographicData(filters),
    { enabled: !!metrics }
  )

  const { data: companyPerformance, isLoading: companyLoading } = useQuery(
    ['company-performance', filters, refreshKey],
    () => apiService.getCompanyPerformanceData({ limit: 10, ...filters }),
    { enabled: !!metrics }
  )

  const { data: riskDistribution, isLoading: riskLoading } = useQuery(
    ['risk-distribution', filters, refreshKey],
    () => apiService.getRiskDistributionData(filters),
    { enabled: !!metrics }
  )

  const { data: cpvAnalysis, isLoading: cpvLoading } = useQuery(
    ['cpv-analysis', filters, refreshKey],
    () => apiService.getCPVAnalysisData({ limit: 15, ...filters }),
    { enabled: !!metrics }
  )

  const { data: timeSeries, isLoading: timeSeriesLoading } = useQuery(
    ['time-series', filters, refreshKey],
    () => apiService.getTimeSeriesData({ metric: 'tender_count', period: 'monthly', ...filters }),
    { enabled: !!metrics }
  )

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1)
  }

  const handleExport = async (chartType: string) => {
    try {
      const data = await apiService.exportVisualizationData({
        chart_type: chartType,
        format: 'csv',
        ...filters
      })
      
      // Create download link
      const blob = new Blob([data.csv_data], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${chartType}-${new Date().toISOString().split('T')[0]}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Business Intelligence Dashboard
          </h1>
          <p className="text-gray-600">
            Analiză comprehensivă a datelor de achiziții publice pentru optimizarea strategiei de business
          </p>
        </div>

        {/* Filters */}
        <FilterControls 
          onFilterChange={setFilters} 
          loading={metricsLoading} 
        />

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Total Licitații"
            value={metrics?.total_tenders || 0}
            change={12.5}
            trend="up"
            icon={<FileText className="w-6 h-6 text-white" />}
            color="bg-blue-500"
            loading={metricsLoading}
          />
          <MetricCard
            title="Valoare Totală"
            value={`${((metrics?.total_value || 0) / 1000000).toFixed(1)}M RON`}
            change={8.3}
            trend="up"
            icon={<DollarSign className="w-6 h-6 text-white" />}
            color="bg-green-500"
            loading={metricsLoading}
          />
          <MetricCard
            title="Companii Active"
            value={metrics?.unique_companies || 0}
            change={-2.1}
            trend="down"
            icon={<Users className="w-6 h-6 text-white" />}
            color="bg-purple-500"
            loading={metricsLoading}
          />
          <MetricCard
            title="Risc Mediu"
            value={`${(metrics?.average_risk_score || 0).toFixed(1)}%`}
            change={-5.8}
            trend="down"
            icon={<AlertCircle className="w-6 h-6 text-white" />}
            color="bg-orange-500"
            loading={metricsLoading}
          />
        </div>

        {/* Main Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Tender Volume Chart */}
          <TenderVolumeChart
            data={tenderVolume || []}
            loading={volumeLoading}
            onRefresh={handleRefresh}
            onExport={() => handleExport('tender-volume')}
          />

          {/* Geographic Distribution */}
          <GeographicDistributionChart
            data={geographic || []}
            loading={geoLoading}
            onRefresh={handleRefresh}
            onExport={() => handleExport('geographic')}
          />

          {/* Company Performance */}
          <CompanyPerformanceChart
            data={companyPerformance || []}
            loading={companyLoading}
            onRefresh={handleRefresh}
            onExport={() => handleExport('company-performance')}
          />

          {/* Risk Distribution */}
          <RiskDistributionPieChart
            data={riskDistribution || []}
            loading={riskLoading}
            onRefresh={handleRefresh}
            onExport={() => handleExport('risk-distribution')}
          />
        </div>

        {/* Secondary Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* CPV Analysis */}
          <CPVDistributionChart
            data={cpvAnalysis || []}
            loading={cpvLoading}
            onRefresh={handleRefresh}
            onExport={() => handleExport('cpv-analysis')}
          />

          {/* Time Series */}
          <TenderVolumeTimeSeriesChart
            data={timeSeries || []}
            loading={timeSeriesLoading}
            onRefresh={handleRefresh}
            onExport={() => handleExport('time-series')}
          />
        </div>

        {/* Geographic Map */}
        <div className="mb-8">
          <TenderGeographicMap
            data={geographic || []}
            loading={geoLoading}
            onRefresh={handleRefresh}
            onExport={() => handleExport('geographic-map')}
            onCountyClick={(county) => {
              setFilters({ ...filters, county })
            }}
          />
        </div>

        {/* Risk Analysis Section */}
        <div className="mb-8">
          <RiskDashboard
            data={{
              overall_score: metrics?.average_risk_score || 0,
              risk_level: metrics?.average_risk_score > 70 ? 'high' : metrics?.average_risk_score > 40 ? 'medium' : 'low',
              trend: 'down',
              indicators: {
                single_bidder: 25,
                price_anomaly: 18,
                geographic_risk: 12,
                frequency_risk: 8
              },
              distribution: riskDistribution || [],
              time_series: timeSeries || [],
              high_risk_tenders: []
            }}
            loading={metricsLoading}
            onRefresh={handleRefresh}
            onExport={() => handleExport('risk-dashboard')}
          />
        </div>

        {/* Footer */}
        <div className="text-center text-gray-500 text-sm mt-8">
          <p>
            Ultima actualizare: {new Date().toLocaleString('ro-RO')} | 
            Datele sunt actualizate în timp real
          </p>
        </div>
      </div>
    </div>
  )
}