## Developer Documentation (readme-dev.md)

Welcome to the NWB & DANDI Static Web Explorer codebase. This document outlines the system architecture, data flow, concurrency patterns, and key component structures designed for running high-performance electrophysiology data inspection entirely client-side via WebAssembly.

## 1. High-Level Architecture

The application is a client-side single-page application built with Vue 3, TypeScript, and Vite. It bypasses backend servers for data parsing by leveraging h5wasm (an official WebAssembly build of HDF5) to read binary NWB (Neurodata Without Borders) files directly inside the browser.

[ DANDI Archive ] 
       │ (REST API / Asset Download URL)
       ▼
[ NwbWebService ] ──(h5wasm Virtual FS)──> [ WASM HDF5 Runtime ]
       │
       ├─► Individual Trace Caching
       └─► Multi-Asset & Bulk Caching
       │
       ▼
[ Vue 3 Components ] ──> [ Plotly.js Visualization ]

## 2. Core Modules & Services

src/services/nwbService.ts (NwbWebService)

 - Asset Lifecycle: Downloads NWB assets as binary ArrayBuffer payloads from the DANDI API and mounts them into h5wasm's virtual file system (FS.writeFile).
 - Multi-Asset & Trace Caching:
    - Maintains an assetCache map (assetUuid -> AssetCacheEntry) ensuring that switching between files (Row 1 $\rightarrow$ Row 2 $\rightarrow$ Row 1) uses in-memory references instantly without re-downloading.
    - Memoizes individual sweep reads (cachedTraces) and bulk collections (cachedAllBulk).
 - HDF5 Parsing: Extracts acquisition and stimulus presentation keys, handles time-vector reconstruction (using explicit timestamps or calculating values from starting_time and sampling rate), and safely coerces unit attributes.

## 3. Component Hierarchy & Responsibilities

 - src/App.vue

    - Root orchestrator managing global state: selected dandiset assets, active trace selectors, bulk states (showAllSweeps), and global loading flags (loading).
    - Coordinates asynchronous data loading flows and passes reactive props down to feature components.

 - src/components/DandisetConfig.vue

    - Handles input configuration for DANDI dataset IDs and versions, triggering initial asset overview fetching.

 - src/components/AssetTable.vue
 
    - Displays paginated records of available NWB assets with metadata (paths, file sizes) and selection handlers.

 - src/components/TraceInspector.vue
 
    - Houses the two-row header layout:
    - Row 1: Title and an opacity-reserved loading badge (Loading data...) designed with a fixed DOM footprint to prevent page jitter or Plotly reflow artifacts.
    - Row 2: Interactive controls including the "Show All Sweeps" checkbox and sweep navigation dropdowns / prev/next buttons.

 - src/components/GenericPlot.vue

    - Encapsulates plotly.js-dist-min.
    - Supports both single trace rendering and multi-trace overlays (with automatic color palette cycling).
    - Manages bi-directional synchronized X-axis panning/zooming via plotly_relayout event listeners.

## 4. Key Engineering Patterns & Decisions

Concurrency Control in WASM
 - Sequential Loading (for...of): Because h5wasm operates within a single-threaded WebAssembly memory space, executing parallel reads (Promise.all) across multiple dataset handles causes file pointer collisions. All bulk sweep reading is executed sequentially to ensure stability.

UI Responsiveness & Paint Cycles
 - Render-Yielding: Heavy asynchronous loops are preceded by await new Promise(resolve => requestAnimationFrame(resolve));. This forces the browser event loop to paint the loading indicator frame before heavy WebAssembly data processing blocks the main JS thread.