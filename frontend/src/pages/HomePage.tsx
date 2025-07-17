import React from 'react'
import { motion } from 'framer-motion'
import { BarChart3, Shield, Map, Building, TrendingUp, Users, FileText, Eye } from 'lucide-react'
import { Link } from 'react-router-dom'

const features = [
  {
    name: 'Transparență Totală',
    description: 'Acces complet la datele despre achizițiile publice din România',
    icon: Eye,
    color: 'bg-blue-500',
    href: '/transparency'
  },
  {
    name: 'Analiză de Risc',
    description: 'Detectarea automată a riscurilor de corupție în licitații',
    icon: Shield,
    color: 'bg-red-500',
    href: '/risk-analysis'
  },
  {
    name: 'Hartă Geografică',
    description: 'Vizualizarea geografică a achizițiilor pe județe',
    icon: Map,
    color: 'bg-green-500',
    href: '/geographic'
  },
  {
    name: 'Business Intelligence',
    description: 'Analize avansate pentru companii și decidenți',
    icon: Building,
    color: 'bg-purple-500',
    href: '/business'
  }
]

const stats = [
  { name: 'Licitații Monitorizate', value: '50,000+', change: '+12%' },
  { name: 'Valoare Totală', value: '2.5B RON', change: '+8%' },
  { name: 'Autorități', value: '1,200+', change: '+3%' },
  { name: 'Companii', value: '25,000+', change: '+15%' }
]

export const HomePage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="relative bg-gradient-to-r from-blue-600 to-blue-800 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <h1 className="text-4xl md:text-6xl font-bold mb-6">
              Platforma Română de
              <span className="block text-yellow-400">Achiziții Publice</span>
            </h1>
            <p className="text-xl md:text-2xl text-blue-100 mb-8 max-w-3xl mx-auto">
              Transparență, analiză și monitorizare în timp real a achizițiilor publice din România
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/transparency"
                className="bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors flex items-center justify-center gap-2"
              >
                <Eye className="w-5 h-5" />
                Explorează Datele
              </Link>
              <Link
                to="/business"
                className="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-blue-600 transition-colors flex items-center justify-center gap-2"
              >
                <BarChart3 className="w-5 h-5" />
                Business Intelligence
              </Link>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: index * 0.1 }}
              className="bg-white rounded-lg p-6 shadow-lg text-center"
            >
              <div className="text-3xl font-bold text-gray-900 mb-2">{stat.value}</div>
              <div className="text-gray-600 mb-2">{stat.name}</div>
              <div className="text-green-600 text-sm font-medium">{stat.change}</div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Features Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            Funcționalități Avansate
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Descoperă toate instrumentele disponibile pentru monitorizarea și analiza achizițiilor publice
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={feature.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: index * 0.1 }}
              className="bg-white rounded-lg p-8 shadow-lg hover:shadow-xl transition-shadow"
            >
              <div className="flex items-center mb-4">
                <div className={`p-3 rounded-lg ${feature.color} mr-4`}>
                  <feature.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900">{feature.name}</h3>
              </div>
              <p className="text-gray-600 mb-6">{feature.description}</p>
              <Link
                to={feature.href}
                className="inline-flex items-center text-blue-600 hover:text-blue-800 font-medium"
              >
                Explorează
                <TrendingUp className="w-4 h-4 ml-2" />
              </Link>
            </motion.div>
          ))}
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-gray-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Începe să Monitorizezi Achizițiile Publice
            </h2>
            <p className="text-xl text-gray-300 mb-8 max-w-3xl mx-auto">
              Accesează gratuit toate datele despre licitațiile publice din România
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/transparency"
                className="bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
              >
                <FileText className="w-5 h-5" />
                Acces Gratuit
              </Link>
              <Link
                to="/register"
                className="border-2 border-gray-300 text-gray-300 px-8 py-3 rounded-lg font-semibold hover:bg-gray-300 hover:text-gray-900 transition-colors flex items-center justify-center gap-2"
              >
                <Users className="w-5 h-5" />
                Creează Cont
              </Link>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}