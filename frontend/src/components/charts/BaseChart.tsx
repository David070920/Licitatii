import React, { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Download, Maximize2, Minimize2, RefreshCw } from 'lucide-react'

interface BaseChartProps {
  title: string
  subtitle?: string
  children: React.ReactNode
  loading?: boolean
  error?: string
  onRefresh?: () => void
  onExport?: () => void
  className?: string
  fullscreenEnabled?: boolean
  height?: number
}

export const BaseChart: React.FC<BaseChartProps> = ({
  title,
  subtitle,
  children,
  loading = false,
  error,
  onRefresh,
  onExport,
  className = '',
  fullscreenEnabled = true,
  height = 400,
}) => {
  const [isFullscreen, setIsFullscreen] = useState(false)
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  const handleFullscreenToggle = async () => {
    if (!chartRef.current) return

    try {
      if (isFullscreen) {
        await document.exitFullscreen()
      } else {
        await chartRef.current.requestFullscreen()
      }
    } catch (error) {
      console.error('Fullscreen error:', error)
    }
  }

  const containerVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { duration: 0.5 }
    }
  }

  const loadingVariants = {
    spin: {
      rotate: 360,
      transition: {
        duration: 1,
        repeat: Infinity,
        ease: 'linear'
      }
    }
  }

  if (error) {
    return (
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className={`card bg-white rounded-lg shadow-md border border-gray-200 ${className}`}
      >
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
          <div className="flex items-center justify-center h-64 text-red-500">
            <div className="text-center">
              <div className="text-4xl mb-2">⚠️</div>
              <p className="text-sm">{error}</p>
              {onRefresh && (
                <button
                  onClick={onRefresh}
                  className="mt-4 btn btn-sm btn-outline"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Încearcă din nou
                </button>
              )}
            </div>
          </div>
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div
      ref={chartRef}
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className={`card bg-white rounded-lg shadow-md border border-gray-200 ${className} ${
        isFullscreen ? 'fixed inset-0 z-50 rounded-none' : ''
      }`}
    >
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            {subtitle && (
              <p className="text-sm text-gray-600 mt-1">{subtitle}</p>
            )}
          </div>
          
          {/* Actions */}
          <div className="flex items-center space-x-2">
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={loading}
                className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                title="Actualizează datele"
              >
                <motion.div
                  animate={loading ? loadingVariants.spin : {}}
                >
                  <RefreshCw className="w-4 h-4" />
                </motion.div>
              </button>
            )}
            
            {onExport && (
              <button
                onClick={onExport}
                disabled={loading}
                className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                title="Exportă datele"
              >
                <Download className="w-4 h-4" />
              </button>
            )}
            
            {fullscreenEnabled && (
              <button
                onClick={handleFullscreenToggle}
                className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                title={isFullscreen ? 'Ieși din ecranul complet' : 'Ecran complet'}
              >
                {isFullscreen ? (
                  <Minimize2 className="w-4 h-4" />
                ) : (
                  <Maximize2 className="w-4 h-4" />
                )}
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div 
          className={`relative ${isFullscreen ? 'h-[calc(100vh-120px)]' : ''}`}
          style={{ height: isFullscreen ? undefined : height }}
        >
          {loading && (
            <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-10">
              <div className="text-center">
                <motion.div
                  animate={loadingVariants.spin}
                  className="w-8 h-8 border-2 border-primary-600 border-t-transparent rounded-full mx-auto mb-2"
                />
                <p className="text-sm text-gray-600">Se încarcă datele...</p>
              </div>
            </div>
          )}
          
          <div className={`h-full ${loading ? 'opacity-50' : ''}`}>
            {children}
          </div>
        </div>
      </div>
    </motion.div>
  )
}