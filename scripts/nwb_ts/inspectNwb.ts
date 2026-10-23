// scripts/nwb_ts/inspectNwb.ts
import { DandiClient } from './dandiClient';

async function main() {
  const client = new DandiClient();
  const dandisetId = '001261';
  const version = '0.250917.2023';

  try {
    console.log('1. Fetching asset list from DANDI...');
    const assetsResponse = await client.getAssets(dandisetId, version, 1, 5);
    
    if (assetsResponse.results.length === 0) {
      console.log('No assets found.');
      return;
    }

    const targetAsset = assetsResponse.results[0];
    console.log(`Target File: ${targetAsset.path}`);
    console.log(`File Size: ${(targetAsset.size / (1024 * 1024)).toFixed(2)} MB`);

    console.log('2. Resolving direct download URL...');
    const downloadUrl = await client.getAssetDownloadUrl(targetAsset.asset_id);

    console.log('3. Downloading NWB binary payload into memory...');
    const fileResponse = await fetch(downloadUrl);
    if (!fileResponse.ok) {
      throw new Error(`Failed to download file: ${fileResponse.statusText}`);
    }
    const arrayBuffer = await fileResponse.arrayBuffer();
    const uint8Array = new Uint8Array(arrayBuffer);
    console.log(`Downloaded ${uint8Array.length} bytes.`);

    console.log('4. Dynamically loading h5wasm for Node.js environment...');
    // @ts-ignore
    const h5wasmModule = await import('h5wasm/node');
    const h5wasm = h5wasmModule.default;

    // Await ready to initialize the Emscripten filesystem (FS)
    const { FS } = await h5wasm.ready;

    const fileName = 'temp_dataset.nwb';
    FS.writeFile(fileName, uint8Array);

    console.log('5. Opening HDF5 / NWB file structure...');
    // Access the File constructor directly from h5wasm namespace
    const f = new h5wasm.File(fileName, 'r');

    console.log('\n--- NWB Root Groups & Contents ---');
    const rootKeys = f.keys();
    console.log('Top-level keys:', rootKeys);

    if (rootKeys.includes('acquisition')) {
      const acquisitionGroup = f.get('acquisition');
      console.log('\nContents of /acquisition group:', acquisitionGroup.keys());
    }

    if (rootKeys.includes('general')) {
      const generalGroup = f.get('general');
      console.log('Contents of /general group:', generalGroup.keys());
    }

    f.close();
    FS.unlink(fileName);
    console.log('\nSuccessfully inspected NWB structure natively in TypeScript!');

  } catch (error) {
    console.error('Error inspecting NWB file:', error);
  }
}

main();
