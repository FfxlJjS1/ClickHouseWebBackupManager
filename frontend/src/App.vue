<template>
  <div class="app">
    <h1>ClickHouse Backup Manager</h1>

    <section>
      <h2>Базы данных</h2>
      <button @click="fetchDatabases" :disabled="loadingDatabases">Обновить</button>
      <ul>
        <li v-for="db in databases" :key="db" @click="selectDatabase(db)" :class="{selected: db === selectedDatabase}">
          {{ db }}
        </li>
      </ul>
    </section>

    <section v-if="selectedDatabase">
      <h2>Бэкапы базы: {{ selectedDatabase }}</h2>
      <button @click="fetchBackups" :disabled="loadingBackups">Обновить список</button>

      <table border="1" cellpadding="5" cellspacing="0">
        <thead>
          <tr>
            <th>ID</th>
            <th>Тип</th>
            <th>Описание</th>
            <th>Место хранения</th>
            <th>Дата создания</th>
            <th>Статус</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in backups" :key="b.id">
            <td>{{ b.id }}</td>
            <td>{{ b.type }}</td>
            <td>{{ b.description || 'без описания' }}</td>
            <td>{{ b.destination }}</td>
            <td>{{ formatDate(b.timestamp) }}</td>
            <td>{{ b.status }}</td>
            <td>
              <button @click="startRestore(b)">Восстановить</button>
              <button @click="deleteBackup(b)" :disabled="deletingId === b.id">Удалить</button>
            </td>
          </tr>
          <tr v-if="backups.length === 0">
            <td colspan="7">Бэкапы не найдены</td>
          </tr>
        </tbody>
      </table>

      <h3>Создать бэкап</h3>
      <form @submit.prevent="createBackup">
        <label>
          Тип:
          <select v-model="newBackup.type">
            <option value="full">Полный</option>
            <option value="incremental">Инкрементный</option>
          </select>
        </label>
        <br />
        <label>
          Описание (название):<br />
          <input v-model="newBackup.description" placeholder="Описание бэкапа" />
        </label>
        <br />
        <label v-if="newBackup.type === 'incremental'">
          ID базового бэкапа:<br />
          <input v-model="newBackup.base_backup_id" placeholder="Введите ID базового полного бэкапа" required />
        </label>
        <br />
        <label>
          Асинхронно:
          <input type="checkbox" v-model="newBackup.async_mode" />
        </label>
        <br />
        <button type="submit" :disabled="creatingBackup">Создать</button>
      </form>

    </section>

    <div v-if="message" :class="{'message': true, 'error': isError}">
      {{ message }}
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";

const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

const databases = ref([]);
const backups = ref([]);
const selectedDatabase = ref(null);

const loadingDatabases = ref(false);
const loadingBackups = ref(false);
const creatingBackup = ref(false);
const deletingId = ref(null);

const message = ref("");
const isError = ref(false);

const showRestoreDialog = ref(false);
const selectedBackup = ref(null);

const newBackup = ref({
  type: "full",
  description: "",
  base_backup_id: "",
  async_mode: false,
});

function formatDate(dt) {
  return new Date(dt).toLocaleString();
}

async function fetchDatabases() {
  loadingDatabases.value = true;
  message.value = "";
  try {
    const res = await fetch(`${apiBase}/databases`);
    if (!res.ok) throw new Error(`Ошибка ${res.status}`);
    databases.value = await res.json();
  } catch (e) {
    message.value = `Ошибка загрузки баз: ${e.message}`;
    isError.value = true;
  } finally {
    loadingDatabases.value = false;
  }
}

async function fetchBackups() {
  if (!selectedDatabase.value) return;
  loadingBackups.value = true;
  message.value = "";
  try {
    const url = new URL(`${apiBase}/backups`);
    url.searchParams.set("database", selectedDatabase.value);
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Ошибка ${res.status}`);
    backups.value = await res.json();
  } catch (e) {
    message.value = `Ошибка загрузки бэкапов: ${e.message}`;
    isError.value = true;
  } finally {
    loadingBackups.value = false;
  }
}

function selectDatabase(db) {
  selectedDatabase.value = db;
  backups.value = [];
  fetchBackups();
  message.value = "";
  isError.value = false;
}

async function createBackup() {
  if (newBackup.value.type === "incremental" && !newBackup.value.base_backup_id.trim()) {
    message.value = "Для инкрементного бэкапа требуется ID базового бэкапа";
    isError.value = true;
    return;
  }
  creatingBackup.value = true;
  message.value = "";
  isError.value = false;
  try {
    const payload = {
      database: selectedDatabase.value,
      backup_type: newBackup.value.type,
      base_backup_id: newBackup.value.type === "incremental" ? newBackup.value.base_backup_id.trim() : undefined,
      async_mode: newBackup.value.async_mode,
      description: newBackup.value.description || undefined,
    };
    const res = await fetch(`${apiBase}/backups`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `Ошибка ${res.status}`);
    }
    const created = await res.json();
    message.value = `Бэкап создан с ID: ${created.id}`;
    isError.value = false;

    // Сброс формы после успешного создания
    newBackup.value.description = "";
    newBackup.value.base_backup_id = "";

    fetchBackups();
  } catch (e) {
    message.value = `Ошибка создания бэкапа: ${e.message}`;
    isError.value = true;
  } finally {
    creatingBackup.value = false;
  }
}

async function startRestore(backup) {
  if (!confirm(`Восстановить базу ${backup.database} из бэкапа ${backup.id}?\nВсе текущие данные будут удалены!`)) {
    return;
  }
  
  try {
    const payload = {
      database: backup.database,
      backup_id: backup.id,
      async_mode: false
    };
    
    const res = await fetch(`${apiBase}/backups/restore`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    
    if (!res.ok) throw new Error(await res.text());
    
    message.value = `Восстановление из бэкапа ${backup.id} запущено`;
    isError.value = false;
  } catch (e) {
    message.value = `Ошибка восстановления: ${e.message}`;
    isError.value = true;
  }
}

async function deleteBackup(backup) {
  if (!confirm(`Удалить бэкап ${backup.id}?`)) return;
  deletingId.value = backup.id;
  message.value = "";
  isError.value = false;
  try {
    const res = await fetch(`${apiBase}/backups/${backup.id}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `Ошибка ${res.status}`);
    }
    message.value = `Бэкап ${backup.id} удалён`;
    fetchBackups();
  } catch (e) {
    message.value = `Ошибка удаления: ${e.message}`;
    isError.value = true;
  } finally {
    deletingId.value = null;
  }
}

// При загрузке страницы подгружаем базы
fetchDatabases();
</script>

<style scoped>
.app {
  max-width: 1100px;
  margin: auto;
  font-family: Arial, sans-serif;
  padding: 1rem;
}
.selected {
  font-weight: bold;
  cursor: pointer;
  color: blue;
}
button {
  margin: 0.2rem;
}
.message {
  margin-top: 1rem;
  padding: 0.5rem;
  border-radius: 4px;
}
.message.error {
  background-color: #fdd;
  color: #900;
}
</style>
