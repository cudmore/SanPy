// dandiTypes.ts

export interface DandiPaginatedResponse<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
  }
  
  export interface DandisetVersionInfo {
    version: string;
    name: string;
    created: string;
    modified: string;
    status: string;
    asset_count: number;
    size: number;
  }
  
  export interface DandisetInfo {
    identifier: string;
    created: string;
    modified: string;
    most_recent_published_version?: DandisetVersionInfo;
    draft_version: DandisetVersionInfo;
  }
  
  export interface DandiAsset {
    asset_id: string; // The UUID
    path: string; // Internal file path e.g. "sub-01/sub-01_ecephys.nwb"
    size: number; // File size in bytes
    created: string;
    modified: string;
    encodingFormat?: string; // e.g. "application/x-nwb" or "application/x-zarr"
    digest?: Record<string, string>;
    // Present when retrieving detailed asset info or extracted from metadata:
    blob?: string;
    zarr?: string;
  }
  
  export interface DandiAssetDetail extends DandiAsset {
    metadata?: Record<string, unknown>;
    contentUrl?: string[]; // Array containing direct AWS S3 / HTTP streaming links
  }
  