<template>
  <div class="create-backup">
    <h2 class="text-xl font-semibold mb-4">Create New Backup</h2>
    
    <div class="flex items-center space-x-4">
      <div class="flex items-center">
        <input 
          type="radio" 
          id="full" 
          value="full" 
          v-model="backupType" 
          class="mr-2"
        >
        <label for="full">Full Backup</label>
      </div>
      
      <div class="flex items-center">
        <input 
          type="radio" 
          id="incremental" 
          value="incremental" 
          v-model="backupType" 
          class="mr-2"
        >
        <label for="incremental">Incremental</label>
      </div>
      
      <button
        @click="createBackup"
        :disabled="isCreating"
        class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded"
      >
        <span v-if="isCreating">Creating...</span>
        <span v-else>Create Backup</span>
      </button>
    </div>
    
    <div v-if="error" class="mt-4 bg-red-100 text-red-700 p-3 rounded">
      {{ error }}
    </div>
  </div>
</template>

<script>
export default {
  name: 'CreateBackup',
  data() {
    return {
      backupType: 'full',
      isCreating: false,
      error: null
    }
  },
  methods: {
    async createBackup() {
      this.isCreating = true;
      this.error = null;
      
      try {
        await this.$store.dispatch('createBackup', this.backupType);
      } catch (error) {
        this.error = error.message || 'Failed to create backup';
      } finally {
        this.isCreating = false;
      }
    }
  }
}
</script>