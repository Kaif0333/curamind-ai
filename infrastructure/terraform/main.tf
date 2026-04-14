provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
  manage_private_bucket = var.create_private_bucket && var.private_bucket_name != ""
}

resource "aws_security_group" "curamind" {
  name        = "${local.name_prefix}-sg"
  description = "Security group for CuraMind AI"
  vpc_id      = var.vpc_id

  dynamic "ingress" {
    for_each = var.allowed_ssh_cidrs
    content {
      description = "SSH"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  dynamic "ingress" {
    for_each = var.allowed_http_cidrs
    content {
      description = "HTTP"
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  dynamic "ingress" {
    for_each = var.allowed_https_cidrs
    content {
      description = "HTTPS"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-sg" })
}

resource "aws_cloudwatch_log_group" "application" {
  name              = "${var.cloudwatch_log_group_prefix}/application"
  retention_in_days = var.cloudwatch_log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "docker" {
  name              = "${var.cloudwatch_log_group_prefix}/docker"
  retention_in_days = var.cloudwatch_log_retention_days
  tags              = local.common_tags
}

resource "aws_s3_bucket" "private" {
  count         = local.manage_private_bucket ? 1 : 0
  bucket        = var.private_bucket_name
  force_destroy = var.s3_force_destroy
  tags          = merge(local.common_tags, { Name = "${local.name_prefix}-private-images" })
}

resource "aws_s3_bucket_public_access_block" "private" {
  count                   = local.manage_private_bucket ? 1 : 0
  bucket                  = aws_s3_bucket.private[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "private" {
  count  = local.manage_private_bucket ? 1 : 0
  bucket = aws_s3_bucket.private[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "private" {
  count  = local.manage_private_bucket ? 1 : 0
  bucket = aws_s3_bucket.private[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "private" {
  count  = local.manage_private_bucket ? 1 : 0
  bucket = aws_s3_bucket.private[0].id

  rule {
    id     = "curamind-private-bucket-lifecycle"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    dynamic "noncurrent_version_expiration" {
      for_each = var.s3_noncurrent_version_expiration_days > 0 ? [1] : []
      content {
        noncurrent_days = var.s3_noncurrent_version_expiration_days
      }
    }
  }
}

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "ec2" {
  name               = "${local.name_prefix}-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "cloudwatch_agent" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "s3_private_bucket" {
  count = var.private_bucket_name == "" ? 0 : 1

  statement {
    effect = "Allow"
    actions = [
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::${var.private_bucket_name}"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]
    resources = [
      "arn:aws:s3:::${var.private_bucket_name}/*"
    ]
  }
}

resource "aws_iam_role_policy" "s3_private_bucket" {
  count  = var.private_bucket_name == "" ? 0 : 1
  name   = "${local.name_prefix}-s3-private-bucket"
  role   = aws_iam_role.ec2.id
  policy = data.aws_iam_policy_document.s3_private_bucket[0].json
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${local.name_prefix}-ec2-profile"
  role = aws_iam_role.ec2.name
}

resource "aws_instance" "curamind" {
  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [aws_security_group.curamind.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2.name
  key_name                    = var.key_name != "" ? var.key_name : null
  associate_public_ip_address = var.associate_public_ip_address
  user_data                   = var.user_data != "" ? var.user_data : null

  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ec2" })
}

resource "aws_eip" "curamind" {
  count    = var.allocate_elastic_ip ? 1 : 0
  domain   = "vpc"
  instance = aws_instance.curamind.id
  tags     = merge(local.common_tags, { Name = "${local.name_prefix}-eip" })
}

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  count               = var.enable_cloudwatch_alarms ? 1 : 0
  alarm_name          = "${local.name_prefix}-cpu-high"
  alarm_description   = "High CPU utilization on the CuraMind AI EC2 host"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.alarm_evaluation_periods
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = var.cpu_alarm_threshold
  treat_missing_data  = "missing"
  alarm_actions       = var.alarm_sns_topic_arns
  ok_actions          = var.alarm_sns_topic_arns

  dimensions = {
    InstanceId = aws_instance.curamind.id
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-cpu-high" })
}

resource "aws_cloudwatch_metric_alarm" "status_check_failed" {
  count               = var.enable_cloudwatch_alarms ? 1 : 0
  alarm_name          = "${local.name_prefix}-status-check-failed"
  alarm_description   = "Instance status check failures on the CuraMind AI EC2 host"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.alarm_evaluation_periods
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = var.status_check_alarm_threshold
  treat_missing_data  = "missing"
  alarm_actions       = var.alarm_sns_topic_arns
  ok_actions          = var.alarm_sns_topic_arns

  dimensions = {
    InstanceId = aws_instance.curamind.id
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-status-check-failed" })
}
