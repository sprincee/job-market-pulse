# Raw API responses, written only by the ingest Lambda.
# curated/ and site/ buckets are added in the steps that first use them.
module "raw_bucket" {
  source = "./modules/secure_bucket"

  name       = "jmp-raw-${local.account_id}"
  versioning = true
}
