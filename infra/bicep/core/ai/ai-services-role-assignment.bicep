// AI Services Role Assignment for Container App Managed Identity
// Assigns Cognitive Services OpenAI User role to allow OpenAI API calls

@description('AI Services account name')
param aiServicesAccountName string

@description('Principal ID of the managed identity (from Container App)')
param principalId string

// Cognitive Services OpenAI User - allows using OpenAI models
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

// Reference existing AI Services account
resource aiServicesAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aiServicesAccountName
}

// Assign Cognitive Services OpenAI User role to the managed identity
resource aiServicesRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesAccount.id, principalId, cognitiveServicesOpenAIUserRoleId)
  scope: aiServicesAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
