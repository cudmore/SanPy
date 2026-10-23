// src/services/nwbService.ts
import { DandiClient } from '../../dandiClient';

export interface SweepTimeSeries {
  name: string;
  time: number[];
  data: number[];
  unit: string;
}

interface AssetCacheEntry {
  file: any;
  sweepNames: { acquisition: string[]; stimulus: string[] };
  traces: Map<string, SweepTimeSeries | null>;
  bulk: { responses: SweepTimeSeries[]; stimuli: SweepTimeSeries[] } | null;
}

export class NwbWebService {
  private dandiClient = new DandiClient();
  private h5wasmInstance: any = null;

  // Multi-asset cache map (assetUuid -> AssetCacheEntry)
  private assetCache = new Map<string, AssetCacheEntry>();
  private activeAssetUuid: string | null = null;

  private async getH5Wasm() {
    if (!this.h5wasmInstance) {
      // @ts-ignore
      const h5wasmModule = await import('h5wasm');
      const h5wasm = h5wasmModule.default || h5wasmModule;
      await h5wasm.ready;
      this.h5wasmInstance = h5wasm;
    }
    return this.h5wasmInstance;
  }

  async fetchAssetOverview(dandisetId: string, version: string) {
    let allResults: any[] = [];
    let page = 1;
    const pageSize = 100;

    while (true) {
      const response = await this.dandiClient.getAssets(dandisetId, version, page, pageSize);
      if (!response || !response.results || response.results.length === 0) {
        break;
      }
      allResults = allResults.concat(response.results);
      if (allResults.length >= response.count || response.results.length < pageSize || !response.next) {
        break;
      }
      page++;
    }

    return allResults.map(asset => ({
      assetId: asset.asset_id,
      path: asset.path,
      sizeMB: Number((asset.size / (1024 * 1024)).toFixed(2)),
    }));
  }

  /**
   * Ensure an asset is downloaded and cached permanently in memory (Multi-asset cache)
   */
  private async ensureAssetLoaded(assetUuid: string): Promise<AssetCacheEntry> {
    this.activeAssetUuid = assetUuid;

    if (this.assetCache.has(assetUuid)) {
      return this.assetCache.get(assetUuid)!; // Instant return for previously visited asset!
    }

    const downloadUrl = await this.dandiClient.getAssetDownloadUrl(assetUuid);
    const res = await fetch(downloadUrl);
    const buffer = await res.arrayBuffer();
    
    const h5wasm = await this.getH5Wasm();
    const { FS } = await h5wasm.ready;
    
    const fileName = `asset_${assetUuid}.nwb`;
    try {
      FS.unlink(fileName);
    } catch (e) {}

    FS.writeFile(fileName, new Uint8Array(buffer));
    
    const file = new h5wasm.File(fileName, 'r');
    
    const acquisition = file.keys().includes('acquisition') ? file.get('acquisition').keys() : [];
    
    let stimulus: string[] = [];
    if (file.keys().includes('stimulus')) {
      const stimGroup = file.get('stimulus');
      if (stimGroup.keys().includes('presentation')) {
        stimulus = stimGroup.get('presentation').keys();
      } else {
        stimulus = stimGroup.keys();
      }
    }

    const entry: AssetCacheEntry = {
      file,
      sweepNames: { acquisition, stimulus },
      traces: new Map(),
      bulk: null,
    };

    this.assetCache.set(assetUuid, entry);
    return entry;
  }

  async getSweepNames(assetUuid: string): Promise<{ acquisition: string[]; stimulus: string[] }> {
    const entry = await this.ensureAssetLoaded(assetUuid);
    return entry.sweepNames;
  }

  async getTraceData(assetUuid: string, groupName: 'acquisition' | 'stimulus', traceName: string): Promise<SweepTimeSeries | null> {
    const entry = await this.ensureAssetLoaded(assetUuid);
    const cacheKey = `${groupName}:${traceName}`;
    
    if (entry.traces.has(cacheKey)) {
      return entry.traces.get(cacheKey)!;
    }

    try {
      if (!entry.file.keys().includes(groupName)) {
        entry.traces.set(cacheKey, null);
        return null;
      }

      let group = entry.file.get(groupName);
      if (groupName === 'stimulus' && group.keys().includes('presentation')) {
        group = group.get('presentation');
      }

      if (!group.keys().includes(traceName)) {
        entry.traces.set(cacheKey, null);
        return null;
      }

      const traceObj = group.get(traceName);
      const dataDataset = traceObj.get('data');
      if (!dataDataset || !dataDataset.value) {
        entry.traces.set(cacheKey, null);
        return null;
      }

      const dataValues = Array.from(dataDataset.value as Float32Array);
      
      let rawUnit = dataDataset.attrs?.unit || traceObj.attrs?.unit;
      let unit = 'a.u.';
      if (typeof rawUnit === 'string') {
        unit = rawUnit;
      } else if (rawUnit) {
        unit = String((rawUnit as any).value || rawUnit);
      }

      let timeValues: number[] = [];
      const traceKeys = traceObj.keys();

      if (traceKeys.includes('timestamps')) {
        timeValues = Array.from(traceObj.get('timestamps').value as Float32Array);
      } else {
        let startingTime = 0;
        if (traceKeys.includes('starting_time')) {
          startingTime = Number(traceObj.get('starting_time').value);
        } else if (traceObj.attrs?.starting_time !== undefined) {
          startingTime = Number(traceObj.attrs.starting_time);
        }

        let rate = 20000;
        if (traceKeys.includes('rate')) {
          rate = Number(traceObj.get('rate').value);
        } else if (traceObj.attrs?.rate !== undefined) {
          rate = Number(traceObj.attrs.rate);
        }

        const dt = 1.0 / rate;
        timeValues = Array.from({ length: dataValues.length }, (_, i) => startingTime + i * dt);
      }

      const result: SweepTimeSeries = {
        name: traceName,
        time: timeValues,
        data: dataValues,
        unit,
      };

      entry.traces.set(cacheKey, result);
      return result;
    } catch (err) {
      console.warn(`Could not read ${groupName}/${traceName}:`, err);
      entry.traces.set(cacheKey, null);
      return null;
    }
  }

  async getAllTraces(assetUuid: string): Promise<{ responses: SweepTimeSeries[]; stimuli: SweepTimeSeries[] }> {
    const entry = await this.ensureAssetLoaded(assetUuid);

    if (entry.bulk) {
      return entry.bulk; // Instant return from per-asset bulk cache!
    }

    const responses: SweepTimeSeries[] = [];
    for (const name of entry.sweepNames.acquisition) {
      const trace = await this.getTraceData(assetUuid, 'acquisition', name);
      if (trace) responses.push(trace);
    }

    const stimuli: SweepTimeSeries[] = [];
    for (let idx = 0; idx < entry.sweepNames.acquisition.length; idx++) {
      const acqName = entry.sweepNames.acquisition[idx];
      const stimName = entry.sweepNames.stimulus[idx] || entry.sweepNames.stimulus.find(s => s === acqName) || entry.sweepNames.stimulus[0];
      if (stimName) {
        const trace = await this.getTraceData(assetUuid, 'stimulus', stimName);
        if (trace) stimuli.push(trace);
      }
    }

    entry.bulk = { responses, stimuli };
    return entry.bulk;
  }
}
