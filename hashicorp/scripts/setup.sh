#!/bin/bash
set -x

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

sudo apt update && sudo apt upgrade -y
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.8 -y
sudo apt install python3-pip -y

sudo pip3 install mlflow

# Fix pip3 install mlflow 'ERROR: flask 2.3.2 has requirement click>=8.1.3, but you'll have click 7.0 which is incompatible.'
sudo pip3 install click==8.1.3
# And similar fixes
sudo pip3 install zipp==3.1.0
sudo pip3 install urllib3==1.26.7
sudo pip3 install requests==2.26.0
