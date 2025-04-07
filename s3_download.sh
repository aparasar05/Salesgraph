#!bin/sh
set -x
 PATH="/usr/local/bin:$PATH"
bucket_name=$1
bucket_folder=$2
download_folder=$3
result=""

if [[ -n $download_folder  && -n $bucket_folder ]]; then
  if [[ "${bucket_folder: -1}" == '/' ]]; then
    aws s3 cp s3://$bucket_name$bucket_folder $download_folder --recursive
  else
    aws s3 cp s3://$bucket_name$bucket_folder $download_folder
  fi
  if [ $? -eq 0 ]; then
    result="Success"
  else
    result="Fail"
  fi
fi

echo $result