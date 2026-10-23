<!-- src/components/GenericPlot.vue -->
<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import Plotly, { type Data, type Layout } from 'plotly.js-dist-min';

export interface PlotTrace {
  name?: string;
  x: number[];
  y: number[];
  lineColor?: string;
}

const props = defineProps<{
  title: string;
  // Single trace fallbacks
  xData?: number[];
  yData?: number[];
  lineColor?: string;
  // Multi-trace support
  traces?: PlotTrace[];
  xLabel?: string;
  yLabel?: string;
  forcedXRange?: [number, number] | null;
}>();

const emit = defineEmits<{
  (e: 'relayout', range: [number, number]): void;
}>();

const plotContainer = ref<HTMLElement | null>(null);
let isInternalUpdate = false;

const renderPlot = () => {
  if (!plotContainer.value) return;

  let plotTraces: Data[] = [];

  if (props.traces && props.traces.length > 0) {
    plotTraces = props.traces.map((t, index) => {
      // Generate a subtle palette cascade if line color isn't explicitly provided
      const defaultColors = ['#2563eb', '#dc2626', '#16a34a', '#d97706', '#9333ea', '#0d9488'];
      const color = t.lineColor || defaultColors[index % defaultColors.length];
      
      return {
        x: t.x,
        y: t.y,
        name: t.name || `Sweep ${index + 1}`,
        type: 'scatter',
        mode: 'lines',
        line: { color, width: 1.2 },
        opacity: 0.85,
      };
    });
  } else if (props.xData && props.yData) {
    plotTraces = [{
      x: props.xData,
      y: props.yData,
      type: 'scatter',
      mode: 'lines',
      line: { color: props.lineColor || '#2563eb', width: 1.5 },
    }];
  }

  const xaxisConfig: any = { 
    title: props.xLabel || 'Time (s)' 
  };

  if (props.forcedXRange) {
    xaxisConfig.range = props.forcedXRange;
  }

  const layout: Partial<Layout> = {
    title: { text: props.title, font: { size: 14 } },
    margin: { l: 50, r: 20, t: 30, b: 40 },
    xaxis: xaxisConfig,
    yaxis: { title: props.yLabel || 'Amplitude' },
    autosize: true,
    showlegend: Boolean(props.traces && props.traces.length > 1),
  };

  const config = { responsive: true, displayModeBar: true };

  Plotly.react(plotContainer.value, plotTraces, layout, config).then(() => {
    const el = plotContainer.value as any;
    if (el && !el._hasRelayoutListener) {
      el._hasRelayoutListener = true;
      el.on('plotly_relayout', (eventData: any) => {
        if (isInternalUpdate) return;
        
        if (eventData['xaxis.range[0]'] !== undefined && eventData['xaxis.range[1]'] !== undefined) {
          emit('relayout', [eventData['xaxis.range[0]'], eventData['xaxis.range[1]']]);
        } else if (eventData['xaxis.autorange']) {
          const firstTraceX = props.traces?.[0]?.x || props.xData;
          if (firstTraceX) {
            emit('relayout', [firstTraceX[0] || 0, firstTraceX[firstTraceX.length - 1] || 1]);
          }
        }
      });
    }
  });
};

onMounted(renderPlot);
watch(() => [props.xData, props.yData, props.traces, props.title, props.yLabel, props.forcedXRange], renderPlot, { deep: true });
</script>

<template>
  <div class="w-full h-72 bg-white rounded-lg shadow p-2">
    <div ref="plotContainer" class="w-full h-full"></div>
  </div>
</template>
