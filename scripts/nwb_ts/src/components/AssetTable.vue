<!-- src/components/AssetTable.vue -->
<script setup lang="ts">
import { ref, computed, watch } from 'vue';

const props = defineProps<{
  assets: Array<{ assetId: string; path: string; sizeMB: number }>;
  selectedAssetId: string | null;
}>();

const emit = defineEmits<{
  (e: 'select', assetId: string): void;
}>();

const currentPage = ref(1);
const itemsPerPage = 20;

// Reset to page 1 whenever the full asset list updates (e.g. loading a new Dandiset)
watch(() => props.assets, () => {
  currentPage.value = 1;
});

const totalPages = computed(() => Math.ceil(props.assets.length / itemsPerPage) || 1);

const paginatedAssets = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  return props.assets.slice(start, start + itemsPerPage);
});

const prevPage = () => {
  if (currentPage.value > 1) currentPage.value--;
};

const nextPage = () => {
  if (currentPage.value < totalPages.value) currentPage.value++;
};
</script>

<template>
  <div class="bg-white rounded-lg shadow overflow-hidden flex flex-col">
    <div class="px-4 py-3 bg-gray-50 border-b border-gray-200 flex justify-between items-center">
      <h3 class="text-sm font-semibold text-gray-700">NWB Asset Files</h3>
      <span class="text-xs text-gray-500" v-if="assets.length > 0">Total: {{ assets.length }} files</span>
    </div>

    <!-- Table Container -->
    <div class="overflow-y-auto max-h-80">
      <table class="w-full text-left border-collapse">
        <thead class="bg-gray-100 text-xs font-semibold text-gray-600 uppercase sticky top-0">
          <tr>
            <th class="px-4 py-2">File Path</th>
            <th class="px-4 py-2 text-right">Size (MB)</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200 text-sm">
          <tr 
            v-for="asset in paginatedAssets" 
            :key="asset.assetId"
            @click="emit('select', asset.assetId)"
            :class="[
              'cursor-pointer transition hover:bg-blue-50',
              selectedAssetId === asset.assetId ? 'bg-blue-100 font-medium' : ''
            ]"
          >
            <td class="px-4 py-2 text-gray-800 truncate max-w-xs" :title="asset.path">{{ asset.path }}</td>
            <td class="px-4 py-2 text-right text-gray-600">{{ asset.sizeMB }}</td>
          </tr>
          <tr v-if="assets.length === 0">
            <td colspan="2" class="px-4 py-6 text-center text-gray-400">No assets loaded yet. Click "Load Dandiset".</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination Footer -->
    <div class="px-4 py-2 bg-gray-50 border-t border-gray-200 flex items-center justify-between text-xs text-gray-600" v-if="assets.length > 0">
      <span>Page {{ currentPage }} of {{ totalPages }}</span>
      <div class="flex gap-1">
        <button 
          @click="prevPage" 
          :disabled="currentPage === 1"
          class="px-2.5 py-1 border rounded bg-white hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
        >Prev</button>
        <button 
          @click="nextPage" 
          :disabled="currentPage >= totalPages"
          class="px-2.5 py-1 border rounded bg-white hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
        >Next</button>
      </div>
    </div>
  </div>
</template>
