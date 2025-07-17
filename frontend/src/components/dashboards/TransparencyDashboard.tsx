import React, { useState } from 'react'
import { useQuery } from 'react-query'
import { motion } from 'framer-motion'
import { 
  Eye, 
  Shield, 
  TrendingUp, 
  MapPin, 
  Building, 
  Users, 
  FileText, 
  AlertTriangle,
  Search,
  Download,
  Calendar,
  DollarSign
} from 'lucide-react'
import { apiService } from '../../services/api'
import { TenderVolumeChart } from '../charts/BarChart'
import { RiskTrendChart } from '../charts/LineChart'
import { CountyDistributionChart } from '../charts/PieChart'
import { RiskGeographicMap, ValueGeographicMap } from '../maps/RomanianMap'
import { RiskScore } from '../charts/RiskVisualization'

interface PublicMetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
  color: string
  trend?: {
    value: number
    direction: 'up' | 'down' | 'stable'
  }
}

const PublicMetricCard: React.FC<PublicMetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  color,
  trend
}) => {
  const formatValue = (val: string | number) => {
    if (typeof val === 'number') {
      if (val >= 1000000000) return `${(val / 1000000000).toFixed(1)}B`
      if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`
      if (val >= 1000) return `${(val / 1000).toFixed(1)}K`
      return val.toLocaleString('ro-RO')
    }
    return val
  }

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="bg-white rounded-lg p-6 shadow-lg border border-gray-200"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>
          {subtitle && (
            <p className="text-sm text-gray-600 mb-3">{subtitle}</p>
          )}
          <div className="text-3xl font-bold text-gray-900">
            {formatValue(value)}
          </div>
          {trend && (
            <div className="flex items-center mt-2 text-sm">
              {trend.direction === 'up' ? (
                <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
              ) : trend.direction === 'down' ? (
                <TrendingUp className="w-4 h-4 text-red-500 mr-1 transform rotate-180" />
              ) : null}
              <span className={`${
                trend.direction === 'up' ? 'text-green-600' : 
                trend.direction === 'down' ? 'text-red-600' : 
                'text-gray-600'
              }`}>
                {trend.value > 0 ? '+' : ''}{trend.value}%
              </span>
              <span className="text-gray-500 ml-1">vs luna trecută</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          {icon}
        </div>
      </div>
    </motion.div>
  )
}

interface TenderSearchProps {
  onSearch: (query: string) => void
  loading?: boolean
}

const TenderSearch: React.FC<TenderSearchProps> = ({ onSearch, loading = false }) => {
  const [searchQuery, setSearchQuery] = useState('')

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    onSearch(searchQuery)
  }

  return (
    <div className="bg-white rounded-lg p-6 shadow-lg border border-gray-200 mb-8">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Căutare Licitații
      </h3>
      <form onSubmit={handleSearch} className="flex gap-4">
        <div className="flex-1">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Caută licitații după titlu, autoritate sau CPV..."
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
        </div>
        <button
          type="submit"
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          disabled={loading}
        >
          <Search className="w-5 h-5" />
          Caută
        </button>
      </form>
    </div>
  )
}

interface RecentTendersProps {
  tenders: any[]
  loading?: boolean
}

const RecentTenders: React.FC<RecentTendersProps> = ({ tenders, loading = false }) => {
  const getRiskColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'low': return 'bg-green-100 text-green-800'
      case 'medium': return 'bg-yellow-100 text-yellow-800'
      case 'high': return 'bg-red-100 text-red-800'
      case 'critical': return 'bg-red-200 text-red-900'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ro-RO', {
      style: 'currency',
      currency: 'RON',
      minimumFractionDigits: 0
    }).format(value)
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-lg border border-gray-200">
        <div className="p-6">
          <div className="animate-pulse">
            <div className="h-6 bg-gray-300 rounded w-1/4 mb-4"></div>
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-16 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-200">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Licitații Recente
          </h3>
          <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
            Vezi toate
          </button>
        </div>
      </div>
      <div className="divide-y divide-gray-200">
        {tenders.map((tender, index) => (
          <div key={index} className="p-6 hover:bg-gray-50 transition-colors">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className="text-md font-medium text-gray-900 mb-2">
                  {tender.title}
                </h4>
                <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
                  <span className="flex items-center gap-1">
                    <Building className="w-4 h-4" />
                    {tender.authority_name}
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="w-4 h-4" />
                    {tender.county}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    {new Date(tender.publication_date).toLocaleDateString('ro-RO')}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-lg font-semibold text-gray-900">
                    {formatCurrency(tender.estimated_value)}
                  </span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskColor(tender.risk_level)}`}>
                    Risc {tender.risk_level === 'low' ? 'Scăzut' : tender.risk_level === 'medium' ? 'Mediu' : tender.risk_level === 'high' ? 'Ridicat' : 'Critic'}
                  </span>
                </div>
              </div>
              <div className="ml-4">
                <RiskScore
                  score={tender.risk_score || 0}
                  level={tender.risk_level || 'low'}
                  size="small"
                  showLabel={false}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export const TransparencyDashboard: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCounty, setSelectedCounty] = useState<string | null>(null)

  // Fetch public metrics
  const { data: metrics, isLoading: metricsLoading } = useQuery(
    ['transparency-metrics'],
    () => apiService.getDashboardMetrics(),
    {
      refetchInterval: 10 * 60 * 1000, // Refetch every 10 minutes
      staleTime: 5 * 60 * 1000, // Data is fresh for 5 minutes
    }
  )

  // Fetch recent tenders
  const { data: recentTenders, isLoading: tendersLoading } = useQuery(
    ['recent-tenders', searchQuery],
    () => apiService.getTenders({ 
      limit: 10, 
      search: searchQuery,
      county: selectedCounty || undefined
    }),
    {
      enabled: true,
      staleTime: 2 * 60 * 1000,
    }
  )

  // Fetch visualization data
  const { data: geographic, isLoading: geoLoading } = useQuery(
    ['transparency-geographic'],
    () => apiService.getGeographicData(),
    { staleTime: 10 * 60 * 1000 }
  )

  const { data: riskTrend, isLoading: riskTrendLoading } = useQuery(
    ['transparency-risk-trend'],
    () => apiService.getTimeSeriesData({ metric: 'risk_score', period: 'monthly' }),
    { staleTime: 10 * 60 * 1000 }
  )

  const { data: tenderVolume, isLoading: volumeLoading } = useQuery(
    ['transparency-tender-volume'],
    () => apiService.getTenderVolumeData({ period: 'monthly' }),
    { staleTime: 10 * 60 * 1000 }
  )

  const handleSearch = (query: string) => {
    setSearchQuery(query)
  }

  const handleCountyClick = (county: string) => {
    setSelectedCounty(county)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 text-white">
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="text-center">
            <h1 className="text-4xl font-bold mb-4">
              Platforma de Transparență a Achizițiilor Publice
            </h1>
            <p className="text-xl text-blue-100 mb-8 max-w-3xl mx-auto">
              Monitorizează în timp real achizițiile publice din România. 
              Acces liber la date, analize și indicatori de transparență.
            </p>
            <div className="flex justify-center gap-4">
              <button className="bg-white text-blue-600 px-6 py-3 rounded-lg font-medium hover:bg-gray-100">
                <Download className="w-5 h-5 inline mr-2" />
                Descarcă Date
              </button>
              <button className="border border-white text-white px-6 py-3 rounded-lg font-medium hover:bg-white hover:text-blue-600">
                <Eye className="w-5 h-5 inline mr-2" />
                Explorează
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Search Section */}
        <TenderSearch onSearch={handleSearch} loading={tendersLoading} />

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <PublicMetricCard
            title="Licitații Active"
            value={metrics?.active_tenders || 0}
            subtitle="În curs de desfășurare"
            icon={<FileText className="w-6 h-6 text-white" />}
            color="bg-blue-500"
            trend={{ value: 5.2, direction: 'up' }}
          />
          <PublicMetricCard
            title="Valoare Totală"
            value={`${((metrics?.total_value || 0) / 1000000000).toFixed(1)}B RON`}
            subtitle="Toate licitațiile"
            icon={<DollarSign className="w-6 h-6 text-white" />}
            color="bg-green-500"
            trend={{ value: 12.8, direction: 'up' }}
          />
          <PublicMetricCard
            title="Autorități"
            value={metrics?.unique_authorities || 0}
            subtitle="Instituții publice"
            icon={<Building className="w-6 h-6 text-white" />}
            color="bg-purple-500"
            trend={{ value: 0.8, direction: 'stable' }}
          />
          <PublicMetricCard
            title="Transparență"
            value={`${(100 - (metrics?.average_risk_score || 0)).toFixed(0)}%`}
            subtitle="Scor mediu"
            icon={<Shield className="w-6 h-6 text-white" />}
            color="bg-indigo-500"
            trend={{ value: 3.2, direction: 'up' }}
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          {/* Recent Tenders */}
          <div className="lg:col-span-2">
            <RecentTenders 
              tenders={recentTenders?.results || []} 
              loading={tendersLoading} 
            />
          </div>

          {/* County Distribution */}
          <div>
            <CountyDistributionChart
              data={geographic || []}
              loading={geoLoading}
              onExport={() => {}}
            />
          </div>
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <TenderVolumeChart
            data={tenderVolume || []}
            loading={volumeLoading}
            onExport={() => {}}
          />
          
          <RiskTrendChart
            data={riskTrend || []}
            loading={riskTrendLoading}
            onExport={() => {}}
          />
        </div>

        {/* Maps Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <ValueGeographicMap
            data={geographic || []}
            loading={geoLoading}
            onCountyClick={handleCountyClick}
            onExport={() => {}}
          />
          
          <RiskGeographicMap
            data={geographic || []}
            loading={geoLoading}
            onCountyClick={handleCountyClick}
            onExport={() => {}}
          />
        </div>

        {/* Footer Info */}
        <div className="bg-white rounded-lg p-6 shadow-lg border border-gray-200">
          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Despre Platforma de Transparență
            </h3>
            <p className="text-gray-600 max-w-3xl mx-auto">
              Această platformă oferă acces liber la datele privind achizițiile publice din România, 
              promovând transparența și responsabilitatea în cheltuirea banilor publici. 
              Datele sunt actualizate zilnic și procesate prin algoritmi avansați de detectare a riscurilor.
            </p>
            <div className="mt-4 flex justify-center gap-6 text-sm text-gray-500">
              <span>Ultima actualizare: {new Date().toLocaleString('ro-RO')}</span>
              <span>•</span>
              <span>Surse: SICAP, ANRMAP, TED</span>
              <span>•</span>
              <span>Acces gratuit</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}