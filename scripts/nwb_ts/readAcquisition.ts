// scripts/nwb_ts/readAcquisition.ts
import { DandiClient } from './dandiClient';

async function main() {
  const client = new DandiClient();
  const dandisetId = '001261';
  const version = '0.250917.2023';

  try {
    console.log('1. Fetching asset list & downloading NWB file...');
    const assetsResponse = await client.getAssets(dandisetId, version, 1, 5);
    const targetAsset = assetsResponse.results[0];
    const downloadUrl = await client.getAssetDownloadUrl(targetAsset.asset_id);

    const fileResponse = await fetch(downloadUrl);
    const arrayBuffer = await fileResponse.arrayBuffer();
    const uint8Array = new Uint8Array(arrayBuffer);

    console.log('2. Initializing h5wasm and mounting file...');
    // @ts-ignore
    const h5wasmModule = await import('h5wasm/node');
    const h5wasm = h5wasmModule.default;
    const { FS } = await h5wasm.ready;

    const fileName = 'temp_dataset.nwb';
    FS.writeFile(fileName, uint8Array);

    const f = new h5wasm.File(fileName, 'r');

    console.log('\n3. Inspecting /acquisition/constant_response_001...');
    const tracePath = 'acquisition/constant_response_001';
    
    // Check if the group exists
    if (!f.keys().includes('acquisition')) {
      console.error('Acquisition group not found in file!');
      f.close();
      return;
    }

    const acquisitionGroup = f.get('acquisition');
    const traceKeys = acquisitionGroup.keys();
    console.log(`Found ${traceKeys.length} acquisition traces.`);

    const targetTraceName = 'constant_response_001';
    const traceObj = acquisitionGroup.get(targetTraceName);

    console.log(`\n--- Contents of /acquisition/${targetTraceName} ---`);
    // In NWB, a TimeSeries or PatchClampSeries is typically an HDF5 Group 
    // containing datasets like 'data', 'timestamps' (or 'starting_time'), and attributes.
    if (traceObj && typeof traceObj.keys === 'function') {
      const subKeys = traceObj.keys();
      console.log('Datasets/Groups inside trace:', subKeys);

      // Let's inspect the 'data' dataset if it exists
      if (subKeys.includes('data')) {
        const dataDataset = traceObj.get('data');
        console.log('\nDataset "data" metadata:');
        console.log('  Shape:', dataDataset.shape);
        console.log('  Type:', dataDataset.type);

        // Read the actual numerical values into a typed array via .value
        const rawValues = dataDataset.value;
        console.log('  Data length:', rawValues.length);
        console.log('  First 10 data points:', rawValues.slice(0, 10));

        // Check if there are attributes like 'unit' or 'conversion'
        if (dataDataset.attrs) {
          console.log('  Dataset attributes:', dataDataset.attrs);
        }
      }

      // Check for timestamps or starting_time
      if (subKeys.includes('timestamps')) {
        const tsDataset = traceObj.get('timestamps');
        console.log('\nDataset "timestamps" shape:', tsDataset.shape);
        console.log('First 5 timestamps:', tsDataset.value.slice(0, 5));
      } else if (subKeys.includes('starting_time')) {
        const stDataset = traceObj.get('starting_time');
        console.log('\nStarting time value:', stDataset.value);
      }
    }

    f.close();
    FS.unlink(fileName);
    console.log('\nSuccessfully extracted numerical time-series data from NWB natively in TS!');

  } catch (error) {
    console.error('Error reading acquisition data:', error);
  }
}

main();
