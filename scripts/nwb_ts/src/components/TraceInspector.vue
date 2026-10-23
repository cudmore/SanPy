<!-- src/components/TraceInspector.vue -->
<script setup lang="ts">
import { ref, computed } from 'vue';
import GenericPlot, { type PlotTrace } from './GenericPlot.vue';
import type { SweepTimeSeries } from '../services/nwbService';

const props = defineProps<{
  acquisitionTraces: string[];
  selectedTrace: string;
  responseTrace: SweepTimeSeries | null;
  stimulusTrace: SweepTimeSeries | null;
  allResponseTraces?: SweepTimeSeries[];
  allStimulusTraces?: SweepTimeSeries[];
  showAllSweeps: boolean;
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:selectedTrace', traceName: string): void;
  (e: 'update:showAllSweeps', showAll: boolean): void;
  (e: 'prev'): void;
  (e: 'next'): void;
}>();

const handleCheckboxChange = (e: Event) => {
  const checked = (e.target as HTMLInputElement).checked;
  emit('update:showAllSweeps', checked);
};

const currentIndex = computed(() => props.acquisitionTraces.indexOf(props.selectedTrace));
const hasPrev = computed(() => currentIndex.value > 0);
const hasNext = computed(() => currentIndex.value >= 0 && currentIndex.value < props.acquisitionTraces.length - 1);

const sharedXRange = ref<[number, number] | null>(null);
const handleRelayout = (range: [number, number]) => {
  sharedXRange.value = range;
};

// Formatter for multi-trace plots
const formattedResponseTraces = computed<PlotTrace[]>(() => {
  if (props.showAllSweeps && props.allResponseTraces) {
    return props.allResponseTraces.filter(Boolean).map(t => ({ name: t.name, x: t.time, y: t.data }));
  }
  return props.responseTrace ? [{ name: props.responseTrace.name, x: props.responseTrace.time, y: props.responseTrace.data }] : [];
});

const formattedStimulusTraces = computed<PlotTrace[]>(() => {
  if (props.showAllSweeps && props.allStimulusTraces) {
    return props.allStimulusTraces.filter(Boolean).map(t => ({ name: t.name, x: t.time, y: t.data }));
  }
  return props.stimulusTrace ? [{ name: props.stimulusTrace.name, x: props.stimulusTrace.time, y: props.stimulusTrace.data }] : [];
});
</script>

<template>
  <div class="bg-white rounded-lg shadow p-4 flex flex-col gap-4 relative">

    <!-- Header & Controls (Two Rows) -->
    <div class="border-b pb-3 flex flex-col gap-2">
      <!-- Row 1: Title & Loading Badge -->
      <div class="flex items-center gap-3">
        <h3 class="text-sm font-semibold text-gray-700">Electrophysiology Inspector</h3>
        
        <!-- Status Feedback Badge (Fixed footprint with opacity toggle) -->
        <span 
          class="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full font-medium flex items-center gap-1 transition-opacity duration-150"
          :class="loading ? 'opacity-100 animate-pulse' : 'opacity-0 pointer-events-none'"
        >
          <svg class="animate-spin -ml-1 mr-1 h-3 w-3 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Loading data...
        </span>
      </div>

      <!-- Row 2: Controls (Checkbox + Sweep Navigation) -->
      <div class="flex items-center justify-between flex-wrap gap-2 pt-1" v-if="acquisitionTraces.length > 0">
        <!-- Show All Sweeps Checkbox -->
        <label class="flex items-center gap-1.5 text-xs font-medium text-gray-700 cursor-pointer select-none">
          <input 
            type="checkbox" 
            :checked="showAllSweeps" 
            @change="handleCheckboxChange"
            :disabled="loading"
            class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          Show All Sweeps
        </label>

        <!-- Sweep Navigation Controls -->
        <div class="flex items-center gap-2">
          <label class="text-xs font-medium text-gray-600">Sweep:</label>
          
          <div class="flex items-center gap-1">
            <button 
              @click="emit('prev')"
              :disabled="loading || showAllSweeps || !hasPrev"
              title="Previous"
              class="px-2.5 py-1 border border-gray-300 rounded text-xs font-bold bg-white hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
            >&lt;</button>

            <select 
              :value="selectedTrace"
              @change="emit('update:selectedTrace', ($event.target as HTMLSelectElement).value)"
              :disabled="loading || showAllSweeps"
              class="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              <option v-for="t in acquisitionTraces" :key="t" :value="t">{{ t }}</option>
            </select>

            <button 
              @click="emit('next')"
              :disabled="loading || showAllSweeps || !hasNext"
              title="Next"
              class="px-2.5 py-1 border border-gray-300 rounded text-xs font-bold bg-white hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
            >&gt;</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Plots Grid -->
    <div class="grid grid-cols-1 gap-4 relative">
      <GenericPlot 
        title="Response Trace (Acquisition)" 
        :traces="formattedResponseTraces"
        yLabel="Voltage"
        :forcedXRange="sharedXRange"
        @relayout="handleRelayout"
      />
      <GenericPlot 
        title="Stimulus Trace" 
        :traces="formattedStimulusTraces"
        yLabel="Current"
        :forcedXRange="sharedXRange"
        @relayout="handleRelayout"
      />
    </div>

  </div>
</template>
