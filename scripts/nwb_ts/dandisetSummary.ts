// scripts/nwb_ts/dandisetSummary.ts
import { DandiClient } from './dandiClient';

export interface AcquisitionTraceSummary {
  traceName: string;
  shape: number[] | null;
  dataType: string;
}

export interface AssetAcquisitionSummary {
  assetId: string;
  filePath: string;
  fileSizeMB: number;
  acquisitionTraces: AcquisitionTraceSummary[];
}

export async function getDandisetAcquisitionOverview(
  dandisetId: string,
  version: string,
  maxAssets: number = 10
): Promise<AssetAcquisitionSummary[]> {
  const client = new DandiClient();
  
  console.log(`Fetching asset list for Dandiset ${dandisetId} (${version})...`);
  const assetsResponse = await client.getAssets(dandisetId, version, 1, maxAssets);
  
  if (!assetsResponse.results || assetsResponse.results.length === 0) {
    console.log('No assets found.');
    return [];
  }

  // Dynamically load h5wasm for Node.js environment
  // @ts-ignore
  const h5wasmModule = await import('h5wasm/node');
  const h5wasm = h5wasmModule.default;
  const { FS } = await h5wasm.ready;

  const overviewResults: AssetAcquisitionSummary[] = [];

  for (const [index, asset] of assetsResponse.results.entries()) {
    const sizeMB = Number((asset.size / (1024 * 1024)).toFixed(2));
    console.log(`\n[${index + 1}/${assetsResponse.results.length}] Inspecting: ${asset.path} (${sizeMB} MB)...`);

    try {
      const downloadUrl = await client.getAssetDownloadUrl(asset.asset_id);
      const fileResponse = await fetch(downloadUrl);
      
      if (!fileResponse.ok) {
        console.warn(`  Failed to download asset ${asset.asset_id}: ${fileResponse.statusText}`);
        continue;
      }

      const arrayBuffer = await fileResponse.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);

      const fileName = `temp_${asset.asset_id}.nwb`;
      FS.writeFile(fileName, uint8Array);

      const f = new h5wasm.File(fileName, 'r');
      const rootKeys = f.keys();

      const traces: AcquisitionTraceSummary[] = [];

      if (rootKeys.includes('acquisition')) {
        const acquisitionGroup = f.get('acquisition');
        const traceNames = acquisitionGroup.keys();

        for (const tName of traceNames) {
          const traceObj = acquisitionGroup.get(tName);
          let shape: number[] | null = null;
          let dataType = 'unknown';

          if (traceObj && typeof traceObj.keys === 'function' && traceObj.keys().includes('data')) {
            const dataDataset = traceObj.get('data');
            shape = dataDataset.shape || null;
            dataType = dataDataset.type || 'unknown';
          }

          traces.push({
            traceName: tName,
            shape,
            dataType,
          });
        }
      }

      f.close();
      FS.unlink(fileName);

      overviewResults.push({
        assetId: asset.asset_id,
        filePath: asset.path,
        fileSizeMB: sizeMB,
        acquisitionTraces: traces,
      });

    } catch (err) {
      console.warn(`  Error parsing asset ${asset.path}:`, err);
    }
  }

  return overviewResults;
}

// Execution block for running via CLI
async function main() {
  const dandisetId = '001261';
  const version = '0.250917.2023';
  const limit = 10; // Keep low for fast testing, increase as needed

  console.log(`==================================================`);
  console.log(`Generating Dandiset Acquisition Summary (Limit: ${limit})`);
  console.log(`==================================================\n`);

  const summary = await getDandisetAcquisitionOverview(dandisetId, version, limit);

  console.log(`\n==================================================`);
  console.log(`SUMMARY TABLE DATA READY (${summary.length} assets processed)`);
  console.log(`==================================================\n`);

  for (const item of summary) {
    console.log(`File: ${item.filePath}`);
    console.log(`Asset UUID: ${item.assetId}`);
    console.log(`Size: ${item.fileSizeMB} MB`);
    console.log(`Total Acquisition Traces: ${item.acquisitionTraces.length}`);
    if (item.acquisitionTraces.length > 0) {
      console.log(`  Sample Trace [0] Name: ${item.acquisitionTraces[0].traceName}`);
      console.log(`  Sample Trace [0] Shape:`, item.acquisitionTraces[0].shape);
    }
    console.log(`--------------------------------------------------`);
  }
}

// Run main if executed directly via tsx
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
