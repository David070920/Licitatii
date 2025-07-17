import React from 'react'
import { useParams } from 'react-router-dom'
import { Calendar, MapPin, Building, DollarSign, Users, FileText, AlertTriangle } from 'lucide-react'
import { RiskScore } from '../components/charts/RiskVisualization'

export const TenderDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  
  // Mock tender data
  const tender = {
    id: id || '1',
    title: 'Achiziție echipamente IT pentru administrația publică',
    description: 'Licitație publică pentru achiziția de echipamente IT moderne destinate modernizării infrastructurii informatice a administrației publice locale.',
    authority_name: 'Primăria Municipiului Cluj-Napoca',
    authority_cui: 'RO4327710',
    external_id: 'CN-2024-001',
    cpv_code: '30200000-1',
    cpv_description: 'Echipamente pentru calculatoare și tehnologia informației',
    procedure_type: 'Licitație deschisă',
    publication_date: '2024-01-15',
    deadline: '2024-02-15',
    estimated_value: 2500000,
    county: 'Cluj',
    city: 'Cluj-Napoca',
    status: 'Publicat',
    risk_score: 72.5,
    risk_level: 'high',
    risk_factors: ['Ofertant unic', 'Preț neobișnuit', 'Timp scurt pentru oferte'],
    documents: [
      { name: 'Caietul de sarcini', url: '#', size: '2.5 MB' },
      { name: 'Formularul de participare', url: '#', size: '1.2 MB' },
      { name: 'Anexa tehnică', url: '#', size: '3.8 MB' }
    ],
    timeline: [
      { event: 'Publicare anunț', date: '2024-01-15', status: 'completed' },
      { event: 'Clarificări', date: '2024-01-25', status: 'completed' },
      { event: 'Depunere oferte', date: '2024-02-15', status: 'current' },
      { event: 'Evaluare oferte', date: '2024-02-20', status: 'pending' },
      { event: 'Adjudecare', date: '2024-02-25', status: 'pending' }
    ]
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                {tender.title}
              </h1>
              <p className="text-gray-600 mb-4">{tender.description}</p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center text-sm text-gray-600">
                  <Building className="w-4 h-4 mr-2" />
                  {tender.authority_name}
                </div>
                <div className="flex items-center text-sm text-gray-600">
                  <MapPin className="w-4 h-4 mr-2" />
                  {tender.city}, {tender.county}
                </div>
                <div className="flex items-center text-sm text-gray-600">
                  <Calendar className="w-4 h-4 mr-2" />
                  Publicat: {new Date(tender.publication_date).toLocaleDateString('ro-RO')}
                </div>
                <div className="flex items-center text-sm text-gray-600">
                  <DollarSign className="w-4 h-4 mr-2" />
                  Valoare estimată: {tender.estimated_value.toLocaleString('ro-RO')} RON
                </div>
              </div>
            </div>
            
            <div className="ml-6">
              <RiskScore
                score={tender.risk_score}
                level={tender.risk_level}
                size="large"
              />
            </div>
          </div>
          
          {/* Risk factors */}
          <div className="border-t pt-4">
            <h3 className="text-sm font-medium text-gray-900 mb-2">Factori de risc identificați:</h3>
            <div className="flex flex-wrap gap-2">
              {tender.risk_factors.map((factor, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800"
                >
                  <AlertTriangle className="w-3 h-3 mr-1" />
                  {factor}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Details Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Tender Information */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Detalii licitație
            </h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700">ID extern</label>
                <p className="text-sm text-gray-900">{tender.external_id}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Cod CPV</label>
                <p className="text-sm text-gray-900">{tender.cpv_code}</p>
                <p className="text-xs text-gray-500">{tender.cpv_description}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Tip procedură</label>
                <p className="text-sm text-gray-900">{tender.procedure_type}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Termen limită</label>
                <p className="text-sm text-gray-900">{new Date(tender.deadline).toLocaleDateString('ro-RO')}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Status</label>
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  {tender.status}
                </span>
              </div>
            </div>
          </div>

          {/* Documents */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Documente
            </h2>
            <div className="space-y-3">
              {tender.documents.map((doc, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center">
                    <FileText className="w-5 h-5 text-gray-400 mr-3" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{doc.name}</p>
                      <p className="text-xs text-gray-500">{doc.size}</p>
                    </div>
                  </div>
                  <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                    Descarcă
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Timeline */}
        <div className="bg-white rounded-lg shadow-md p-6 mt-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Cronologie
          </h2>
          <div className="space-y-4">
            {tender.timeline.map((event, index) => (
              <div key={index} className="flex items-center">
                <div className={`w-4 h-4 rounded-full mr-4 ${
                  event.status === 'completed' ? 'bg-green-500' :
                  event.status === 'current' ? 'bg-blue-500' :
                  'bg-gray-300'
                }`} />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{event.event}</p>
                  <p className="text-xs text-gray-500">{new Date(event.date).toLocaleDateString('ro-RO')}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}