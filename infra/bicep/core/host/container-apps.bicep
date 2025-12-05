// Container Apps Environment with Backend and Frontend
// Provides: Hosting for Prism application

@description('Location for resources')
param location string

@description('Tags to apply to resources')
param tags object = {}

@description('Name of the Container Apps environment')
param environmentName string

@description('Name of the Container Registry')
param registryName string

@description('Name of the backend app')
param backendAppName string

@description('Name of the frontend app')
param frontendAppName string

// AI Services configuration
@description('Azure AI Services endpoint')
param aiServicesEndpoint string

@secure()
@description('Azure AI Services key')
param aiServicesKey string

@description('Chat model deployment name (for Knowledge Agents/agentic retrieval)')
param chatDeploymentName string

@description('Workflow model deployment name (for workflow Q&A - can use newer models)')
param workflowDeploymentName string = ''

@description('Embedding deployment name')
param embeddingDeploymentName string

// Search configuration
@description('Azure AI Search endpoint')
param searchEndpoint string

@secure()
@description('Azure AI Search admin key')
param searchAdminKey string

// Auth configuration
@secure()
@description('Application auth password')
param authPassword string

// Monitoring
@description('Application Insights connection string')
param applicationInsightsConnectionString string = ''

// Storage configuration (RBAC-based, no keys)
@description('Azure Storage account name')
param storageAccountName string = ''

@description('Azure Storage blob endpoint')
param storageBlobEndpoint string = ''

@description('Azure Storage container name')
param storageContainerName string = ''

@description('Azure Storage account resource ID (for role assignment)')
param storageAccountId string = ''

// ============================================================================
// Container Registry
// ============================================================================

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: registryName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
  }
}

// ============================================================================
// Log Analytics Workspace (for Container Apps)
// ============================================================================

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${environmentName}-logs'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// ============================================================================
// Container Apps Environment
// ============================================================================

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    daprAIConnectionString: applicationInsightsConnectionString
  }
}

// ============================================================================
// Backend Container App (with Managed Identity)
// ============================================================================

resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: backendAppName
  location: location
  tags: union(tags, {
    'azd-service-name': 'backend'
  })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
        }
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.listCredentials().username
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        {
          name: 'registry-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
        {
          name: 'ai-services-key'
          value: aiServicesKey
        }
        {
          name: 'search-admin-key'
          value: searchAdminKey
        }
        {
          name: 'auth-password'
          value: authPassword
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          // Placeholder image - will be replaced by azd deploy
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: aiServicesEndpoint
            }
            {
              name: 'AZURE_OPENAI_API_KEY'
              secretRef: 'ai-services-key'
            }
            {
              name: 'AZURE_OPENAI_CHAT_DEPLOYMENT_NAME'
              value: chatDeploymentName
            }
            {
              name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME'
              value: embeddingDeploymentName
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: '2025-01-01-preview'
            }
            {
              name: 'AZURE_OPENAI_MODEL_NAME'
              value: chatDeploymentName
            }
            {
              name: 'AZURE_OPENAI_WORKFLOW_DEPLOYMENT_NAME'
              value: !empty(workflowDeploymentName) ? workflowDeploymentName : chatDeploymentName
            }
            {
              name: 'AZURE_SEARCH_ENDPOINT'
              value: searchEndpoint
            }
            {
              name: 'AZURE_SEARCH_ADMIN_KEY'
              secretRef: 'search-admin-key'
            }
            {
              name: 'AUTH_PASSWORD'
              secretRef: 'auth-password'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: applicationInsightsConnectionString
            }
            {
              name: 'AZURE_STORAGE_ACCOUNT_NAME'
              value: storageAccountName
            }
            {
              name: 'AZURE_STORAGE_ACCOUNT_URL'
              value: storageBlobEndpoint
            }
            {
              name: 'AZURE_STORAGE_CONTAINER_NAME'
              value: storageContainerName
            }
            // No AZURE_STORAGE_ACCOUNT_KEY - uses managed identity
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

// ============================================================================
// Frontend Container App
// ============================================================================

resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: frontendAppName
  location: location
  tags: union(tags, {
    'azd-service-name': 'frontend'
  })
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 80
        transport: 'http'
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.listCredentials().username
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        {
          name: 'registry-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          // Placeholder image - will be replaced by azd deploy
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'BACKEND_URL'
              value: 'https://${backendApp.properties.configuration.ingress.fqdn}'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

// ============================================================================
// Outputs
// ============================================================================

output environmentId string = containerAppsEnvironment.id
output environmentName string = containerAppsEnvironment.name
output registryLoginServer string = containerRegistry.properties.loginServer
output registryName string = containerRegistry.name
output backendUrl string = 'https://${backendApp.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output backendAppName string = backendApp.name
output frontendAppName string = frontendApp.name
output backendPrincipalId string = backendApp.identity.principalId
