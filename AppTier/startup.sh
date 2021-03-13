#!/bin/bash

export AWS_CONFIG_FILE=/home/ubuntu/config
export AWS_SHARED_CREDENTIALS_FILE=/home/ubuntu/credentials
cd /home/ubuntu/classifier/
python3 AppTier.py
rm *.JPEG
rm *.txt
mkdir Nik
#shutdown -h now