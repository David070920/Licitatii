import React from 'react'
import { TenderGeographicMap, ValueGeographicMap } from '../components/maps/RomanianMap'

export const GeographicAnalysis: React.FC = () => {
  // Mock data for demonstration
  const mockGeographicData = [
    { county: 'Bucuresti', count: 150, total_value: 2500000000, average_value: 16666667 },
    { county: 'Cluj', count: 85, total_value: 1200000000, average_value: 14117647 },
    { county: 'Timis', count: 72, total_value: 980000000, average_value: 13611111 },
    { county: 'Constanta', count: 65, total_value: 850000000, average_value: 13076923 },
    { county: 'Iasi', count: 58, total_value: 720000000, average_value: 12413793 }
  ]

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Analiza Geografică
          </h1>
          <p className="text-gray-600">
            Vizualizarea distribuției geografice a achizițiilor publice pe teritoriul României
          </p>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <TenderGeographicMap
            data={mockGeographicData}
            loading={false}
            onRefresh={() => {}}
            onExport={() => {}}
            onCountyClick={(county) => console.log('Selected county:', county)}
          />
          
          <ValueGeographicMap
            data={mockGeographicData}
            loading={false}
            onRefresh={() => {}}
            onExport={() => {}}
            onCountyClick={(county) => console.log('Selected county:', county)}
          />
        </div>
        
        <div className="mt-8 bg-white rounded-lg p-6 shadow-md">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Statistici Geografice
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600 mb-2">42</div>
              <div className="text-sm text-gray-600">Județe Active</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600 mb-2">2.5B</div>
              <div className="text-sm text-gray-600">Valoare Totală (RON)</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-600 mb-2">430</div>
              <div className="text-sm text-gray-600">Licitații Totale</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-orange-600 mb-2">5.8M</div>
              <div className="text-sm text-gray-600">Valoare Medie (RON)</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}