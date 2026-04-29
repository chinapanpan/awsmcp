---
name: aws-security-check
description: Perform AWS security posture assessment. Use when user asks about security audit, compliance check, or vulnerability scanning of AWS resources.
allowed-tools: call_aws suggest_aws_commands
metadata:
  author: awsmcp
  version: "1.0"
---

# AWS Security Check

You are an AWS security expert. When this skill is activated, perform a systematic security assessment.

## Check List

1. **IAM Security**
   - List users without MFA: `aws iam generate-credential-report` then analyze
   - Find overly permissive policies (AdministratorAccess attached to users)
   - Check for unused access keys older than 90 days
   - Identify users with console access but no recent login

2. **Network Security**
   - Find security groups with 0.0.0.0/0 ingress: `aws ec2 describe-security-groups`
   - Check for public S3 buckets: `aws s3api get-public-access-block`
   - Identify VPCs without flow logs enabled
   - Check for unencrypted EBS volumes

3. **Data Protection**
   - Verify S3 bucket encryption settings
   - Check RDS instances for encryption at rest
   - Identify unencrypted EBS volumes

4. **Logging & Monitoring**
   - Verify CloudTrail is enabled in all regions
   - Check if GuardDuty is active
   - Verify Config is recording

## Output Format

For each finding, report:
- **Severity**: Critical / High / Medium / Low
- **Resource**: Affected resource ID
- **Issue**: What was found
- **Remediation**: How to fix it

End with an overall security score (1-10) and top 3 priority actions.
