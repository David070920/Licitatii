import React from 'react'
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { BaseChart } from './BaseChart'

interface BarChartProps {
  data: any[]
  title: string
  subtitle?: string
  xAxisKey: string
  yAxisKey: string
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
  className?: string
  height?: number
  colors?: string[]
  showLegend?: boolean
  formatYAxis?: (value: any) => string
  formatTooltip?: (value: any, name: string) => [string, string]
}

const DEFAULT_COLORS = [
  '#3B82F6',
  '#10B981',
  '#F59E0B',
  '#EF4444',
  '#8B5CF6',
  '#06B6D4',
  '#84CC16',
  '#F97316',
]

export const BarChart: React.FC<BarChartProps> = ({
  data,
  title,
  subtitle,
  xAxisKey,
  yAxisKey,
  loading = false,
  error,
  onRefresh,
  onExport,
  className = '',
  height = 400,
  colors = DEFAULT_COLORS,
  showLegend = true,
  formatYAxis,
  formatTooltip,
}) => {
  const formatValue = (value: any) => {
    if (formatYAxis) {
      return formatYAxis(value)
    }
    
    if (typeof value === 'number') {
      if (value >= 1000000) {
        return `${(value / 1000000).toFixed(1)}M`
      } else if (value >= 1000) {
        return `${(value / 1000).toFixed(1)}K`
      }
      return value.toLocaleString('ro-RO')
    }
    
    return value
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-medium text-gray-900 mb-2">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {formatTooltip ? (
                formatTooltip(entry.value, entry.name)[0]
              ) : (
                `${entry.name}: ${formatValue(entry.value)}`
              )}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <BaseChart
      title={title}
      subtitle={subtitle}
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      className={className}
      height={height}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RechartsBarChart
          data={data}
          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey={xAxisKey}
            tick={{ fontSize: 12, fill: '#6B7280' }}
            axisLine={{ stroke: '#D1D5DB' }}
            tickLine={{ stroke: '#D1D5DB' }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#6B7280' }}
            axisLine={{ stroke: '#D1D5DB' }}
            tickLine={{ stroke: '#D1D5DB' }}
            tickFormatter={formatValue}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ fill: 'rgba(59, 130, 246, 0.1)' }}
          />
          {showLegend && (
            <Legend
              wrapperStyle={{ paddingTop: '20px' }}
              iconType="rect"
            />
          )}
          <Bar
            dataKey={yAxisKey}
            fill={colors[0]}
            radius={[4, 4, 0, 0]}
            className="transition-all duration-200"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Bar>
        </RechartsBarChart>
      </ResponsiveContainer>
    </BaseChart>
  )
}

// Specialized bar chart components
export const TenderVolumeChart: React.FC<{
  data: any[]
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
}> = ({ data, loading, error, onRefresh, onExport }) => {
  return (
    <BarChart
      data={data}
      title="Volumul Licitațiilor"
      subtitle="Numărul și valoarea licitațiilor în timp"
      xAxisKey="date"
      yAxisKey="count"
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      formatYAxis={(value) => value.toLocaleString('ro-RO')}
      formatTooltip={(value, name) => [
        `${value.toLocaleString('ro-RO')} ${name === 'count' ? 'licitații' : 'RON'}`,
        name === 'count' ? 'Numărul licitațiilor' : 'Valoarea totală'
      ]}
    />
  )
}

export const GeographicDistributionChart: React.FC<{
  data: any[]
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
}> = ({ data, loading, error, onRefresh, onExport }) => {
  return (
    <BarChart
      data={data}
      title="Distribuția Geografică"
      subtitle="Licitații pe județe"
      xAxisKey="county"
      yAxisKey="count"
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      height={500}
      colors={['#002B7F', '#FCD116', '#CE1126']}
      formatYAxis={(value) => value.toLocaleString('ro-RO')}
    />
  )
}

export const CompanyPerformanceChart: React.FC<{
  data: any[]
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
}> = ({ data, loading, error, onRefresh, onExport }) => {
  return (
    <BarChart
      data={data.slice(0, 15)} // Show top 15 companies
      title="Performanța Companiilor"
      subtitle="Top 15 companii după rata de câștig"
      xAxisKey="company_name"
      yAxisKey="win_rate"
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      height={500}
      colors={['#10B981']}
      formatYAxis={(value) => `${value}%`}
      formatTooltip={(value, name) => [
        `${value}%`,
        'Rata de câștig'
      ]}
    />
  )
}