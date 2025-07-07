<template>
  <div class="settings-page">
    <h2 class="text-xl font-semibold mb-6">System Settings</h2>
    
    <div class="bg-white p-6 rounded-lg shadow-md">
      <h3 class="text-lg font-medium mb-4">Backup Configuration</h3>
      
      <div class="space-y-4">
        <div>
          <label class="block text-gray-700 mb-1">Backup Storage Path</label>
          <input 
            type="text" 
            v-model="storagePath"
            class="w-full p-2 border rounded"
            disabled
          >
        </div>
        
        <div>
          <label class="block text-gray-700 mb-1">Auto Backup Schedule</label>
          <select v-model="schedule" class="w-full p-2 border rounded">
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
      </div>
      
      <button class="mt-6 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded">
        Save Settings
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SettingsPage',
  data() {
    return {
      storagePath: '/backups',
      schedule: 'daily'
    }
  }
}
</script>