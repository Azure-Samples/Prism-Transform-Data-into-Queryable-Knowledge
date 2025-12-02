// Azure AI Search Service
// Provides: Vector search, hybrid search, semantic ranking for RAG

@description('Location for resources')
param location string

@description('Tags to apply to resources')
param tags object = {}

@description('Name of the search service')
param name string

@description('SKU for the search service')
@allowed([
  'free'
  'basic'
  'standard'
  'standard2'
  'standard3'
  'storage_optimized_l1'
  'storage_optimized_l2'
])
param sku string = 'basic'

@description('Semantic search tier')
@allowed([
  'disabled'
  'free'
  'standard'
])
param semanticSearch string = 'standard'

@description('Number of replicas')
@minValue(1)
@maxValue(12)
param replicaCount int = 1

@description('Number of partitions')
@allowed([1, 2, 3, 4, 6, 12])
param partitionCount int = 1

@description('Hosting mode')
@allowed([
  'default'
  'highDensity'
])
param hostingMode string = 'default'

// ============================================================================
// Search Service
// ============================================================================

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: sku
  }
  properties: {
    replicaCount: replicaCount
    partitionCount: partitionCount
    hostingMode: hostingMode
    semanticSearch: semanticSearch
    publicNetworkAccess: 'enabled'
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
}

// ============================================================================
// Outputs
// ============================================================================

output id string = searchService.id
output name string = searchService.name
output endpoint string = 'https://${searchService.name}.search.windows.net'
output adminKey string = searchService.listAdminKeys().primaryKey
output principalId string = searchService.identity.principalId
