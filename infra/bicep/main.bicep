// Prism Infrastructure - Main Orchestrator
// Deploys: AI Foundry + Azure AI Search + Container Apps
// Usage: azd up

targetScope = 'subscription'

// ============================================================================
// Parameters
// ============================================================================

@minLength(1)
@maxLength(64)
@description('Name of the environment (e.g., dev, staging, prod)')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
@allowed([
  'australiaeast'
  'brazilsouth'
  'canadacentral'
  'canadaeast'
  'eastus'
  'eastus2'
  'francecentral'
  'germanywestcentral'
  'japaneast'
  'koreacentral'
  'northcentralus'
  'norwayeast'
  'polandcentral'
  'southafricanorth'
  'southcentralus'
  'southindia'
  'swedencentral'
  'switzerlandnorth'
  'uksouth'
  'westeurope'
  'westus'
  'westus3'
])
param location string

@description('Name of the resource group')
param resourceGroupName string = ''

@description('Principal ID of the user running the deployment')
param principalId string = ''

@description('Chat model deployment name (for Knowledge Agents/agentic retrieval)')
param chatDeploymentName string = 'gpt-4.1'

@description('Chat model name')
param chatModelName string = 'gpt-4.1'

@description('Chat deployment capacity (TPM in thousands)')
param chatCapacity int = 30

@description('Workflow model deployment name (for workflow Q&A - supports newer models)')
param workflowDeploymentName string = 'gpt-5-chat'

@description('Workflow model name')
param workflowModelName string = 'gpt-5-chat'

@description('Workflow deployment capacity (TPM in thousands)')
param workflowCapacity int = 50

@description('Text embedding model deployment name')
param embeddingDeploymentName string = 'text-embedding-3-large'

@description('Text embedding model name')
param embeddingModelName string = 'text-embedding-3-large'

@description('Embedding deployment capacity (TPM in thousands)')
param embeddingCapacity int = 120

@description('Deploy Container Apps for hosting')
param deployContainerApps bool = true

@description('Auth password for the application (auto-generated if not provided)')
@secure()
param authPassword string = ''

// ============================================================================
// Variables
// ============================================================================

var abbrs = loadJsonContent('abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
// Generate a password if none provided
var effectiveAuthPassword = !empty(authPassword) ? authPassword : 'Prism${uniqueString(subscription().id, environmentName, 'auth')}!'
var tags = {
  'azd-env-name': environmentName
  'application': 'prism'
}

// Resource group name
var rgName = !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}prism-${environmentName}'

// AI Foundry model deployments configuration
var modelDeployments = [
  {
    name: chatDeploymentName
    model: {
      format: 'OpenAI'
      name: chatModelName
    }
    sku: {
      name: 'GlobalStandard'
      capacity: chatCapacity
    }
  }
  {
    name: workflowDeploymentName
    model: {
      format: 'OpenAI'
      name: workflowModelName
    }
    sku: {
      name: 'GlobalStandard'
      capacity: workflowCapacity
    }
  }
  {
    name: embeddingDeploymentName
    model: {
      format: 'OpenAI'
      name: embeddingModelName
    }
    sku: {
      name: 'Standard'
      capacity: embeddingCapacity
    }
  }
]

// ============================================================================
// Resource Group
// ============================================================================

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
  tags: tags
}

// ============================================================================
// Monitoring (Log Analytics + App Insights)
// ============================================================================

module monitoring 'core/monitor/monitoring.bicep' = {
  name: 'monitoring'
  scope: rg
  params: {
    location: location
    tags: tags
    logAnalyticsName: '${abbrs.operationalInsightsWorkspaces}prism-${resourceToken}'
    applicationInsightsName: '${abbrs.insightsComponents}prism-${resourceToken}'
  }
}

// ============================================================================
// AI Foundry (Cognitive Services Account + Project)
// ============================================================================

module aiFoundry 'core/ai/ai-foundry.bicep' = {
  name: 'ai-foundry'
  scope: rg
  params: {
    location: location
    tags: tags
    accountName: '${abbrs.cognitiveServicesAccounts}prism-${resourceToken}'
    projectName: 'prism-project'
    modelDeployments: modelDeployments
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    applicationInsightsId: monitoring.outputs.applicationInsightsId
    applicationInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString
  }
}

// ============================================================================
// Azure Storage (for project files persistence)
// ============================================================================

module storage 'core/storage/storage-account.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    location: location
    tags: tags
    name: '${abbrs.storageStorageAccounts}prism${resourceToken}'
    containerName: 'prism-projects'
  }
}

// ============================================================================
// Azure AI Search
// ============================================================================

module search 'core/search/search-services.bicep' = {
  name: 'search'
  scope: rg
  params: {
    location: location
    tags: tags
    name: '${abbrs.searchSearchServices}prism-${resourceToken}'
    sku: 'basic'
    semanticSearch: 'standard'
  }
}

// ============================================================================
// AI Foundry Connection to Search
// ============================================================================

module searchConnection 'core/ai/connection.bicep' = {
  name: 'search-connection'
  scope: rg
  params: {
    accountName: aiFoundry.outputs.accountName
    projectName: aiFoundry.outputs.projectName
    connectionName: 'prism-search'
    connectionCategory: 'CognitiveSearch'
    connectionTarget: search.outputs.endpoint
    connectionApiKey: search.outputs.adminKey
  }
}

// ============================================================================
// Container Apps (Optional)
// ============================================================================

module containerApps 'core/host/container-apps.bicep' = if (deployContainerApps) {
  name: 'container-apps'
  scope: rg
  params: {
    location: location
    tags: tags
    environmentName: '${abbrs.appManagedEnvironments}prism-${resourceToken}'
    registryName: '${abbrs.containerRegistryRegistries}prism${resourceToken}'
    backendAppName: 'prism-backend'
    frontendAppName: 'prism-frontend'
    // Pass AI service configuration
    aiServicesEndpoint: aiFoundry.outputs.endpoint
    aiServicesKey: aiFoundry.outputs.key
    chatDeploymentName: chatDeploymentName
    workflowDeploymentName: workflowDeploymentName
    embeddingDeploymentName: embeddingDeploymentName
    // Pass Search configuration
    searchEndpoint: search.outputs.endpoint
    searchAdminKey: search.outputs.adminKey
    // Auth
    authPassword: effectiveAuthPassword
    // Monitoring
    applicationInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString
    // Storage (RBAC - no keys, uses managed identity)
    storageAccountName: storage.outputs.name
    storageBlobEndpoint: storage.outputs.primaryEndpoint
    storageContainerName: storage.outputs.containerName
    storageAccountId: storage.outputs.id
  }
}

// ============================================================================
// Role Assignments (for user running deployment)
// ============================================================================

module userRoleAssignments 'core/ai/role-assignments.bicep' = if (!empty(principalId)) {
  name: 'user-role-assignments'
  scope: rg
  params: {
    principalId: principalId
    aiServicesAccountName: aiFoundry.outputs.accountName
    searchServiceName: search.outputs.name
  }
}

// ============================================================================
// Storage Role Assignment (for Container App Managed Identity)
// ============================================================================

module storageRoleAssignment 'core/storage/storage-role-assignment.bicep' = if (deployContainerApps) {
  name: 'storage-role-assignment'
  scope: rg
  params: {
    storageAccountName: storage.outputs.name
    storageAccountId: storage.outputs.id
    principalId: containerApps.outputs.backendPrincipalId
  }
  dependsOn: [
    containerApps
    storage
  ]
}

// ============================================================================
// Outputs
// ============================================================================

// Resource Group
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_LOCATION string = location

// AI Foundry
output AZURE_AI_SERVICES_ENDPOINT string = aiFoundry.outputs.endpoint
output AZURE_AI_PROJECT_NAME string = aiFoundry.outputs.projectName
output AZURE_OPENAI_ENDPOINT string = aiFoundry.outputs.endpoint
#disable-next-line outputs-should-not-contain-secrets
output AZURE_OPENAI_KEY string = aiFoundry.outputs.key
output AZURE_OPENAI_CHAT_DEPLOYMENT_NAME string = chatDeploymentName
output AZURE_OPENAI_WORKFLOW_DEPLOYMENT_NAME string = workflowDeploymentName
output AZURE_OPENAI_MODEL_NAME string = chatModelName
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME string = embeddingDeploymentName
output AZURE_OPENAI_API_VERSION string = '2025-01-01-preview'

// Search
output AZURE_SEARCH_ENDPOINT string = search.outputs.endpoint
output AZURE_SEARCH_SERVICE_NAME string = search.outputs.name
#disable-next-line outputs-should-not-contain-secrets
output AZURE_SEARCH_ADMIN_KEY string = search.outputs.adminKey

// Container Apps (conditional)
#disable-next-line BCP318
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = deployContainerApps ? containerApps.outputs.registryLoginServer : ''
#disable-next-line BCP318
output BACKEND_URL string = deployContainerApps ? containerApps.outputs.backendUrl : ''
#disable-next-line BCP318
output FRONTEND_URL string = deployContainerApps ? containerApps.outputs.frontendUrl : ''

// Monitoring
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.applicationInsightsConnectionString

// Auth (output the effective password so user knows it)
#disable-next-line outputs-should-not-contain-secrets
output AUTH_PASSWORD string = effectiveAuthPassword

// Storage (RBAC only - no keys)
output AZURE_STORAGE_ACCOUNT_NAME string = storage.outputs.name
output AZURE_STORAGE_ACCOUNT_URL string = storage.outputs.primaryEndpoint
output AZURE_STORAGE_CONTAINER_NAME string = storage.outputs.containerName
