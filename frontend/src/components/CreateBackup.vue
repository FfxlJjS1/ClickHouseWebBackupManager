<template>
  <div class="create-backup">
    <h2 class="text-xl font-semibold mb-4">Create New Backup</h2>
    
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <button 
        @click="createBackup('auto')"
        class="bg-blue-500 hover:bg-blue-600 text-white p-4 rounded-lg shadow transition"
        :disabled="loading"
      >
        <h3 class="font-bold text-lg mb-2">Auto Backup</h3>
        <p>Creates full backup on Sundays, incremental on other days</p>
      </button>
      
      <button 
        @click="createBackup('full')"
        class="bg-purple-500 hover:bg-purple-600 text-white p-4 rounded-lg shadow transition"
        :disabled="loading"
      >
        <h3 class="font-bold text-lg mb-2">Full Backup</h3>
        <p>Complete database snapshot</p>
      </button>
      
      <button 
        @click="createBackup('incremental')"
        class="bg-teal-500 hover:bg-teal-600 text-white p-4 rounded-lg shadow transition"
        :disabled="loading"
      >
        <h3 class="font-bold text-lg mb-2">Incremental Backup</h3>
        <p>Only changes since last full backup</p>
      </button>
    </div>
    
    <div v-if="message" :class="messageClass" class="p-4 rounded-lg">
      {{ message }}
    </div>
    
    <div v-if="loading" class="mt-4 p-4 bg-gray-100 rounded-lg">
      <p class="text-center">Creating backup, please wait...</p>
      <div class="mt-2 h-2 bg-gray-300 rounded overflow-hidden">
        <div class="h-full bg-blue-500 animate-pulse" style="width: 60%"></div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    loading: Boolean
  },
  data() {
    return {
      message: '',
      messageClass: ''
    }
  },
  methods: {
    async createBackup(type) {
      this.message = ''
      try {
        const result = await this.$store.dispatch('createBackup', type)
        
        if (result.success) {
          this.message = `Backup created successfully: ${result.output || ''}`
          this.messageClass = 'bg-green-100 text-green-800'
          this.$emit('backup-created')
        } else {
          this.message = `Error: ${result.message}`
          this.messageClass = 'bg-red-100 text-red-800'
        }
      } catch (error) {
        this.message = `Request failed: ${error.message}`
        this.messageClass = 'bg-red-100 text-red-800'
      }
    }
  }
}
</script>