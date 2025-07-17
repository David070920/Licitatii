import React from 'react'
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { BaseChart } from './BaseChart'

interface LineChartProps {
  data: any[]
  title: string
  subtitle?: string
  xAxisKey: string
  yAxisKey: string | string[]
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
  className?: string
  height?: number
  colors?: string[]
  showLegend?: boolean
  showGrid?: boolean
  showDots?: boolean
  formatYAxis?: (value: any) => string
  formatTooltip?: (value: any, name: string) => [string, string]
  referenceLines?: { value: number; label: string; color?: string }[]
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

export const LineChart: React.FC<LineChartProps> = ({
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
  showGrid = true,
  showDots = true,
  formatYAxis,
  formatTooltip,
  referenceLines = [],
}) => {
  const yAxisKeys = Array.isArray(yAxisKey) ? yAxisKey : [yAxisKey]

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
        <RechartsLineChart
          data={data}
          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
        >
          {showGrid && (
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          )}
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
            cursor={{ stroke: '#9CA3AF', strokeWidth: 1 }}
          />
          {showLegend && (
            <Legend
              wrapperStyle={{ paddingTop: '20px' }}
              iconType="line"
            />
          )}
          
          {/* Reference lines */}
          {referenceLines.map((refLine, index) => (
            <ReferenceLine
              key={index}
              y={refLine.value}
              stroke={refLine.color || '#EF4444'}
              strokeDasharray="5 5"
              label={refLine.label}
            />
          ))}
          
          {/* Data lines */}
          {yAxisKeys.map((key, index) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={colors[index % colors.length]}
              strokeWidth={2}
              dot={showDots ? { r: 4 } : false}
              activeDot={{ r: 6, stroke: colors[index % colors.length], strokeWidth: 2 }}
              className="transition-all duration-200"
            />
          ))}
        </RechartsLineChart>
      </ResponsiveContainer>
    </BaseChart>
  )
}

// Specialized line chart components
export const TenderVolumeTimeSeriesChart: React.FC<{
  data: any[]
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
}> = ({ data, loading, error, onRefresh, onExport }) => {
  return (
    <LineChart
      data={data}
      title="Evoluția în Timp a Licitațiilor"
      subtitle="Tendințe și variații pe perioade"
      xAxisKey="period"
      yAxisKey={['value']}
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      colors={['#002B7F']}
      formatYAxis={(value) => value.toLocaleString('ro-RO')}
      formatTooltip={(value, name) => [
        `${value.toLocaleString('ro-RO')}`,
        'Valoare'
      ]}
    />
  )
}

export const RiskTrendChart: React.FC<{
  data: any[]
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
}> = ({ data, loading, error, onRefresh, onExport }) => {
  return (
    <LineChart
      data={data}
      title="Evoluția Scorului de Risc"
      subtitle="Tendințe în detectarea riscurilor"
      xAxisKey="period"
      yAxisKey={['value']}
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      colors={['#EF4444']}
      referenceLines={[
        { value: 70, label: 'Risc ridicat', color: '#EF4444' },
        { value: 40, label: 'Risc mediu', color: '#F59E0B' },
      ]}
      formatYAxis={(value) => `${value}%`}
      formatTooltip={(value, name) => [
        `${value}%`,
        'Scor risc'
      ]}
    />
  )
}

export const MultiMetricChart: React.FC<{
  data: any[]
  metrics: string[]
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
}> = ({ data, metrics, loading, error, onRefresh, onExport }) => {
  return (
    <LineChart
      data={data}
      title="Analiza Multi-Metrică"
      subtitle="Compararea multiplelor indicatori"
      xAxisKey="period"
      yAxisKey={metrics}
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      height={500}
      colors={['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6']}
      formatYAxis={(value) => value.toLocaleString('ro-RO')}
    />
  )
}

export const ComparisonChart: React.FC<{
  data: any[]
  compareKeys: string[]
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
}> = ({ data, compareKeys, loading, error, onRefresh, onExport }) => {
  return (
    <LineChart
      data={data}
      title="Analiză Comparativă"
      subtitle="Compararea performanțelor"
      xAxisKey="period"
      yAxisKey={compareKeys}
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      height={500}
      colors={['#002B7F', '#FCD116', '#CE1126']}
      showDots={false}
      formatYAxis={(value) => value.toLocaleString('ro-RO')}
    />
  )
}