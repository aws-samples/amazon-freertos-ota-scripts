## Amazon Freertos OTA Scripts

Scripts to aid initiating OTA updates for Amazon FreeRTOS devices.

For more information on Amazon FreeRTOS OTA updates, please refer to the [documentation](https://docs.aws.amazon.com/freertos/latest/userguide/freertos-ota-dev.html)

## Folder Contents
### start_ota.py
This script is used to update the firmware on the device without creating a separate stream

    usage: start_ota.py [-h] --profile PROFILE [--region REGION]
                        [--account ACCOUNT] [--devicetype DEVICETYPE] --name NAME
                        --role ROLE --s3bucket S3BUCKET --otasigningprofile
                        OTASIGNINGPROFILE --signingcertificateid
                        SIGNINGCERTIFICATEID [--codelocation CODELOCATION]

    Script to start OTA update

    optional arguments:
      -h, --help            show this help message and exit
      --profile PROFILE     Profile name created using aws configure
      --region REGION       Region
      --account ACCOUNT     Account ID
      --devicetype DEVICETYPE
                            thing|group
      --name NAME           Name of thing/group
      --role ROLE           Role for OTA updates
      --s3bucket S3BUCKET   S3 bucket to store firmware updates
      --otasigningprofile OTASIGNINGPROFILE
                            Signing profile to be created or used
      --signingcertificateid SIGNINGCERTIFICATEID
                            certificate id (not arn) to be used
      --codelocation CODELOCATION
                            base folder location (can be relative)


### start_ota_stream.py
This script is used to update the firmware on the device after creating a stream. The stream creation step is needed if the file Id needs to be injected into the OTA update.

    usage: start_ota_stream.py [-h] [--fileId FILEID] --profile PROFILE
                              [--region REGION] [--account ACCOUNT]
                              [--devicetype DEVICETYPE] --name NAME --role ROLE
                              --s3bucket S3BUCKET --otasigningprofile
                              OTASIGNINGPROFILE --signingcertificateid
                              SIGNINGCERTIFICATEID [--codelocation CODELOCATION]

    Script to start OTA update

    optional arguments:
      -h, --help            show this help message and exit
      --fileId FILEID       ID of file being streamed to the device
      --profile PROFILE     Profile name created using aws configure
      --region REGION       Region
      --account ACCOUNT     Account ID
      --devicetype DEVICETYPE
                            thing|group
      --name NAME           Name of thing/group
      --role ROLE           Role for OTA updates
      --s3bucket S3BUCKET   S3 bucket to store firmware updates
      --otasigningprofile OTASIGNINGPROFILE
                            Signing profile to be created or used
      --signingcertificateid SIGNINGCERTIFICATEID
                            certificate id (not arn) to be used
      --codelocation CODELOCATION
                            base folder location (can be relative)


### ota-ble.cform.json
This file is used to create infrastructure needed to support OTA updates including S3 buckets, roles, policies and users needed to perform the updates. 

Note: Access Keys are not automatically generated in the cloudformation scripts and need to be generated manually.


## Warning
Before you distribute the CloudFormation template to your organization, review the template. Check IAM permissions, Deletion policies, update stack behavior, other aspects of the template, and ensure that they are as per your expectations and processes. These sample CloudFormation templates may need updates before you can use them in production. Running these templates may result in charges to your AWS account. Provisioning the supplied Products through ServiceCatalog will create AWS Services which will be billed to your account.

## License Summary

This sample code is made available under the Apache 2.0 license. See the LICENSE file.
