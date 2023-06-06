# Copyright Jiaqi Liu
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

variable "aws_deploy_region" {
  type = string
  description = "The EC2 region"
}

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
  region = var.aws_deploy_region
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
