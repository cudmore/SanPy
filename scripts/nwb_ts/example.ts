// scripts/nwb_ts/example.ts
import { DandiClient } from './dandiClient';

async function main() {
  const client = new DandiClient();
  const dandisetId = '001261';
  const version = '0.250917.2023'; // Explicitly set the published version

  try {
    console.log(`========================================`);
    console.log(`Fetching Overview for Dandiset ${dandisetId} (${version})`);
    console.log(`========================================\n`);

    // 1. Fetch Dandiset Metadata
    const dandiset = await client.getDandiset(dandisetId);
    console.log(`Dandiset Identifier: ${dandiset.identifier}`);
    console.log(`Created: ${dandiset.created}`);
    console.log(`Modified: ${dandiset.modified}\n`);

    // 2. Query Assets for this specific version
    console.log(`Querying assets for version '${version}'...`);
    const assetsResponse = await client.getAssets(dandisetId, version, 1, 20);
    console.log(`Total Assets in this version: ${assetsResponse.count}\n`);

    if (assetsResponse.results.length === 0) {
      console.log('No assets found for this version.');
      return;
    }

    // 3. Display an overview table of the first few files
    console.log(`--- First ${assetsResponse.results.length} Asset Files ---`);
    for (const [index, asset] of assetsResponse.results.entries()) {
      const sizeMB = (asset.size / (1024 * 1024)).toFixed(2);
      console.log(`\n[${index + 1}] File Path: ${asset.path}`);
      console.log(`    Asset UUID: ${asset.asset_id}`);
      console.log(`    Size: ${sizeMB} MB`);
      console.log(`    Format: ${asset.encodingFormat || 'Unknown'}`);
    }

    // 4. Resolve a download URL for the first asset to verify link generation
    const firstAsset = assetsResponse.results[0];
    console.log(`\n----------------------------------------`);
    console.log(`Resolving streaming download URL for first asset:`);
    const downloadUrl = await client.getAssetDownloadUrl(firstAsset.asset_id);
    console.log(`${downloadUrl}`);
    console.log(`----------------------------------------`);

  } catch (error) {
    console.error('Error fetching data from DANDI:', error);
  }
}

main();
