import React, { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, GeoJSON, Marker, Popup } from 'react-leaflet'
import { LatLngBounds } from 'leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { BaseChart } from '../charts/BaseChart'

// Fix leaflet icon issues
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
})

interface GeographicMapProps {
  data: any[]
  title: string
  subtitle?: string
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
  className?: string
  height?: number
  colorProperty?: string
  colorScale?: string[]
  showMarkers?: boolean
  showTooltips?: boolean
  onCountyClick?: (county: string) => void
}

// Romanian counties GeoJSON data (simplified)
const romanianCounties = {
  "type": "FeatureCollection",
  "features": [
    // This would normally contain the full GeoJSON data for Romanian counties
    // For demonstration purposes, we'll use a simplified structure
    {
      "type": "Feature",
      "properties": {
        "name": "Bucuresti",
        "county": "Bucuresti"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [26.0, 44.3],
          [26.2, 44.3],
          [26.2, 44.5],
          [26.0, 44.5],
          [26.0, 44.3]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Cluj",
        "county": "Cluj"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [23.4, 46.6],
          [23.8, 46.6],
          [23.8, 47.0],
          [23.4, 47.0],
          [23.4, 46.6]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Timis",
        "county": "Timis"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [21.2, 45.7],
          [21.6, 45.7],
          [21.6, 46.1],
          [21.2, 46.1],
          [21.2, 45.7]
        ]]
      }
    }
    // More counties would be added here in a real implementation
  ]
}

const DEFAULT_COLOR_SCALE = [
  '#FEF0D9',
  '#FDCC8A',
  '#FC8D59',
  '#E34A33',
  '#B30000'
]

export const RomanianMap: React.FC<GeographicMapProps> = ({
  data,
  title,
  subtitle,
  loading = false,
  error,
  onRefresh,
  onExport,
  className = '',
  height = 500,
  colorProperty = 'count',
  colorScale = DEFAULT_COLOR_SCALE,
  showMarkers = false,
  showTooltips = true,
  onCountyClick,
}) => {
  const mapRef = useRef<any>(null)
  
  // Romanian bounds
  const romanianBounds = new LatLngBounds(
    [43.618682, 20.261194], // Southwest
    [48.265273, 29.715805]  // Northeast
  )

  // Get color based on data value
  const getColor = (value: number, maxValue: number) => {
    if (maxValue === 0) return colorScale[0]
    const normalizedValue = value / maxValue
    const index = Math.min(Math.floor(normalizedValue * colorScale.length), colorScale.length - 1)
    return colorScale[index]
  }

  // Create data map for quick lookup
  const dataMap = data.reduce((acc, item) => {
    acc[item.county] = item
    return acc
  }, {} as any)

  // Get max value for color scaling
  const maxValue = Math.max(...data.map(item => item[colorProperty] || 0))

  // Style function for GeoJSON
  const getFeatureStyle = (feature: any) => {
    const countyData = dataMap[feature.properties.county] || {}
    const value = countyData[colorProperty] || 0
    
    return {
      fillColor: getColor(value, maxValue),
      weight: 2,
      opacity: 1,
      color: '#ffffff',
      dashArray: '3',
      fillOpacity: 0.7
    }
  }

  // Event handlers
  const onEachFeature = (feature: any, layer: any) => {
    const countyData = dataMap[feature.properties.county] || {}
    
    layer.on({
      mouseover: (e: any) => {
        const layer = e.target
        layer.setStyle({
          weight: 5,
          color: '#666',
          dashArray: '',
          fillOpacity: 0.7
        })
        layer.bringToFront()
      },
      mouseout: (e: any) => {
        const layer = e.target
        layer.setStyle(getFeatureStyle(feature))
      },
      click: (e: any) => {
        if (onCountyClick) {
          onCountyClick(feature.properties.county)
        }
        mapRef.current?.fitBounds(e.target.getBounds())
      }
    })

    // Add popup if tooltips are enabled
    if (showTooltips) {
      const popupContent = `
        <div class="p-2">
          <h4 class="font-bold text-lg">${feature.properties.name}</h4>
          <p class="text-sm text-gray-600">Județ: ${feature.properties.county}</p>
          <p class="text-sm">Licitații: ${countyData.count || 0}</p>
          <p class="text-sm">Valoare totală: ${(countyData.total_value || 0).toLocaleString('ro-RO')} RON</p>
          ${countyData.risk_score ? `<p class="text-sm">Scor risc: ${countyData.risk_score.toFixed(1)}</p>` : ''}
        </div>
      `
      layer.bindPopup(popupContent)
    }
  }

  // Create legend
  const Legend = () => {
    const legendItems = colorScale.map((color, index) => {
      const minVal = Math.round((index / colorScale.length) * maxValue)
      const maxVal = Math.round(((index + 1) / colorScale.length) * maxValue)
      
      return (
        <div key={index} className="flex items-center mb-1">
          <div 
            className="w-4 h-4 mr-2 border border-gray-300"
            style={{ backgroundColor: color }}
          />
          <span className="text-xs text-gray-600">
            {minVal} - {maxVal}
          </span>
        </div>
      )
    })

    return (
      <div className="absolute bottom-4 left-4 bg-white p-3 rounded-lg shadow-lg border border-gray-200 z-10">
        <h4 className="font-medium text-sm mb-2">{colorProperty === 'count' ? 'Număr licitații' : 'Valoare (RON)'}</h4>
        {legendItems}
      </div>
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
      fullscreenEnabled={true}
    >
      <div className="relative h-full">
        <MapContainer
          ref={mapRef}
          bounds={romanianBounds}
          zoom={7}
          scrollWheelZoom={true}
          className="h-full w-full rounded-lg"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          
          <GeoJSON
            data={romanianCounties as any}
            style={getFeatureStyle}
            onEachFeature={onEachFeature}
          />
          
          {/* Markers for specific locations */}
          {showMarkers && data.map((item, index) => {
            // This would need actual coordinates for each county
            // For demo purposes, using approximate coordinates
            const coordinates = getCountyCoordinates(item.county)
            if (coordinates) {
              return (
                <Marker key={index} position={coordinates}>
                  <Popup>
                    <div className="p-2">
                      <h4 className="font-bold">{item.county}</h4>
                      <p>Licitații: {item.count}</p>
                      <p>Valoare: {item.total_value?.toLocaleString('ro-RO')} RON</p>
                    </div>
                  </Popup>
                </Marker>
              )
            }
            return null
          })}
        </MapContainer>
        
        <Legend />
      </div>
    </BaseChart>
  )
}

// Helper function to get county coordinates (simplified)
const getCountyCoordinates = (county: string): [number, number] | null => {
  const coordinates: { [key: string]: [number, number] } = {
    'Bucuresti': [44.4268, 26.1025],
    'Cluj': [46.7712, 23.6236],
    'Timis': [45.7489, 21.2087],
    'Constanta': [44.1598, 28.6348],
    'Iasi': [47.1585, 27.6014],
    'Brasov': [45.6427, 25.5887],
    'Dolj': [44.3302, 23.7949],
    'Galati': [45.4353, 28.0080],
    'Prahova': [45.1000, 26.0167],
    'Bihor': [47.0722, 21.9211],
    // Add more counties as needed
  }
  
  return coordinates[county] || null
}

// Specialized map components
export const TenderGeographicMap: React.FC<{
  data: any[]
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
  onCountyClick?: (county: string) => void
}> = ({ data, loading, error, onRefresh, onExport, onCountyClick }) => {
  return (
    <RomanianMap
      data={data}
      title="Distribuția Geografică a Licitațiilor"
      subtitle="Licitații pe județe cu vizualizare pe hartă"
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      onCountyClick={onCountyClick}
      colorProperty="count"
      height={600}
    />
  )
}

export const RiskGeographicMap: React.FC<{
  data: any[]
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
  onCountyClick?: (county: string) => void
}> = ({ data, loading, error, onRefresh, onExport, onCountyClick }) => {
  return (
    <RomanianMap
      data={data}
      title="Harta Riscurilor"
      subtitle="Distribuția geografică a riscurilor de corupție"
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      onCountyClick={onCountyClick}
      colorProperty="risk_score"
      colorScale={['#10B981', '#F59E0B', '#EF4444', '#7C2D12', '#450A0A']}
      height={600}
    />
  )
}

export const ValueGeographicMap: React.FC<{
  data: any[]
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
  onCountyClick?: (county: string) => void
}> = ({ data, loading, error, onRefresh, onExport, onCountyClick }) => {
  return (
    <RomanianMap
      data={data}
      title="Harta Valorilor"
      subtitle="Distribuția geografică a valorilor licitațiilor"
      loading={loading}
      error={error}
      onRefresh={onRefresh}
      onExport={onExport}
      onCountyClick={onCountyClick}
      colorProperty="total_value"
      colorScale={['#DBEAFE', '#93C5FD', '#3B82F6', '#1D4ED8', '#1E3A8A']}
      height={600}
    />
  )
}
