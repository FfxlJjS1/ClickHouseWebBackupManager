<template>
  <div class="backup-list">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-xl font-semibold">Available Backups</h2>
      <button 
        @click="$emit('refresh')"
        class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded"
      >
        Refresh
      </button>
    </div>

    <div v-if="loading" class="text-center py-8">
      <p>Loading backups...</p>
    </div>

    <div v-else-if="error" class="bg-red-100 text-red-700 p-4 rounded mb-4">
      {{ error }}
    </div>

    <div v-else>
      <div v-if="backups.length === 0" class="text-center py-8">
        <p>No backups found</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full bg-white rounded-lg overflow-hidden">
          <thead class="bg-gray-200">
            <tr>
              <th class="py-3 px-4 text-left">Name</th>
              <th class="py-3 px-4 text-left">Type</th>
              <th class="py-3 px-4 text-left">Date</th>
              <th class="py-3 px-4 text-left">Size</th>
              <th class="py-3 px-4 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="backup in backups" :key="backup.name" class="border-b hover:bg-gray-50">
              <td class="py-3 px-4">{{ backup.name }}</td>
              <td class="py-3 px-4">
                <StatusBadge :type="backup.type" />
              </td>
              <td class="py-3 px-4">{{ formatDate(backup.name) }}</td>
              <td class="py-3 px-4">{{ backup.size || 'N/A' }}</td>
              <td class="py-3 px-4">
                <button 
                  @click="restoreBackup(backup.name)"
                  class="bg-green-500 hover:bg-green-600 text-white px-3 py-1 rounded mr-2"
                  :disabled="isRestoring"
                >
                  Restore
                </button>
                <button 
                  @click="deleteBackup(backup.name)"
                  class="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded"
                  :disabled="isDeleting"
                >
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import StatusBadge from './StatusBadge.vue'

export default {
  components: { StatusBadge },
  props: {
    backups: Array,
    loading: Boolean,
    error: String
  },
  data() {
    return {
      isRestoring: false,
      isDeleting: false
    }
  },
  methods: {
    formatDate(backupName) {
      const match = backupName.match(/(\d{4})(\d{2})(\d{2})/)
      if (match) {
        return `${match[1]}-${match[2]}-${match[3]}`
      }
      return backupName
    },
    async restoreBackup(backupName) {
      // Извлекаем UUID из имени файла (удаляем .zip)
      const backupId = backupName.replace('.zip', '');

      if (!confirm(`Are you sure you want to restore ${backupName}? This will overwrite current data.`)) 
        return
      
      this.isRestoring = true
      try {
        const result = await this.$store.dispatch('restoreBackup', backupId)
        if (result.success) {
          alert('Restore completed successfully!')
        } else {
          alert(`Restore failed: ${result.message}`)
        }
      } finally {
        this.isRestoring = false
      }
    },
    async deleteBackup(backupName) {
      const backupId = backupName.replace('.zip', '');

      if (!confirm(`Permanently delete ${backupId}?`)) return
      
      this.isDeleting = true
      try {
      await this.$store.dispatch('deleteBackup', backupId);
        alert('Backup deleted successfully!');
      } finally {
        this.isDeleting = false
      }
    }
  }
}
</script>