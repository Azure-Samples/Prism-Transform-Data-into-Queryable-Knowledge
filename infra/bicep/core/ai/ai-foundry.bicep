// AI Foundry - Cognitive Services Account with Project
// Provides: Azure OpenAI models through AI Foundry unified experience

@description('Location for resources')
param location string

@description('Tags to apply to resources')
param tags object = {}

@description('Name of the Cognitive Services account')
param accountName string

@description('Name of the AI Foundry project')
param projectName string

@description('Model deployments configuration')
param modelDeployments array = []

@description('Log Analytics Workspace ID for diagnostics')
param logAnalyticsWorkspaceId string = ''

@description('Application Insights resource ID')
param applicationInsightsId string = ''

@description('SKU name for Cognitive Services')
param skuName string = 'S0'

// ============================================================================
// Cognitive Services Account (AI Foundry Hub)
// ============================================================================

resource aiServicesAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: accountName
  location: location
  tags: tags
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: skuName
  }
  properties: {
    customSubDomainName: accountName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

// ============================================================================
// AI Foundry Project
// ============================================================================

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiServicesAccount
  name: projectName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: projectName
    description: 'Prism Document Intelligence Project'
  }
}

// ============================================================================
// Model Deployments
// ============================================================================

@batchSize(1)
resource deployments 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = [for deployment in modelDeployments: {
  parent: aiServicesAccount
  name: deployment.name
  sku: deployment.sku
  properties: {
    model: deployment.model
    raiPolicyName: 'Microsoft.Default'
  }
}]

// ============================================================================
// Diagnostic Settings
// ============================================================================

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(logAnalyticsWorkspaceId)) {
  name: '${accountName}-diagnostics'
  scope: aiServicesAccount
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

// ============================================================================
// App Insights Connection (if provided)
// ============================================================================

resource appInsightsConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = if (!empty(applicationInsightsId)) {
  parent: aiProject
  name: 'appinsights'
  properties: {
    category: 'AppInsights'
    target: applicationInsightsId
    authType: 'AAD'
  }
}

// ============================================================================
// Outputs
// ============================================================================

output accountName string = aiServicesAccount.name
output accountId string = aiServicesAccount.id
output projectName string = aiProject.name
output projectId string = aiProject.id
output endpoint string = aiServicesAccount.properties.endpoint
output key string = aiServicesAccount.listKeys().key1
output principalId string = aiServicesAccount.identity.principalId
