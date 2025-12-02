// AI Foundry Connection
// Creates a connection from AI Foundry project to external services (e.g., Azure AI Search)

@description('Name of the Cognitive Services account')
param accountName string

@description('Name of the AI Foundry project')
param projectName string

@description('Name for the connection')
param connectionName string

@description('Category of the connection')
@allowed([
  'CognitiveSearch'
  'CognitiveService'
  'AzureBlob'
  'AzureOpenAI'
  'ApiKey'
  'CustomKeys'
])
param connectionCategory string

@description('Target endpoint URL')
param connectionTarget string

@description('API key for the connection')
@secure()
param connectionApiKey string = ''

// ============================================================================
// Reference existing AI Services Account and Project
// ============================================================================

resource aiServicesAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: accountName
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' existing = {
  parent: aiServicesAccount
  name: projectName
}

// ============================================================================
// Connection Resource
// ============================================================================

resource connection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: aiProject
  name: connectionName
  properties: {
    category: connectionCategory
    target: connectionTarget
    authType: !empty(connectionApiKey) ? 'ApiKey' : 'AAD'
    credentials: !empty(connectionApiKey) ? {
      key: connectionApiKey
    } : null
  }
}

// ============================================================================
// Outputs
// ============================================================================

output connectionName string = connection.name
output connectionId string = connection.id
