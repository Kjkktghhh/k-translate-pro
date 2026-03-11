import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({ baseURL: API_BASE })

export const batchesAPI = {
  create: (formData) => api.post('/api/batches/', formData),
  list: () => api.get('/api/batches/'),
  get: (id) => api.get(`/api/batches/${id}`),
  getImages: (id, filter) => api.get(`/api/batches/${id}/images`, { params: { filter } }),
  correct: (batchId, imageId, data) => api.patch(`/api/batches/${batchId}/images/${imageId}/correct`, data),
  approve: (batchId, imageId) => api.post(`/api/batches/${batchId}/images/${imageId}/approve`),
  exportZip: (batchId) => `${API_BASE}/api/batches/${batchId}/export`,
}

export const glossariesAPI = {
  create: (data) => api.post('/api/glossaries/', data),
  list: () => api.get('/api/glossaries/'),
  get: (id) => api.get(`/api/glossaries/${id}`),
  getEntries: (id) => api.get(`/api/glossaries/${id}/entries`),
  addEntry: (id, entry) => api.post(`/api/glossaries/${id}/entries`, entry),
  uploadCsv: (id, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post(`/api/glossaries/${id}/upload-csv`, fd)
  },
  delete: (id) => api.delete(`/api/glossaries/${id}`),
}

export const imagesAPI = {
  originalUrl: (id) => `${API_BASE}/api/images/${id}/original`,
  outputUrl: (id, lang) => `${API_BASE}/api/images/${id}/output/${lang}`,
}

export default api
