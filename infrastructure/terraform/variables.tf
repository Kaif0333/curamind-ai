variable "aws_region" {
  description = "AWS region for the CuraMind AI deployment."
  type        = string
}

variable "project_name" {
  description = "Project name prefix."
  type        = string
  default     = "curamind"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "production"
}

variable "ami_id" {
  description = "AMI ID for the EC2 instance."
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type."
  type        = string
  default     = "t3.large"
}

variable "subnet_id" {
  description = "Subnet ID for the EC2 instance."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the security group."
  type        = string
}

variable "key_name" {
  description = "Optional EC2 key pair name."
  type        = string
  default     = ""
}

variable "associate_public_ip_address" {
  description = "Whether to assign a public IP to the instance."
  type        = bool
  default     = true
}

variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed to SSH to the EC2 instance."
  type        = list(string)
  default     = []
}

variable "allowed_http_cidrs" {
  description = "CIDR blocks allowed to access HTTP."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "allowed_https_cidrs" {
  description = "CIDR blocks allowed to access HTTPS."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "root_volume_size" {
  description = "Root EBS volume size in GiB."
  type        = number
  default     = 50
}

variable "cloudwatch_log_group_prefix" {
  description = "Prefix for CloudWatch log groups created for the platform."
  type        = string
  default     = "/curamind/production"
}

variable "cloudwatch_log_retention_days" {
  description = "Retention period in days for CloudWatch log groups."
  type        = number
  default     = 30
}

variable "private_bucket_name" {
  description = "Optional private S3 bucket name used for medical image storage."
  type        = string
  default     = ""
}

variable "user_data" {
  description = "Optional user data script for the EC2 instance."
  type        = string
  default     = ""
}
