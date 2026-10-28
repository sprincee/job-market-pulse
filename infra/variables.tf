variable "alert_email" {
  description = "Where pipeline alarms are sent (set in terraform.tfvars, which is gitignored)"
  type        = string

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "alert_email must be an email address."
  }
}
