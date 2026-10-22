targetScope = 'resourceGroup'

@description('Azure region for the Container Apps environment and app.')
param location string = resourceGroup().location

@description('Unique Container Apps environment name in this resource group.')
param environmentName string = 'pulse-xi-demo-env'

@description('Container App name. Use a dedicated resource group for this demo.')
param appName string = 'pulse-xi-demo'

@description('Public, immutable container image reference. Do not include credentials.')
param image string

@description('Unique suffix for this immutable application revision.')
@minLength(1)
@maxLength(64)
param revisionSuffix string = 'initial'

@description('Non-sensitive resource ownership tags.')
param tags object = {
  application: 'pulse-xi'
  purpose: 'public-demo'
  managedBy: 'bicep'
}

resource environment 'Microsoft.App/managedEnvironments@2025-07-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'none'
    }
    zoneRedundant: false
  }
}

resource app 'Microsoft.App/containerApps@2025-07-01' = {
  name: appName
  location: location
  tags: tags
  properties: {
    environmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
        allowInsecure: false
      }
    }
    template: {
      revisionSuffix: revisionSuffix
      containers: [
        {
          name: 'pulse-xi'
          image: image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'PORT', value: '8080' }
            { name: 'PULSE_DEPLOYMENT_MODE', value: 'public-readonly' }
            { name: 'PULSE_RUNTIME_DRIVER', value: '0' }
            { name: 'PULSE_DB_PATH', value: '/tmp/pulse-xi/imported.sqlite' }
            { name: 'PULSE_RUNTIME_DB_PATH', value: '/tmp/pulse-xi/runtime.sqlite' }
            { name: 'PULSE_ENABLE_FOUNDRY', value: 'false' }
          ]
          probes: [
            {
              type: 'Startup'
              httpGet: { path: '/ready', port: 8080, scheme: 'HTTP' }
              initialDelaySeconds: 2
              periodSeconds: 5
              timeoutSeconds: 3
              failureThreshold: 10
            }
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8080, scheme: 'HTTP' }
              periodSeconds: 10
              timeoutSeconds: 3
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: { path: '/ready', port: 8080, scheme: 'HTTP' }
              periodSeconds: 5
              timeoutSeconds: 3
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

output appName string = app.name
output environmentName string = environment.name
output fqdn string = app.properties.configuration.ingress.fqdn
