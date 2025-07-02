import { createStore } from 'vuex'
import axios from 'axios'

export default createStore({
  state: {
    backups: [],
    loading: false,
    error: null,
    settings: {
      retentionDays: 30,
      autoBackup: true
    }
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
    },
    UPDATE_SETTINGS(state, settings) {
      state.settings = { ...state.settings, ...settings }
    }
  },
  actions: {
    async fetchBackups({ commit }) {
      commit('SET_LOADING', true)
      try {
        const response = await axios.get('/backups/list')
        commit('SET_BACKUPS', response.data.backups)
        commit('SET_ERROR', null)
      } catch (error) {
        commit('SET_ERROR', 'Failed to fetch backups')
        console.error(error)
      } finally {
        commit('SET_LOADING', false)
      }
    },
    async createBackup({ dispatch }, type) {
      try {
        const response = await axios.post('/backups/create', { backup_type: type })
        dispatch('fetchBackups')
        return { 
          success: true,
          output: response.data.output || 'Backup created successfully'
        }
      } catch (error) {
        return { 
          success: false, 
          message: error.response?.data?.output || 'Unknown error' 
        }
      }
    },
    async restoreBackup({ commit }, backupName) {
      try {
        const response = await axios.post(`/backups/restore/${backupName}`)
        return { 
          success: true,
          output: response.data.output || 'Restore completed successfully'
        }
      } catch (error) {
        return { 
          success: false, 
          message: error.response?.data?.output || 'Restore failed' 
        }
      }
    }
  }
})