provider "aws" {
  region = "us-east-1"
}

# ----------------------
# S3 Buckets
# ----------------------
resource "aws_s3_bucket" "bucket_1" {
  bucket = "example-bucket-1-${random_id.suffix.hex}"
  force_destroy = true
}

resource "aws_s3_bucket" "bucket_2" {
  bucket = "example-bucket-2-${random_id.suffix.hex}"
  force_destroy = true
}

# Random suffix to ensure bucket names are globally unique
resource "random_id" "suffix" {
  byte_length = 4
}

# ----------------------
# EC2 Instances
# ----------------------
resource "aws_instance" "t3_large_instance" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.large"

  tags = {
    Name = "t3-large-instance"
  }
}

resource "aws_instance" "c5_9xlarge_instances" {
  count         = 3
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "c5.9xlarge"

  tags = {
    Name = "c5-9xlarge-${count.index}"
  }
}

# ----------------------
# AMI Lookup (Amazon Linux 2)
# ----------------------
data "aws_ami" "amazon_linux" {
  most_recent = true

  owners = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}
