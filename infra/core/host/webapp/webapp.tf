
# Create the web app service plan
resource "azurerm_service_plan" "appServicePlan" {
  name                = var.plan_name
  location            = var.location
  resource_group_name = var.resourceGroupName

  sku_name = var.sku["size"]
  worker_count = var.sku["capacity"]
  os_type = "Linux"

  tags = var.tags
}

resource "azurerm_monitor_autoscale_setting" "scaleout" {
  name                = azurerm_service_plan.appServicePlan.name
  resource_group_name = var.resourceGroupName
  location            = var.location
  target_resource_id  = azurerm_service_plan.appServicePlan.id

  profile {
    name = "Scale out condition"
    capacity {
      default = 1
      minimum = 1
      maximum = 5
    }

    rule {
      metric_trigger {
        metric_name         = "CpuPercentage"
        metric_resource_id  = azurerm_service_plan.appServicePlan.id
        time_grain          = "PT1M"
        statistic           = "Average"
        time_window         = "PT5M"
        time_aggregation    = "Average"
        operator            = "GreaterThan"
        threshold           = 60
      }

      scale_action {
        direction = "Increase"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT5M"
      }
    }

    rule {
      metric_trigger {
        metric_name         = "CpuPercentage"
        metric_resource_id  = azurerm_service_plan.appServicePlan.id
        time_grain          = "PT1M"
        statistic           = "Average"
        time_window         = "PT10M"
        time_aggregation    = "Average"
        operator            = "LessThan"
        threshold           = 20
      }

      scale_action {
        direction = "Decrease"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT15M"
      }
    }
  }
}



# Create the web app service
resource "azurerm_linux_web_app" "app_service" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resourceGroupName
  service_plan_id = azurerm_service_plan.appServicePlan.id
  https_only          = true
  tags                = var.tags

  site_config {
    application_stack {
      python_version = var.runtimeVersion
    }
    always_on                      = var.alwaysOn
    ftps_state                     = var.ftpsState
    app_command_line               = var.appCommandLine
    health_check_path              = var.healthCheckPath
    cors {
      allowed_origins = concat([var.azure_portal_domain, "https://ms.portal.azure.com"], var.allowedOrigins)
    }
  }

  identity {
    type = var.managedIdentity ? "SystemAssigned" : "None"
  }
 
  app_settings = merge(
    var.appSettings,
    {
      "SCM_DO_BUILD_DURING_DEPLOYMENT" = lower(tostring(var.scmDoBuildDuringDeployment))
      "ENABLE_ORYX_BUILD"              = lower(tostring(var.enableOryxBuild))
      "APPLICATIONINSIGHTS_CONNECTION_STRING" = var.applicationInsightsConnectionString
      "AZURE_SEARCH_SERVICE_KEY" = "@Microsoft.KeyVault(SecretUri=${var.keyVaultUri}secrets/AZURE-SEARCH-SERVICE-KEY)"
      "COSMOSDB_KEY" = "@Microsoft.KeyVault(SecretUri=${var.keyVaultUri}secrets/COSMOSDB-KEY)"
      "AZURE_BLOB_STORAGE_KEY" = "@Microsoft.KeyVault(SecretUri=${var.keyVaultUri}secrets/AZURE-BLOB-STORAGE-KEY)"
      "ENRICHMENT_KEY" = "@Microsoft.KeyVault(SecretUri=${var.keyVaultUri}secrets/ENRICHMENT-KEY)"
      "AZURE_OPENAI_SERVICE_KEY" = "@Microsoft.KeyVault(SecretUri=${var.keyVaultUri}secrets/AZURE-OPENAI-SERVICE-KEY)"
    }
  )

  logs {
    application_logs {
      file_system_level = "Verbose"
    }
    http_logs {
      file_system {
        retention_in_days = 1
        retention_in_mb   = 35
      }
    }
  }

  auth_settings_v2 {
    auth_enabled = true
    default_provider = "azureactivedirectory"
    runtime_version = "~2"
    unauthenticated_action = "RedirectToLoginPage"
    require_https = true
    active_directory_v2{
      client_id = var.aadClientId
      login_parameters = {}
      tenant_auth_endpoint = "https://sts.windows.net/${var.tenantId}/v2.0"
      www_authentication_disabled  = false
      allowed_audiences = [
        "api://${var.name}"
      ]
    }
    login{
      token_store_enabled = false
    }
  }

}


// from secure-appservice
resource "azurerm_linux_web_app" "app_service" {
  count               = var.is_secure_mode? 1 : 0
  name                = var.name
  location            = var.location
  resource_group_name = var.resourceGroupName
  service_plan_id = azurerm_service_plan.appServicePlan.id
  https_only          = true
  public_network_access_enabled = false
  tags                = var.tags

  site_config {
    application_stack {
      python_version = var.runtimeVersion
    }
    always_on                      = var.alwaysOn
    ftps_state                     = "Disabled"
    app_command_line               = var.appCommandLine
    health_check_path              = var.healthCheckPath
    cors {
      allowed_origins = concat([var.azure_portal_domain, "https://ms.portal.azure.com"], var.allowedOrigins)
    }
  }

  identity {
    type = var.managedIdentity ? "SystemAssigned" : "None"
  }

  auth_settings {
    enabled  = true
    # Remove the 'active_directory_client_id' attribute
    issuer = "https://sts.windows.net/${var.tenantId}"
    runtime_version = "~1"
    token_store_enabled = true
    unauthenticated_client_action = "RedirectToLoginPage"
  }
}


resource "azurerm_cdn_profile" "front_door_profile" { 
  count               = var.is_secure_mode? 1 : 0
  name                = var.fdProfileName
  resource_group_name = var.resourceGroupName
  location            = "global"
  sku                 = "Premium_AzureFrontDoor"
}

resource "azurerm_cdn_endpoint" "front_door_endpoint" {
  count                        = var.is_secure_mode ? 1 : 0
  name                         = var.fdEndpointName
  profile_name                 = azurerm_cdn_profile.front_door_profile.name
  location                     = "global"
  resource_group_name          = var.resourceGroupName
  is_compression_enabled       = true
  is_http_allowed              = true
  is_https_allowed             = true
  querystring_caching_behaviour = "IgnoreQueryString"

  origin {
    name                = var.fdOriginName
    host_name           = azurerm_app_service.app_service.default_site_hostname
    http_port           = 80
    https_port          = 443
  }
}

resource "azurerm_cdn_origin_group" "front_door_origin_group" {
  count               = var.is_secure_mode ? 1 : 0
  name                = var.front_door_origin_group_name
  profile_name        = azurerm_cdn_profile.front_door_profile.name
  resource_group_name = var.resource_group_name

  load_balancing_sample_size = 4
  load_balancing_successful_samples_required = 3

  health_probe_path = "/"
  health_probe_request_type = "HEAD"
  health_probe_protocol = "Http"
  health_probe_interval_in_seconds = 100
}

resource "azurerm_cdn_origin" "front_door_origin" {
  count               = var.is_secure_mode ? 1 : 0
  name                = var.front_door_origin_name
  endpoint_name       = azurerm_cdn_endpoint.front_door_endpoint.name
  profile_name        = azurerm_cdn_profile.front_door_profile.name
  resource_group_name = var.resource_group_name
  host_name           = azurerm_app_service.app_service.default_site_hostname
  http_port           = 80
  https_port          = 443
  origin_group_id     = azurerm_cdn_origin_group.front_door_origin_group.id
}

resource "azurerm_cdn_route" "front_door_route" {
  count               = var.is_secure_mode ? 1 : 0
  name                = var.frontDoorRouteName
  endpoint_name       = azurerm_cdn_endpoint.front_door_endpoint.name
  profile_name        = azurerm_cdn_profile.front_door_profile.name
  resource_group_name = var.resourceGroupName
  origin_group_id     = azurerm_cdn_origin_group.front_door_origin_group.id

  patterns_to_match = [ "/*" ]
  forwarding_protocol = "HttpsOnly"
  https_redirect = true
  supported_protocols = [ "Http", "Https" ]
  link_to_default_domain = true

  depends_on = [ azurerm_cdn_origin.front_door_origin ]
}

resource "azurerm_web_application_firewall_policy" "waf_policy" {
  count               = var.is_secure_mode? 1 : 0
  name                = var.wafPolicyName
  resource_group_name = var.resourceGroupName
  location            = "Global"
  policy_settings {
    mode = var.waf_mode
    request_body_check = true
    max_request_body_size_in_kb = 128
  }
  managed_rules {
    managed_rule_set {
      type = "Microsoft_DefaultRuleSet"
      version = "2.1"
      rule_group_override {
        rule_group_name = "DefaultRuleSet"
        # Remove the "action" attribute
      }
    }
    managed_rule_set {
      type = "Microsoft_BotManagerRuleSet"
      version = "1.0"
      rule_group_override {
        rule_group_name = "BotManagerRuleSet"
        # Remove the "action" attribute
      }
    }
  }
}

// Attach WAF Policy to the Front Door Endpoint
resource "azurerm_frontdoor_firewall_policy_link" "link" {
  count               = var.is_secure_mode ? 1 : 0
  name                = var.securityPolicyName
  frontdoor_name      = azurerm_frontdoor.front_door.name
  resource_group_name = var.resourceGroupName
  web_application_firewall_policy_id = azurerm_web_application_firewall_policy.waf_policy.id
}


resource "azurerm_app_service_virtual_network_swift_connection" "virtualNetworkConnection" {
  app_service_id = azurerm_linux_web_app.app_service.id
  subnet_id      = var.subnetResourceIdOutbound
}

data "azurerm_key_vault" "existing" {
  name                = var.keyVaultName
  resource_group_name = var.resourceGroupName
}

resource "azurerm_key_vault_access_policy" "policy" {
  key_vault_id = data.azurerm_key_vault.existing.id

  tenant_id = azurerm_linux_web_app.app_service.identity.0.tenant_id
  object_id = azurerm_linux_web_app.app_service.identity.0.principal_id

  secret_permissions = [
    "Get",
    "List"
  ]
}


resource "azurerm_monitor_diagnostic_setting" "diagnostic_logs" {
  name                       = azurerm_linux_web_app.app_service.name
  target_resource_id         = azurerm_linux_web_app.app_service.id
  log_analytics_workspace_id = var.logAnalyticsWorkspaceResourceId

  enabled_log  {
    category = "AppServiceAppLogs"
  }

  enabled_log {
    category = "AppServicePlatformLogs"
  }

  enabled_log {
    category = "AppServiceConsoleLogs"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}


