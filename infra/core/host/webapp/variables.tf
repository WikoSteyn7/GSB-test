variable "name" {
  type = string
}

variable "planName" {
  type = string
}

variable "location" {
  type = string
}

variable "tags" {
  type = map(string)
  default = {}
}

variable "kind" {
  type = string
  default = ""
}

variable "reserved" {
  type = bool
  default = true
}

variable "sku" {
  type = map(string)
}

variable "resourceGroupName" {
  type    = string
  default = ""
}

variable "storageAccountId" {
  type    = string
  default = ""
}

variable "managedIdentity" {
  type = bool
  default = false
}

variable "logAnalyticsWorkspaceResourceId" {
  type = string
  default = ""
}

variable "applicationInsightsConnectionString" {
  type    = string
  default = ""
}

variable "keyVaultUri" { 
  type = string
}

variable "keyVaultName" {
  type = string
}

variable "aadClientId" {
  type = string
  default = ""
}

variable "tenantId" {
  type = string
  default = ""
}

variable "scmDoBuildDuringDeployment" {
  type = bool
  default = true
}

variable "enableOryxBuild" {
  type = bool
  default = true
}

variable "appSettings" {
  type = map(string)
  default = {}
}

variable "ftpsState" {
  type = string
  default = "FtpsOnly"
}

variable "alwaysOn" {
  type = bool
  default = true
}

variable "appCommandLine" {
  type = string
  default = ""
}

variable "healthCheckPath" {
  type = string
  default = ""
}

variable "azurePortalDomain" {
  type    = string
  default = ""
}

variable "allowedOrigins" {
  type = list(string)
  default = []
}

variable "runtimeVersion" {
  type    = string
  default = "3.10"
}

variable "azureEnvironment" {
  type    = string
  default = "AzureCloud"
}
variable "securityPolicyName" {
  description = "The name of the security policy"
  type        = string
  default     = ""
}

variable "subnetResourceIdOutbound" {
  description = "The resource ID of the outbound subnet"
  type        = string
  default     = ""
}

variable "wafPolicyName" {
  description = "The name of the Web Application Firewall (WAF) policy"
  type        = string
  default     = ""
}

variable "waf_mode" {
  description = "The mode of the Web Application Firewall (WAF)"
  type        = string
  default     = "Detection"
}

variable "is_secure_mode" {
  description = "Specifies whether to deploy in secure mode"
  type        = bool
  default     = false
}

variable "fdProfileName" {
  description = "The name of the Front Door profile"
  type        = string
  default     = ""
}

variable "fdEndpointName" {
  description = "The name of the Front Door endpoint"
  type        = string
  default     = ""
}

variable "fdOriginName" {
  description = "The name of the Front Door origin"
  type        = string
  default     = ""
}

variable "appServiceplanName" {
  description = "The name of the App Service Plan within which to create this App Service"
  type        = string
  default     = ""
}

variable "appServiceplanId" {
  description = "The ID of the App Service Plan within which to create this App Service"
  type        = string
  default     = ""
}