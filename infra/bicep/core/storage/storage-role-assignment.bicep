// Storage Role Assignment for Container App Managed Identity
// Assigns Storage Blob Data Contributor role to allow blob operations

@description('Storage account name')
param storageAccountName string

@description('Storage account resource ID')
param storageAccountId string

@description('Principal ID of the managed identity (from Container App)')
param principalId string

// Storage Blob Data Contributor role
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

// Reference existing storage account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

// Assign role to the managed identity
// Use the same GUID formula as the original container-apps.bicep for idempotency
resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountId, principalId, storageBlobDataContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
