import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '/api/v1').trim()

const instance: AxiosInstance = axios.create({
  baseURL: apiBaseUrl,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

instance.interceptors.request.use(
  (config) => {
    const runtimeKey = localStorage.getItem('geo_internal_api_key') || import.meta.env.VITE_INTERNAL_API_KEY
    if (runtimeKey) {
      config.headers['x-api-key'] = runtimeKey
    }
    return config
  },
  (error) => Promise.reject(error)
)

instance.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

export default instance
