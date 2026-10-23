// dandiClient.ts
import { DandiAsset, DandiAssetDetail, DandiPaginatedResponse, DandisetInfo } from './dandiTypes';

export class DandiClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'https://api.dandiarchive.org/api') {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  private async fetchJson<T>(endpoint: string): Promise<T> {
    const url = `${this.baseUrl}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`DANDI API Error (${response.status}): ${response.statusText} at ${url}`);
    }

    return response.json() as Promise<T>;
  }

  /**
   * Fetch details for a specific Dandiset ID (e.g., "001261")
   */
  async getDandiset(dandisetId: string): Promise<DandisetInfo> {
    return this.fetchJson<DandisetInfo>(`/dandisets/${dandisetId}/`);
  }

  /**
   * List assets within a Dandiset for a given version ('draft' or specific version like '0.250917.2023')
   */
  async getAssets(
    dandisetId: string,
    version: string = 'draft',
    page: number = 1,
    pageSize: number = 50
  ): Promise<DandiPaginatedResponse<DandiAsset>> {
    const endpoint = `/dandisets/${dandisetId}/versions/${version}/assets/?page=${page}&page_size=${pageSize}`;
    return this.fetchJson<DandiPaginatedResponse<DandiAsset>>(endpoint);
  }

  /**
   * Get full details for a specific Asset by its UUID.
   */
  async getAssetDetail(assetUuid: string): Promise<DandiAssetDetail> {
    return this.fetchJson<DandiAssetDetail>(`/assets/${assetUuid}/`);
  }

  /**
   * Get direct download/streaming HTTP URLs for a given Asset UUID.
   */
  async getAssetDownloadUrl(assetUuid: string): Promise<string> {
    const detail = await this.getAssetDetail(assetUuid);
    
    // The DANDI API delivers S3 direct links in the contentUrl array
    if (detail.contentUrl && detail.contentUrl.length > 0) {
      return detail.contentUrl[0];
    }
    
    // Fallback: Construct redirect download endpoint directly
    return `${this.baseUrl}/assets/${assetUuid}/download/`;
  }
}
