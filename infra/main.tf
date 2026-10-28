# Main infrastructure. State lives in the bucket created by infra/bootstrap.

terraform {
  required_version = ">= 1.10" # 1.10+ needed for native S3 state locking (use_lockfile)

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    # Zips the Lambda package locally; no cloud service involved.
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }

  # Backend blocks can't use variables, so these values are literal.
  backend "s3" {
    bucket       = "jmp-tfstate-723951823306"
    key          = "main/terraform.tfstate"
    region       = "us-east-1"
    profile      = "jmp"
    encrypt      = true
    use_lockfile = true # writes a .tflock object so two applies can't run at once
  }
}

provider "aws" {
  region  = "us-east-1"
  profile = "jmp"

  # Refuse to run against any other account (this laptop has other projects).
  allowed_account_ids = ["723951823306"]

  default_tags {
    tags = {
      Project   = "job-market-pulse"
      ManagedBy = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
}
