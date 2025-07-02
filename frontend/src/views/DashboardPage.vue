<template>
  <div class="dashboard-page">
    <div class="mb-8">
      <CreateBackup 
        @backup-created="fetchBackups" 
        :loading="loading"
      />
    </div>
    
    <BackupList 
      :backups="backups"
      :loading="loading"
      :error="error"
      @refresh="fetchBackups"
    />
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex'
import CreateBackup from '@/components/CreateBackup.vue'
import BackupList from '@/components/BackupList.vue'

export default {
  name: 'DashboardPage',
  components: {
    CreateBackup,
    BackupList
  },
  computed: {
    ...mapState(['backups', 'loading', 'error'])
  },
  created() {
    this.fetchBackups()
  },
  methods: {
    ...mapActions(['fetchBackups'])
  }
}
</script>