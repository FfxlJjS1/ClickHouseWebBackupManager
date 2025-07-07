import { createStore } from 'vuex'
import axios from 'axios'

export default createStore({
  state: {
    backups: [],
    loading: false,
    error: null
  },
  mutations: {
    SET_BACKUPS(state, backups) {
      state.backups = backups
    },
    SET_LOADING(state, isLoading) {
      state.loading = isLoading
    },
    SET_ERROR(state, error) {
      state.error = error
    }
  },
  actions: {
    async fetchBackups({ commit }) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      
      try {
        const response = await axios.get('/api/backups')
        const backups = response.data.map(name => ({
          name,
          type: name.includes('inc') ? 'incremental' : 'full',
          size: 'N/A' // В реальном приложении можно добавить размер
        }))
        commit('SET_BACKUPS', backups)
      } catch (error) {
        commit('SET_ERROR', 'Failed to load backups: ' + error.message)
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    async createBackup({ commit, dispatch }, backupType) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      
      try {
        await axios.post('/api/backups/create', null, {
          params: { backup_type: backupType }
        })
        // Даем время на создание бэкапа перед обновлением списка
        setTimeout(() => dispatch('fetchBackups'), 2000)
      } catch (error) {
        commit('SET_ERROR', 'Backup creation failed: ' + error.message)
        throw error
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    async restoreBackup({ commit }, backupId) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      
      try {
        await axios.post(`/api/backups/restore/${encodeURIComponent(backupId)}`)
        return { success: true, message: 'Restore initiated successfully' }
      } catch (error) {
        commit('SET_ERROR', 'Restore failed: ' + error.message)
        return { success: false, message: error.message }
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    async deleteBackup({ commit, dispatch }, backupId) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      
      try {
        await axios.delete(`/api/backups/${encodeURIComponent(backupId)}`)
        dispatch('fetchBackups')
        return { success: true }
      } catch (error) {
        commit('SET_ERROR', 'Delete failed: ' + error.message)
        return { success: false }
      } finally {
        commit('SET_LOADING', false)
      }
    }
  }
})