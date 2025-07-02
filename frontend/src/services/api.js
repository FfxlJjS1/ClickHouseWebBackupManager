import axios from 'axios'

const api = axios.create({
  baseURL: process.env.VUE_APP_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': process.env.VUE_APP_API_KEY
  }
})

export default {
  async getBackups() {
    try {
      const response = await api.get('/backups/list')
      return response.data.backups || []
    } catch (error) {
      console.error('Error fetching backups:', error)
      return []
    }
  },

  async createBackup(type = 'auto') {
    try {
      const response = await api.post('/backups/create', { backup_type: type })
      return response.data
    } catch (error) {
      console.error('Error creating backup:', error)
      throw error
    }
  },

  async restoreBackup(name) {
    try {
      const response = await api.post(`/backups/restore/${name}`)
      return response.data
    } catch (error) {
      console.error('Error restoring backup:', error)
      throw error
    }
  }
}
