# Terraform Scaffold

This directory provisions the AWS foundation for a single-host CuraMind AI deployment:

- EC2 instance
- security group for `22`, `80`, and `443`
- IAM role + instance profile
- CloudWatch log groups
- optional S3 private-bucket access policy for imaging storage

## Files
- `versions.tf`
- `variables.tf`
- `main.tf`
- `outputs.tf`
- `terraform.tfvars.example`

## Usage
1. Copy `terraform.tfvars.example` to `terraform.tfvars`
2. Fill in your VPC, subnet, AMI, key pair, and bucket values
3. Run:

```bash
terraform init
terraform plan
terraform apply
```

## After Apply
1. SSH or SSM into the instance
2. Clone the repo
3. Run `scripts/ec2_bootstrap.sh`
4. Run `scripts/install_cloudwatch_agent.sh`
5. Run `scripts/deploy_ec2.sh .env`
