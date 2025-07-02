<template>
  <div id="app">
    <header class="bg-gray-800 text-white p-4">
      <div class="container mx-auto flex justify-between items-center">
        <h1 class="text-2xl font-bold">ClickHouse Backup Manager</h1>
        <nav>
          <router-link to="/" class="mr-4">Dashboard</router-link>
          <router-link to="/settings">Settings</router-link>
        </nav>
      </div>
    </header>

    <main class="container mx-auto p-4">
      <router-view />
    </main>

    <footer class="bg-gray-100 py-4 mt-8">
      <div class="container mx-auto text-center text-gray-600">
        Backup System &copy; {{ new Date().getFullYear() }}
      </div>
    </footer>
  </div>
</template>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.router-link-exact-active {
  border-bottom: 2px solid #4299e1;
  padding-bottom: 2px;
}
</style>