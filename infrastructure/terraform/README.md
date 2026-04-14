# Terraform Scaffold

This directory provisions the AWS foundation for a single-host CuraMind AI deployment:

- EC2 instance
- security group for `22`, `80`, and `443`
- IAM role + instance profile
- CloudWatch log groups
- optional secure S3 private bucket for imaging storage
- optional Elastic IP for a stable public address
- optional CloudWatch alarms for CPU and EC2 status checks
- optional SNS alarm routing when topic ARNs are provided

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
5. Optional: install systemd timers with `scripts/install_ops_timers.sh`
6. Run `scripts/deploy_ec2.sh .env`

## Notes
- Set `create_private_bucket = true` to let Terraform create the private S3 imaging bucket with versioning, public-access blocking, encryption, and lifecycle controls.
- Set `allocate_elastic_ip = true` if the deployment should keep a stable public IP address.
- Set `alarm_sns_topic_arns` to receive CloudWatch alarm notifications for CPU or failed EC2 status checks.
