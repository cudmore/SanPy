<!-- src/components/DandisetConfig.vue -->
<script setup lang="ts">
import { ref } from 'vue';

const emit = defineEmits<{
  (e: 'load', dandisetId: string, version: string): void;
}>();

// Single input supporting formats like "001261/0.250917.2023" or just "001261"
const dandisetInput = ref('001261/0.250917.2023');

const handleLoad = () => {
  const raw = dandisetInput.value.trim();
  if (!raw) return;

  let dandisetId = raw;
  let version = 'draft';

  if (raw.includes('/')) {
    const parts = raw.split('/');
    dandisetId = parts[0];
    version = parts.slice(1).join('/') || 'draft';
  }

  emit('load', dandisetId, version);
};
</script>

<template>
  <div class="bg-white p-4 rounded-lg shadow mb-6 flex flex-wrap items-end gap-4">
    <div class="flex-grow max-w-md">
      <label class="block text-sm font-medium text-gray-700 mb-1">Dandiset ID / Version Path</label>
      <input 
        v-model="dandisetInput" 
        type="text" 
        placeholder="e.g. 001261/0.250917.2023"
        class="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
    <button 
      @click="handleLoad" 
      class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded shadow transition"
    >
      Load Dandiset
    </button>
  </div>
</template>
