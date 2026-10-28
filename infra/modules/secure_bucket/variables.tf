variable "name" {
  description = "Globally unique bucket name"
  type        = string
}

variable "versioning" {
  description = "Keep previous versions of overwritten or deleted objects"
  type        = bool
  default     = false
}

variable "noncurrent_version_expiration_days" {
  description = "Days to keep a version after it is overwritten (only if versioning)"
  type        = number
  default     = 30
}
