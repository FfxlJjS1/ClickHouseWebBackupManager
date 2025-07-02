<template>
  <div class="settings">
    <h2 class="text-xl font-semibold mb-6">Backup Settings</h2>
    
    <div class="bg-white rounded-lg shadow p-6 max-w-2xl">
      <div class="mb-6">
        <label class="block text-gray-700 font-medium mb-2">
          Retention Period (days)
        </label>
        <input 
          v-model.number="localSettings.retentionDays"
          type="number"
          min="1"
          max="365"
          class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
        <p class="text-sm text-gray-500 mt-1">
          Backups older than this will be automatically deleted
        </p>
      </div>
      
      <div class="mb-6">
        <label class="flex items-center cursor-pointer">
          <div class="relative">
            <input 
              v-model="localSettings.autoBackup"
              type="checkbox"
              class="sr-only"
            >
            <div 
              class="block bg-gray-300 w-14 h-8 rounded-full"
              :class="{ 'bg-green-400': localSettings.autoBackup }"
            ></div>
            <div 
              class="dot absolute left-1 top-1 bg-white w-6 h-6 rounded-full transition transform"
              :class="{ 'translate-x-6': localSettings.autoBackup }"
            ></div>
          </div>
          <div class="ml-3 text-gray-700 font-medium">
            Enable Daily Automatic Backups
          </div>
        </label>
      </div>
      
      <button 
        @click="saveSettings"
        class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg"
        :disabled="isSaving"
      >
        {{ isSaving ? 'Saving...' : 'Save Settings' }}
      </button>
    </div>
  </div>
</template>

<script>
import { mapState } from 'vuex'

export default {
  name: 'SettingsPage',
  data() {
    return {
      localSettings: { ...this.$store.state.settings },
      isSaving: false
    }
  },
  computed: {
    ...mapState(['settings'])
  },
  watch: {
    settings: {
      handler(newSettings) {
        this.localSettings = { ...newSettings }
      },
      deep: true
    }
  },
  methods: {
    saveSettings() {
      this.isSaving = true
      // Simulate API call
      setTimeout(() => {
        this.$store.commit('UPDATE_SETTINGS', this.localSettings)
        this.isSaving = false
        alert('Settings saved successfully!')
      }, 800)
    }
  }
}
</script>

<style scoped>
.dot {
  transition: transform 0.3s ease;
}
</style>