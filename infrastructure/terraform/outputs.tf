output "instance_id" {
  description = "EC2 instance ID for the CuraMind AI host."
  value       = aws_instance.curamind.id
}

output "instance_public_ip" {
  description = "Public IP of the EC2 instance."
  value       = aws_instance.curamind.public_ip
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
