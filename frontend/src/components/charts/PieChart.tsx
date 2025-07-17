import React from 'react'
import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts'
import { BaseChart } from './BaseChart'

interface PieChartProps {
  data: any[]
  title: string
  subtitle?: string
  dataKey: string
  nameKey: string
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
  className?: string
  height?: number
  colors?: string[]
  showLegend?: boolean
  showLabels?: boolean
  innerRadius?: number
  outerRadius?: number
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
  '#EC4899',
  '#14B8A6',
]

export const PieChart: React.FC<PieChartProps> = ({
  data,
  title,
  subtitle,
  dataKey,
  nameKey,
  loading = false,
  error,
  onRefresh,
  onExport,
  className = '',
  height = 400,
  colors = DEFAULT_COLORS,
  showLegend = true,
  showLabels = true,
  innerRadius = 0,
  outerRadius = 120,
  formatTooltip,
}) => {
  const formatValue = (value: any) => {
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

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-medium text-gray-900 mb-1">{data[nameKey]}</p>
          <p className="text-sm text-gray-600">
            {formatTooltip ? (
              formatTooltip(data[dataKey], data[nameKey])[0]
            ) : (
              formatValue(data[dataKey])
            )}
          </p>
          {data.percentage && (
            <p className="text-xs text-gray-500 mt-1">
              {data.percentage.toFixed(1)}% din total
            </p>
          )}
        </div>
      )
    }
    return null
  }

  const CustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, value, index }: any) => {
    const RADIAN = Math.PI / 180
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5
    const x = cx + radius * Math.cos(-midAngle * RADIAN)
    const y = cy + radius * Math.sin(-midAngle * RADIAN)

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        className="text-xs font-medium"
      >
        {`${((value / data.reduce((a, b) => a + b[dataKey], 0)) * 100).toFixed(0)}%`}
      </text>
    )
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
        <RechartsPieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={showLabels ? CustomLabel : false}
            outerRadius={outerRadius}
            innerRadius={innerRadius}
            fill="#8884d8"
            dataKey={dataKey}
            className="transition-all duration-200"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          {showLegend && (
            <Legend
              verticalAlign="bottom"
              height={36}
              wrapperStyle={{ paddingTop: '20px' }}
            />
          )}
        </RechartsPieChart>
      </ResponsiveContainer>
    </BaseChart>
  )
}

// Specialized pie chart components
export const RiskDistributionPieChart: React.FC<{
  data: any[]
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
}> = ({ data, loading, error, onRefresh, onExport }) => {
  const riskColors = {
    'low': '#10B981',
    'medium': '#F59E0B',
    'high': '#EF4444',
    'critical': '#7C2D12',
  }

  const coloredData = data.map(item => ({
    ...item,
    color: riskColors[item.risk_level as keyof typeof riskColors] || '#6B7280'
  }))

  return (
    <PieChart
      data={coloredData}
      title="Distribuția Riscurilor"
      subtitle="Clasificarea licitațiilor pe nivele de risc"
      dataKey="count"
      nameKey="risk_level"
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      colors={coloredData.map(item => item.color)}
      formatTooltip={(value, name) => [
        `${value} licitații`,
        `Risc ${name === 'low' ? 'scăzut' : name === 'medium' ? 'mediu' : name === 'high' ? 'ridicat' : 'critic'}`
      ]}
    />
  )
}

export const CPVDistributionChart: React.FC<{
  data: any[]
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
}> = ({ data, loading, error, onRefresh, onExport }) => {
  return (
    <PieChart
      data={data.slice(0, 10)} // Top 10 CPV codes
      title="Distribuția CPV"
      subtitle="Top 10 coduri CPV după valoare"
      dataKey="total_value"
      nameKey="description"
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      formatTooltip={(value, name) => [
        `${value.toLocaleString('ro-RO')} RON`,
        name.length > 30 ? name.substring(0, 30) + '...' : name
      ]}
    />
  )
}

export const CountyDistributionChart: React.FC<{
  data: any[]
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
}> = ({ data, loading, error, onRefresh, onExport }) => {
  return (
    <PieChart
      data={data.slice(0, 15)} // Top 15 counties
      title="Distribuția pe Județe"
      subtitle="Top 15 județe după numărul de licitații"
      dataKey="count"
      nameKey="county"
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      colors={['#002B7F', '#FCD116', '#CE1126', '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#14B8A6', '#6366F1', '#8B5A2B']}
      formatTooltip={(value, name) => [
        `${value} licitații`,
        `Județul ${name}`
      ]}
    />
  )
}

export const DonutChart: React.FC<{
  data: any[]
  title: string
  subtitle?: string
  dataKey: string
  nameKey: string
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
  centerText?: string
  centerSubtext?: string
}> = ({ 
  data, 
  title, 
  subtitle, 
  dataKey, 
  nameKey, 
  loading, 
  error, 
  onRefresh, 
  onExport,
  centerText,
  centerSubtext
}) => {
  const total = data.reduce((sum, item) => sum + item[dataKey], 0)

  return (
    <BaseChart
      title={title}
      subtitle={subtitle}
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      height={400}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RechartsPieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={120}
            paddingAngle={2}
            dataKey={dataKey}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={DEFAULT_COLORS[index % DEFAULT_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: any) => [value.toLocaleString('ro-RO'), '']}
          />
          <Legend verticalAlign="bottom" height={36} />
          
          {/* Center text */}
          {centerText && (
            <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" className="text-2xl font-bold fill-gray-900">
              {centerText}
            </text>
          )}
          {centerSubtext && (
            <text x="50%" y="50%" dy={20} textAnchor="middle" dominantBaseline="middle" className="text-sm fill-gray-600">
              {centerSubtext}
            </text>
          )}
        </RechartsPieChart>
      </ResponsiveContainer>
    </BaseChart>
  )
}