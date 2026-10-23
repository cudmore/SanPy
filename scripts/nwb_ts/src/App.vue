<!-- src/App.vue -->
<script setup lang="ts">
import { nextTick, ref } from 'vue';
import DandisetConfig from './components/DandisetConfig.vue';
import AssetTable from './components/AssetTable.vue';
import TraceInspector from './components/TraceInspector.vue';
import { NwbWebService, type SweepTimeSeries } from './services/nwbService';
import './style.css';

const nwbService = new NwbWebService();

const assets = ref<Array<{ assetId: string; path: string; sizeMB: number }>>([]);
const selectedAssetId = ref<string | null>(null);

const acquisitionTraces = ref<string[]>([]);
const selectedTrace = ref<string>('');

const responseTrace = ref<SweepTimeSeries | null>(null);
const stimulusTrace = ref<SweepTimeSeries | null>(null);

// Multi-sweep bulk state
const showAllSweeps = ref(false);
const allResponseTraces = ref<SweepTimeSeries[]>([]);
const allStimulusTraces = ref<SweepTimeSeries[]>([]);

const loading = ref(false);

// 1. Load Dandiset Assets
const handleLoadDandiset = async (dandisetId: string, version: string) => {
  try {
    loading.value = true;
    assets.value = await nwbService.fetchAssetOverview(dandisetId, version);
    selectedAssetId.value = null;
    acquisitionTraces.value = [];
    responseTrace.value = null;
    stimulusTrace.value = null;
    allResponseTraces.value = [];
    allStimulusTraces.value = [];
    showAllSweeps.value = false;
  } catch (err) {
    console.error('Error loading dandiset:', err);
    alert('Failed to load dandiset. Check console for details.');
  } finally {
    loading.value = false;
  }
};

// 2. Select Asset File
const handleSelectAsset = async (assetId: string) => {
  try {
    selectedAssetId.value = assetId;
    loading.value = true;
    
    const sweeps = await nwbService.getSweepNames(assetId);
    acquisitionTraces.value = sweeps.acquisition;
    
    if (sweeps.acquisition.length > 0) {
      selectedTrace.value = sweeps.acquisition[0];
      if (showAllSweeps.value) {
        await loadAllSweepsData(assetId);
      } else {
        await loadTraceData(assetId, selectedTrace.value, sweeps.stimulus);
      }
    }
  } catch (err) {
    console.error('Error parsing asset sweeps:', err);
  } finally {
    loading.value = false;
  }
};

// 3. Load Specific Sweep Trace & Stimulus
const loadTraceData = async (assetId: string, traceName: string, availableStimuli: string[]) => {
  loading.value = true;
  try {
    responseTrace.value = await nwbService.getTraceData(assetId, 'acquisition', traceName);

    const index = acquisitionTraces.value.indexOf(traceName);
    let matchingStim: string | undefined;

    if (index >= 0 && availableStimuli[index]) {
      matchingStim = availableStimuli[index];
    } else {
      matchingStim = availableStimuli.find(s => s === traceName) || availableStimuli[0];
    }

    if (matchingStim) {
      stimulusTrace.value = await nwbService.getTraceData(assetId, 'stimulus', matchingStim);
    } else {
      stimulusTrace.value = null;
    }
  } catch (err) {
    console.error('Error loading trace data:', err);
  } finally {
    loading.value = false;
  }
};

// 4. Load All Sweeps (Utilizes service bulk cache)
const loadAllSweepsData = async (assetId: string) => {
  loading.value = true;
  try {
    const { responses, stimuli } = await nwbService.getAllTraces(assetId);
    allResponseTraces.value = responses;
    allStimulusTraces.value = stimuli;
  } catch (err) {
    console.error('Error loading all sweeps:', err);
  } finally {
    loading.value = false;
  }
};

// Handle sweep dropdown change
const handleTraceChange = async (newTrace: string) => {
  selectedTrace.value = newTrace;
  if (selectedAssetId.value) {
    const sweeps = await nwbService.getSweepNames(selectedAssetId.value);
    await loadTraceData(selectedAssetId.value, newTrace, sweeps.stimulus);
  }
};

// Handle "Show All Sweeps" Checkbox Toggle
const handleShowAllSweepsToggle = async (showAll: boolean) => {
  if (!selectedAssetId.value) {
    showAllSweeps.value = showAll;
    return;
  }

  loading.value = true;
  // Paint the badge before the sweep read. requestAnimationFrame runs before
  // paint, and the read continues on microtasks, so the browser never paints it.
  await nextTick();
  await new Promise<void>((resolve) => {
    setTimeout(resolve, 0);
  });

  try {
    showAllSweeps.value = showAll;
    if (showAll) {
      await loadAllSweepsData(selectedAssetId.value);
    } else {
      const sweeps = await nwbService.getSweepNames(selectedAssetId.value);
      if (selectedTrace.value) {
        await loadTraceData(selectedAssetId.value, selectedTrace.value, sweeps.stimulus);
      }
    }
  } catch (err) {
    console.error('Error toggling sweeps:', err);
  } finally {
    loading.value = false;
  }
};

// Go to previous sweep
const handlePrevSweep = async () => {
  if (acquisitionTraces.value.length === 0 || !selectedTrace.value) return;
  const idx = acquisitionTraces.value.indexOf(selectedTrace.value);
  if (idx > 0) {
    const prevTrace = acquisitionTraces.value[idx - 1];
    selectedTrace.value = prevTrace;
    if (selectedAssetId.value) {
      const sweeps = await nwbService.getSweepNames(selectedAssetId.value);
      await loadTraceData(selectedAssetId.value, prevTrace, sweeps.stimulus);
    }
  }
};

// Go to next sweep
const handleNextSweep = async () => {
  if (acquisitionTraces.value.length === 0 || !selectedTrace.value) return;
  const idx = acquisitionTraces.value.indexOf(selectedTrace.value);
  if (idx >= 0 && idx < acquisitionTraces.value.length - 1) {
    const nextTrace = acquisitionTraces.value[idx + 1];
    selectedTrace.value = nextTrace;
    if (selectedAssetId.value) {
      const sweeps = await nwbService.getSweepNames(selectedAssetId.value);
      await loadTraceData(selectedAssetId.value, nextTrace, sweeps.stimulus);
    }
  }
};
</script>

<template>
  <div class="min-h-screen bg-gray-100 p-6">
    <div class="max-w-7xl mx-auto">
      <header class="mb-6">
        <h1 class="text-2xl font-bold text-gray-800">NWB & DANDI Static Web Explorer</h1>
        <p class="text-sm text-gray-600">Pure TypeScript / Vue 3 client powered by WebAssembly (h5wasm)</p>
      </header>

      <!-- Component 1: Configuration -->
      <DandisetConfig @load="handleLoadDandiset" />

      <!-- Main Layout Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Component 2: Asset Table -->
        <div class="lg:col-span-1">
          <AssetTable 
            :assets="assets" 
            :selectedAssetId="selectedAssetId" 
            @select="handleSelectAsset" 
          />
        </div>

        <!-- Component 3 & 4: Response & Stimulus Plots -->
        <div class="lg:col-span-2">
            <TraceInspector 
            :acquisitionTraces="acquisitionTraces"
            v-model:selectedTrace="selectedTrace"
            :showAllSweeps="showAllSweeps"
            :responseTrace="responseTrace"
            :stimulusTrace="stimulusTrace"
            :allResponseTraces="allResponseTraces"
            :allStimulusTraces="allStimulusTraces"
            :loading="loading"
            @update:selectedTrace="handleTraceChange"
            @update:showAllSweeps="handleShowAllSweepsToggle"
            @prev="handlePrevSweep"
            @next="handleNextSweep"
            />
        </div>
      </div>
    </div>
  </div>
</template>
