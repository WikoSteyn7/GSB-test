output "identityPrincipalId" {
  description = "The Principal ID for the Service Principal associated with the Managed Service Identity of this App Service"
  value = var.managedIdentity ? azurerm_linux_web_app.app_service.identity.0.principal_id : ""
}

output "appServiceName" {
  description = "The name of the app service"
  value = azurerm_linux_web_app.app_service.name
}

output "plan_name" {
  description = "The name of the plan"
  value = azurerm_service_plan.appServicePlan.name
}

output "appServiceId" {
  description = "The ID of the app service"
  value = azurerm_linux_web_app.app_service.id
}

output "appServiceUri" {
  description = "The URI of the app service"
  value = "https://${azurerm_linux_web_app.app_service.default_hostname}"
}

output "fdEndpointName" {
  description = "The name of the front door endpoint"
  value = azurerm_frontdoor.front_door.endpoint
}

output "appServiceplanName" {
  description = "The app service plan name"
  value = azurerm_service_plan.appServicePlan.name
}

output "appServiceplanId" {
  description = "The app service plan id"
  value = azurerm_service_plan.appServicePlan.id
}