output "instance_id" {
  description = "EC2 instance ID for the CuraMind AI host."
  value       = aws_instance.curamind.id
}

output "instance_public_ip" {
  description = "Public IP of the EC2 instance."
  value       = aws_instance.curamind.public_ip
}

output "elastic_ip" {
  description = "Elastic IP allocated for the EC2 instance when enabled."
  value       = try(aws_eip.curamind[0].public_ip, null)
}

output "security_group_id" {
  description = "Security group ID used by the EC2 instance."
  value       = aws_security_group.curamind.id
}

output "iam_instance_profile_name" {
  description = "Instance profile attached to the EC2 instance."
  value       = aws_iam_instance_profile.ec2.name
}

output "cloudwatch_log_group_names" {
  description = "CloudWatch log groups created for the stack."
  value = [
    aws_cloudwatch_log_group.application.name,
    aws_cloudwatch_log_group.docker.name
  ]
}

output "private_bucket_name" {
  description = "Private S3 bucket used for medical image storage."
  value       = var.private_bucket_name != "" ? var.private_bucket_name : null
}

output "private_bucket_arn" {
  description = "ARN of the managed private bucket when Terraform creates it."
  value       = try(aws_s3_bucket.private[0].arn, null)
}

output "cloudwatch_alarm_names" {
  description = "CloudWatch alarm names created for the EC2 host."
  value = compact([
    try(aws_cloudwatch_metric_alarm.cpu_high[0].alarm_name, null),
    try(aws_cloudwatch_metric_alarm.status_check_failed[0].alarm_name, null)
  ])
}
