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
      <button @click="resetFilters" class="reset-btn">Сбросить фильтры</button>

      <table border="1" cellpadding="5" cellspacing="0">
        <thead>
          <tr>
            <th @click="toggleSort('id')" class="sortable">
              ID 
              <span v-if="sortField === 'id'">{{ sortDirection === 'asc' ? '▲' : '▼' }}</span>
            </th>
            <th @click="toggleSort('type')" class="sortable">
              Тип 
              <span v-if="sortField === 'type'">{{ sortDirection === 'asc' ? '▲' : '▼' }}</span>
            </th>
            <th @click="toggleSort('description')" class="sortable">
              Описание 
              <span v-if="sortField === 'description'">{{ sortDirection === 'asc' ? '▲' : '▼' }}</span>
            </th>
            <th @click="toggleSort('base_backup')" class="sortable">
              ID базового бекапа 
              <span v-if="sortField === 'base_backup'">{{ sortDirection === 'asc' ? '▲' : '▼' }}</span>
            </th>
            <th @click="toggleSort('timestamp')" class="sortable">
              Дата создания 
              <span v-if="sortField === 'timestamp'">{{ sortDirection === 'asc' ? '▲' : '▼' }}</span>
            </th>
            <th @click="toggleSort('size')" class="sortable">
              Размер 
              <span v-if="sortField === 'size'">{{ sortDirection === 'asc' ? '▲' : '▼' }}</span>
            </th>
            <th @click="toggleSort('status')" class="sortable">
              Статус 
              <span v-if="sortField === 'status'">{{ sortDirection === 'asc' ? '▲' : '▼' }}</span>
            </th>
            <th>Действия</th>
          </tr>
          <tr class="filter-row">
            <td>
              <input type="text" v-model="filters.id" placeholder="Фильтр ID" />
            </td>
            <td>
              <select v-model="filters.type">
                <option value="">Все</option>
                <option value="full">Полный</option>
                <option value="incremental">Инкрементный</option>
              </select>
            </td>
            <td>
              <input type="text" v-model="filters.description" placeholder="Фильтр описания" />
            </td>
            <td>
              <input type="text" v-model="filters.base_backup" placeholder="Фильтр базового ID" />
            </td>
            <td>
              <input type="text" v-model="filters.timestamp" placeholder="Фильтр даты" />
            </td>
            <td>
              <select v-model="filters.size">
                <option value="">Все</option>
                <option value="small">Малые (< 1MB)</option>
                <option value="medium">Средние (1MB-100MB)</option>
                <option value="large">Большие (> 100MB)</option>
              </select>
            </td>
            <td>
              <select v-model="filters.status">
                <option value="">Все</option>
                <option value="BACKUP_CREATED">Успешно</option>
                <option value="BACKUP_FAILED">Ошибка</option>
                <option value="CREATING">В процессе</option>
              </select>
            </td>
            <td></td>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in processedBackups" :key="b.id">
            <td>{{ b.id }}</td>
            <td>{{ b.type }}</td>
            <td>{{ b.description || 'Без описания' }}</td>
            <td>{{ b.base_backup || 'Отсутствует' }}</td>
            <td>{{ formatDate(b.timestamp) }}</td>
            <td>{{ formatSize(b.size) }}</td>
            <td>{{ b.status }}</td>
            <td>
              <button @click="startRestore(b)">Восстановить</button>
              <button @click="deleteBackup(b)" :disabled="deletingId === b.id">Удалить</button>
            </td>
          </tr>
          <tr v-if="processedBackups.length === 0">
            <td colspan="8">Бэкапы не найдены</td>
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
import { ref, computed } from "vue";

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

// Состояние для сортировки
const sortField = ref("timestamp");
const sortDirection = ref("desc");

// Фильтры
const filters = ref({
  id: "",
  type: "",
  description: "",
  base_backup: "",
  timestamp: "",
  size: "",
  status: ""
});

const newBackup = ref({
  type: "full",
  description: "",
  base_backup_id: "",
  async_mode: false,
});

// Обработанные бэкапы с учетом сортировки и фильтрации
const processedBackups = computed(() => {
  let result = [...backups.value];
  
  // Применяем фильтры
  if (filters.value.id) {
    result = result.filter(b => b.id.toLowerCase().includes(filters.value.id.toLowerCase()));
  }
  if (filters.value.type) {
    result = result.filter(b => b.type === filters.value.type);
  }
  if (filters.value.description) {
    result = result.filter(b => 
      b.description && b.description.toLowerCase().includes(filters.value.description.toLowerCase())
    );
  }
  if (filters.value.base_backup) {
    result = result.filter(b => 
      b.base_backup && b.base_backup.toLowerCase().includes(filters.value.base_backup.toLowerCase())
    );
  }
  if (filters.value.timestamp) {
    result = result.filter(b => 
      formatDate(b.timestamp).toLowerCase().includes(filters.value.timestamp.toLowerCase())
    );
  }
  if (filters.value.size) {
    result = result.filter(b => {
      if (!b.size) return false;
      const bytes = b.size;
      if (filters.value.size === 'small') return bytes < 1000000;
      if (filters.value.size === 'medium') return bytes >= 1000000 && bytes < 100000000;
      if (filters.value.size === 'large') return bytes >= 100000000;
      return true;
    });
  }
  if (filters.value.status) {
    result = result.filter(b => b.status === filters.value.status);
  }
  
  // Применяем сортировку
  if (sortField.value) {
    result.sort((a, b) => {
      let valA = a[sortField.value];
      let valB = b[sortField.value];
      
      // Особые случаи для сортировки
      if (sortField.value === 'timestamp') {
        valA = new Date(valA).getTime();
        valB = new Date(valB).getTime();
      }
      if (sortField.value === 'size') {
        valA = valA || 0;
        valB = valB || 0;
      }
      if (sortField.value === 'base_backup') {
        valA = valA || '';
        valB = valB || '';
      }
      if (sortField.value === 'description') {
        valA = valA || '';
        valB = valB || '';
      }
      
      // Сравнение значений
      let comparison = 0;
      if (valA < valB) comparison = -1;
      if (valA > valB) comparison = 1;
      
      return sortDirection.value === 'asc' ? comparison : -comparison;
    });
  }
  
  return result;
});

function toggleSort(field) {
  if (sortField.value === field) {
    // Переключаем направление, если поле то же самое
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
  } else {
    // Новое поле сортировки
    sortField.value = field;
    sortDirection.value = 'asc';
  }
}

function resetFilters() {
  filters.value = {
    id: "",
    type: "",
    description: "",
    base_backup: "",
    timestamp: "",
    size: "",
    status: ""
  };
}

function formatDate(dt) {
  return new Date(dt).toLocaleString();
}

function formatSize(bytes) {
  if (bytes === null || bytes === undefined) return 'N/A';
  if (bytes === 0) return '0 B';
  
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${parseFloat((bytes / Math.pow(1024, i)).toFixed(2))} ${sizes[i]}`;
}

// Остальные методы остаются без изменений (fetchDatabases, fetchBackups, selectDatabase, createBackup, startRestore, deleteBackup)

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
  resetFilters();
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
.reset-btn {
  background-color: #f0f0f0;
  border: 1px solid #ccc;
  margin-left: 10px;
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
.sortable {
  cursor: pointer;
  position: relative;
  padding-right: 20px;
}
.sortable:hover {
  background-color: #f5f5f5;
}
.sortable span {
  position: absolute;
  right: 5px;
}
.filter-row input, .filter-row select {
  width: 90%;
  padding: 5px;
  box-sizing: border-box;
}
</style>