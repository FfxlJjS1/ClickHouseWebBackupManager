<template>
  <span :class="badgeClasses">
    {{ typeLabel }}
  </span>
</template>

<script>
export default {
  props: {
    type: String
  },
  computed: {
    typeLabel() {
      if (this.type === 'full') return 'Full'
      if (this.type === 'incremental') return 'Incremental'
      return this.type || 'Unknown'
    },
    badgeClasses() {
      const base = 'px-2 py-1 rounded-full text-xs font-bold'
      
      if (this.type === 'full') 
        return `${base} bg-blue-100 text-blue-800`
      
      if (this.type === 'incremental') 
        return `${base} bg-green-100 text-green-800`
      
      return `${base} bg-gray-100 text-gray-800`
    }
  }
}
</script>