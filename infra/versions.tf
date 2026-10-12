terraform {
  required_version = ">= 1.10" # S3 state locking with a lockfile (use_lockfile)

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # The state bucket was created by hand and is not managed here. Locking uses a lockfile
  # next to the state object, so no DynamoDB table is needed.
  backend "s3" {
    bucket       = "infrastructure-832474135782-us-east-2-an"
    key          = "topfivemovies/terraform/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }
}
