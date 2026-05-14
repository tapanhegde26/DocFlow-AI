terraform {
  backend "s3" {
    bucket = "intouchx-terraform-tf-state-bucket"
    key    = "dev/terraform.tfstate"
    region = "ca-central-1"
    //dynamodb_table = "intouchx-terraform-locks"         
    encrypt = true
  }
}
