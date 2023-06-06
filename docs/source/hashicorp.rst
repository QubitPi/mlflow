MLflow AMI Image
================

A public MLflow AMI image is available at `AWS AMI <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html>`_ for
anyone with an AWS account. The *AMI name* is "**jack20191124-mlflow**" and *Owner ID* is "**899075777617**". We
could, for example, deploy an EC2 instance of this image using HashiCorp Terraform (The code snippet below can be put
in a file with extension ``.tf``, such as `main.tf`):

.. code-block:: terraform

  terraform {
    required_providers {
      aws = {
        source  = "hashicorp/aws"
        version = "~> 4.42.0"
      }
    }
    required_version = ">= 0.14.5"
  }

  provider "aws" {
    region = "us-east-1"
  }

  data "aws_ami" "latest-jack20191124-mlflow" {
    most_recent = true
    owners = ["899075777617"]

    filter {
      name   = "name"
      values = ["jack20191124-mlflow"]
    }

    filter {
      name   = "virtualization-type"
      values = ["hvm"]
    }
  }

  resource "aws_instance" "mlflow-tracking-server" {
    ami = "${data.aws_ami.latest-jack20191124-mlflow.id}"
    instance_type = "t2.micro"
    tags = {
      Name = "MLflow UI & Tracking Server"
    }

    user_data = <<-EOF
      #!/bin/bash
      mlflow server --host 0.0.0.0
    EOF
  }

- Please do not forget to specify the ``AWS_ACCESS_KEY_ID`` & ``AWS_SECRET_ACCESS_KEY`` environment variables of the
  `IAM user <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users.html>`_, because
  `terraform needs to be authenticated <https://developer.hashicorp.com/terraform/tutorials/aws-get-started/aws-build>`_
  to create EC2 instances on behalf of that user.
- Note that the configuration above deploys the EC2 instance to East 1 region
- When deployed, the EC2 instance name will be "MLflow UI & Tracking Server".
- After EC2 is instantiated, we still need to manually attach
  `security group <https://docs.aws.amazon.com/vpc/latest/userguide/security-groups.html>`_ to that instance. There is
  a plan, though, to enable automatically attaching a pre-configured security group

  - The security group must have TCP port 5000 open for its UI access

The MLflow instance, after deployment, can be accessed at ``http://<ec2-public-ip>:5000``
