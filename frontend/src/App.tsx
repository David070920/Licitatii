import React, { useState } from 'react'

function App() {
  const [currentPage, setCurrentPage] = useState('home')

  const HomePage = () => (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Romanian Public Procurement Platform
        </h1>
        <p className="text-gray-600 mb-8">
          Platform pentru transparența achizițiilor publice
        </p>
        <div className="bg-white p-6 rounded-lg shadow-lg max-w-md mx-auto">
          <h2 className="text-xl font-semibold mb-4">Status</h2>
          <p className="text-green-600 mb-2">✅ Frontend: Deployed</p>
          <p className="text-green-600 mb-2">✅ Backend: Working</p>
          <p className="text-blue-600">🔄 Integration: Ready</p>
        </div>
      </div>
    </div>
  )

  const TransparencyDashboard = () => (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          Dashboard Transparență
        </h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Total Licitații</h3>
            <p className="text-3xl font-bold text-blue-600">1,250</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Valoare Totală</h3>
            <p className="text-3xl font-bold text-green-600">2.5B RON</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Autorități</h3>
            <p className="text-3xl font-bold text-purple-600">120</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Companii</h3>
            <p className="text-3xl font-bold text-orange-600">850</p>
          </div>
        </div>
      </div>
    </div>
  )

  const BusinessDashboard = () => (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          Business Intelligence
        </h1>
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Analiză Piață</h2>
          <p className="text-gray-600">
            Instrumentele de business intelligence pentru monitorizarea oportunităților de afaceri.
          </p>
        </div>
      </div>
    </div>
  )

  const Navigation = () => (
    <nav className="bg-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <button 
              onClick={() => setCurrentPage('home')}
              className="text-xl font-bold text-gray-900"
            >
              Licitații România
            </button>
          </div>
          <div className="flex items-center space-x-4">
            <button 
              onClick={() => setCurrentPage('home')}
              className={`${currentPage === 'home' ? 'text-blue-600' : 'text-gray-600'} hover:text-gray-900`}
            >
              Acasă
            </button>
            <button 
              onClick={() => setCurrentPage('transparency')}
              className={`${currentPage === 'transparency' ? 'text-blue-600' : 'text-gray-600'} hover:text-gray-900`}
            >
              Transparență
            </button>
            <button 
              onClick={() => setCurrentPage('business')}
              className={`${currentPage === 'business' ? 'text-blue-600' : 'text-gray-600'} hover:text-gray-900`}
            >
              Business
            </button>
          </div>
        </div>
      </div>
    </nav>
  )

  const renderPage = () => {
    switch (currentPage) {
      case 'transparency':
        return <TransparencyDashboard />
      case 'business':
        return <BusinessDashboard />
      default:
        return <HomePage />
    }
  }

  return (
    <div className="App">
      <Navigation />
      {renderPage()}
    </div>
  )
}

export default App