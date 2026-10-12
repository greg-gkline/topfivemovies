provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "topfivemovies"
      ManagedBy = "terraform"
    }
  }
}

# CloudFront reads its certificate from us-east-1, whatever region the rest is in.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project   = "topfivemovies"
      ManagedBy = "terraform"
    }
  }
}
