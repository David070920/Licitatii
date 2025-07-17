import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

// Types for API responses
export interface TenderVolumeData {
  date: string
  count: number
  total_value: number
  average_value: number
}

export interface GeographicData {
  county: string
  count: number
  total_value: number
  average_value: number
  risk_score?: number
}

export interface RiskDistributionData {
  risk_level: string
  count: number
  percentage: number
}

export interface CompanyPerformanceData {
  company_name: string
  company_cui: string
  tender_count: number
  win_rate: number
  total_value: number
  average_value: number
  risk_score?: number
}

export interface CPVAnalysisData {
  cpv_code: string
  description: string
  count: number
  total_value: number
  average_value: number
  competition_level: number
}

export interface TimeSeriesData {
  period: string
  metric: string
  value: number
  change_percentage?: number
}

export interface DashboardMetrics {
  total_tenders: number
  total_value: number
  average_value: number
  active_tenders: number
  high_risk_tenders: number
  unique_companies: number
  unique_authorities: number
  average_risk_score: number
}

export interface ApiError {
  message: string
  status: number
  data?: any
}

class ApiService {
  private client: AxiosInstance
  
  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )
    
    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired, redirect to login
          localStorage.removeItem('access_token')
          window.location.href = '/login'
        }
        return Promise.reject(this.handleError(error))
      }
    )
  }
  
  private handleError(error: any): ApiError {
    if (error.response) {
      return {
        message: error.response.data?.message || 'An error occurred',
        status: error.response.status,
        data: error.response.data,
      }
    } else if (error.request) {
      return {
        message: 'Network error - please check your connection',
        status: 0,
      }
    } else {
      return {
        message: error.message || 'An unexpected error occurred',
        status: 0,
      }
    }
  }
  
  private async request<T>(config: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.client.request(config)
    return response.data
  }
  
  // Authentication endpoints
  async login(email: string, password: string): Promise<{ access_token: string; user: any }> {
    return this.request({
      method: 'POST',
      url: '/auth/login',
      data: { email, password },
    })
  }
  
  async register(userData: any): Promise<{ access_token: string; user: any }> {
    return this.request({
      method: 'POST',
      url: '/auth/register',
      data: userData,
    })
  }
  
  async getCurrentUser(): Promise<any> {
    return this.request({
      method: 'GET',
      url: '/auth/me',
    })
  }
  
  // Visualization endpoints
  async getDashboardMetrics(params?: {
    start_date?: string
    end_date?: string
  }): Promise<DashboardMetrics> {
    return this.request({
      method: 'GET',
      url: '/visualizations/dashboard/metrics',
      params,
    })
  }
  
  async getTenderVolumeData(params: {
    period?: string
    start_date?: string
    end_date?: string
  }): Promise<TenderVolumeData[]> {
    return this.request({
      method: 'GET',
      url: '/visualizations/charts/tender-volume',
      params,
    })
  }
  
  async getGeographicData(params?: {
    start_date?: string
    end_date?: string
  }): Promise<GeographicData[]> {
    return this.request({
      method: 'GET',
      url: '/visualizations/charts/geographic',
      params,
    })
  }
  
  async getRiskDistributionData(params?: {
    start_date?: string
    end_date?: string
  }): Promise<RiskDistributionData[]> {
    return this.request({
      method: 'GET',
      url: '/visualizations/charts/risk-distribution',
      params,
    })
  }
  
  async getCompanyPerformanceData(params?: {
    limit?: number
    sort_by?: string
    start_date?: string
    end_date?: string
  }): Promise<CompanyPerformanceData[]> {
    return this.request({
      method: 'GET',
      url: '/visualizations/charts/company-performance',
      params,
    })
  }
  
  async getCPVAnalysisData(params?: {
    limit?: number
    start_date?: string
    end_date?: string
  }): Promise<CPVAnalysisData[]> {
    return this.request({
      method: 'GET',
      url: '/visualizations/charts/cpv-analysis',
      params,
    })
  }
  
  async getTimeSeriesData(params: {
    metric: string
    period?: string
    start_date?: string
    end_date?: string
  }): Promise<TimeSeriesData[]> {
    return this.request({
      method: 'GET',
      url: '/visualizations/charts/time-series',
      params,
    })
  }
  
  async exportVisualizationData(params: {
    chart_type: string
    format?: string
    start_date?: string
    end_date?: string
  }): Promise<any> {
    return this.request({
      method: 'GET',
      url: '/visualizations/export/data',
      params,
    })
  }
  
  // Tender endpoints
  async getTenders(params?: {
    page?: number
    limit?: number
    search?: string
    status?: string
    county?: string
    cpv_code?: string
    min_value?: number
    max_value?: number
    start_date?: string
    end_date?: string
  }): Promise<any> {
    return this.request({
      method: 'GET',
      url: '/tenders',
      params,
    })
  }
  
  async getTender(id: string): Promise<any> {
    return this.request({
      method: 'GET',
      url: `/tenders/${id}`,
    })
  }
  
  // Company endpoints
  async getCompanies(params?: {
    page?: number
    limit?: number
    search?: string
    county?: string
  }): Promise<any> {
    return this.request({
      method: 'GET',
      url: '/companies',
      params,
    })
  }
  
  async getCompany(id: string): Promise<any> {
    return this.request({
      method: 'GET',
      url: `/companies/${id}`,
    })
  }
  
  // Authority endpoints
  async getAuthorities(params?: {
    page?: number
    limit?: number
    search?: string
    county?: string
  }): Promise<any> {
    return this.request({
      method: 'GET',
      url: '/authorities',
      params,
    })
  }
  
  async getAuthority(id: string): Promise<any> {
    return this.request({
      method: 'GET',
      url: `/authorities/${id}`,
    })
  }
  
  // Risk analysis endpoints
  async getRiskAnalysis(params?: {
    tender_id?: string
    risk_level?: string
    start_date?: string
    end_date?: string
  }): Promise<any> {
    return this.request({
      method: 'GET',
      url: '/risk/analysis',
      params,
    })
  }
  
  async getTenderRiskScore(tenderId: string): Promise<any> {
    return this.request({
      method: 'GET',
      url: `/risk/tender/${tenderId}`,
    })
  }
}

export const apiService = new ApiService()
export default apiService