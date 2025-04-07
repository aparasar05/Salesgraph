import json
import os
import boto3
import time


def lambda_handler(event, context):
    try:
        variable_result = check_env_variables()
        print(variable_result)
        # Perform the operation on the instances
        if variable_result['result'] is True:
            operation_result = perform_operation(variable_result)

    except Exception as error:
        print('S3UD_ERR_001',
                     'System Exception: {0}'.format(str(error)))
    return


def check_instance_running(instance):
    result = False
    ec2_client = boto3.client('ec2', region_name='ap-northeast-1')

    response = ec2_client.describe_instance_status(InstanceIds=[instance],
                                                   IncludeAllInstances=True)
    http_status_code = response[
        "ResponseMetadata"]["HTTPStatusCode"]
    # Checking Status Code is 200 then return result as true.
    if http_status_code == 200:
        if response['InstanceStatuses'][0]['InstanceState'][
            'Name'] == 'running':
            result = True
    else:
        log_msg = 'Unable to fetch the status of the EC2 instance {0}'.format(
            instance)
        raise Exception(log_msg)
    return result


# Check environment variables
def check_env_variables():
    s3_bucket_syn_path = ''
    sever_download_dir = ''
    required_variables_available = False

    try:
        if os.environ['S3_Bucket_name'] and os.environ['S3_Server_id']:
            if 'S3_Server_download_directory' in os.environ and 'S3_Bucket_sync_path' in os.environ:
                required_variables_available = True
                s3_bucket_syn_path = os.environ['S3_Bucket_sync_path']
                sever_download_dir = os.environ['S3_Server_download_directory']
    except Exception as error:
        # Convert error into sting
        log_msg = str(error)
        raise Exception('Environment variable {0} is missing'.format(log_msg))

    if required_variables_available is False:
        raise Exception(
            "Environment variables are missing.")
    required_variables = {
        "s3_bucket_name": os.environ['S3_Bucket_name'],
        "s3_bucket_syn_path": s3_bucket_syn_path,
        "sever_download_dir": sever_download_dir,
        "result": required_variables_available,
        "S3_server_id": os.environ['S3_Server_id']
    }
    return required_variables


def check_status(command_id, instance_id, ssm, operation):
    retry = False
    result = False
    reason = ''
    while True:
        time.sleep(2)
        status_response = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id)
        print('BBBBBBBBBBBBBB')
        print(status_response)
        http_status_code = status_response[
            "ResponseMetadata"]["HTTPStatusCode"]
        if http_status_code == 200:
            status = status_response['Status']
            if status == 'Success':
                if 'Fail' in status_response['StandardOutputContent']:
                    log_msg = "The {0} operation failed to sync with the " \
                              "S3 bucket".format(operation)
                    result = False
                else:
                    log_msg = "The {0} operation to sync with the S3 " \
                              "bucket is successful".format(operation)
                    result = True
                break
            elif status == 'Failed' or status == 'Timeout':
                log_msg = "The {0} operation failed to sync with the S3 " \
                          "bucket".format(operation)
                reason = '{0} \n'.format(
                    status_response['StandardErrorContent'])
                break
            else:
                retry = True
        else:
            log_msg = "Unable to get the status of the {0} operation to " \
                      "sync with S3 bucket.".format(operation)
            if 'Error' in status_response:
                reason = status_response['Error']['Message']

        if retry:

            continue
        break

    final_status = {
        "result": result,
        "reason": reason
    }
    return final_status


# This function performs the desired operation on the instance ids.`
def perform_operation(variable_result):
    instance = variable_result['S3_server_id']
    # # Check if instance ids exist to be started
    instance_running = check_instance_running(instance)
    if instance_running:
        ssm = boto3.client('ssm')
        http_status_code = 0
        command = "sudo sh /script/bin/s3_download.sh {0} {1} {2} ". \
            format(variable_result['s3_bucket_name'],
                   variable_result[
                       's3_bucket_syn_path'],
                   variable_result[
                       'sever_download_dir'])

        command = command.replace("   ", " \"\" \"\" ")
        command = command.replace("  ", " \"\" ")
        print('CCCCCCCCCCCC')
        print(command)
        response = ssm.send_command(
            InstanceIds=[variable_result['S3_server_id']],
            DocumentName='AWS-RunShellScript',
            Parameters={"commands": [command]}
        )

        http_status_code = response[
            "ResponseMetadata"]["HTTPStatusCode"]
        # Checking Status Code is 200 then return result as true.
        if http_status_code == 200:
            command_id = response['Command']['CommandId']
            result = check_status(command_id, variable_result['S3_server_id'],
                                  ssm, "Download")
            print("AAAAAAAAAAAAA")
            print(result)
        else:
            log_msg = 'The {0} operation failed to sync with the S3 ' \
                      'bucket'.format(variable_result['operation'])

            result = {
                "result": False,
                "reason": log_msg
            }
    else:
        log_msg = "Instance {0} is not running.".format(instance)

        result = {
            "result": False,
            "reason": log_msg
        }
    return result
