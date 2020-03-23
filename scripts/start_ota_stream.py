# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#     http://www.apache.org/licenses/LICENSE-2.0
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.
#
# AWS IoT OTA Update Script
# Important Note: Requires Python 3

import pathlib
import re
from pathlib import Path
from shutil import copyfile
import random
import boto3
import sys
import argparse
import traceback
import time

parser = argparse.ArgumentParser(description='Script to start OTA update')
parser.add_argument(
    "--fileId", help="ID of file being streamed to the device", default=0, type=int, required=False)
parser.add_argument(
    "--profile", help="Profile name created using aws configure", required=True)
parser.add_argument("--region", help="Region", default="", required=False)
parser.add_argument("--account", help="Account ID", default="", required=False)
parser.add_argument("--devicetype", help="thing|group",
                    default="thing", required=False)
parser.add_argument("--name", help="Name of thing/group", required=True)
parser.add_argument("--role", help="Role for OTA updates", required=True)
parser.add_argument(
    "--s3bucket", help="S3 bucket to store firmware updates", required=True)
parser.add_argument("--otasigningprofile",
                    help="Signing profile to be created or used", required=True)
parser.add_argument("--signingcertificateid",
                    help="certificate id (not arn) to be used", required=True)
parser.add_argument("--codelocation", help="base FreeRTOS folder location (can be relative) when fileId is 0",
                    default="../code/amazon-freertos/", required=False)
parser.add_argument("--filelocation", help="OTA update file location when fileId is greater than 0",
                    default="update.bin", required=False)
parser.add_argument("--otaversion", help="Version for custom FreeRTOS ota when fileId is 0 or secondary OTA when fileId is greater than 0",
                    default="0.0.0", required=False)
args = parser.parse_args()


class AWS_IoT_OTA:

    constants = dict()

    """
    Read constants from the header file so that we can grab the version information
    """

    def ReadConstantsFromHeader(self):
        self.DEMOS_PATH = Path(args.codelocation)
        self.VERSIONFILE = self.DEMOS_PATH / \
            Path("demos/include/aws_application_version.h")
        self.BUILD_PATH = self.DEMOS_PATH / Path("build/")

        with open(self.VERSIONFILE) as infile:
            for line in infile:
                try:
                    matchFound = (re.findall(
                        r"#define\s+(\w+)\s+(.*)", line.strip()))
                    if (len(matchFound) != 0):
                        self.constants.update(matchFound)
                except Exception as e:
                    pass
        #print ( repr(constants) )

    """
    Converts the passed in ota version to major, minor, and build version
    """
    def ConvertOTAVersionToMajorMinorBuild(self):
        if args.otaversion:
            major, *version = str(args.otaversion).split(".")

            try:
                int(major)
            except ValueError:
                print("Error value %s can't be converted to integer" % major)
                raise Exception("Error value %s can't be converted to integer" % major)

            if len(version) > 0:
                minor = version[0]
            else:
                minor = "0"

            if len(version) > 1:
                build = version[1]
            else:
                build = "0"

            self.constants["APP_VERSION_MAJOR"] = major
            self.constants["APP_VERSION_MINOR"] = minor
            self.constants["APP_VERSION_BUILD"] = build
        else:
            self.constants["APP_VERSION_MAJOR"] = "0"
            self.constants["APP_VERSION_MINOR"] = "0"
            self.constants["APP_VERSION_BUILD"] = "0"

    def BuildFirmwareFileNames(self):

        # Check if we are updating Processor 0 firmware and extract the versions from
        # the FreeRTOS header file
        if args.fileId == 0 and not args.otaversion:
            # Read constants from header and build the application name to be used for update
            self.ReadConstantsFromHeader()

            # We Should have the versions stored at this point. Build the App name
            self.APP_NAME = "aws_demos_" + self.constants["APP_VERSION_MAJOR"] + "." + \
                self.constants["APP_VERSION_MINOR"] + "." + \
                self.constants["APP_VERSION_BUILD"] + ".bin"
            self.APP_FULL_NAME = self.BUILD_PATH / Path(self.APP_NAME)
            self.BUILD_FILE_FULL_NAME = self.BUILD_PATH/Path("aws_demos.bin")
            print("Using App Location: " + str(self.APP_FULL_NAME))
            print("Build File Name: " + str(self.BUILD_FILE_FULL_NAME))

            # First make a copy of the bin file with the version in the name
            try:
                copyfile(self.BUILD_FILE_FULL_NAME, self.APP_FULL_NAME)
            except Exception as e:
                print("Error copying %s" % self.BUILD_FILE_FULL_NAME)
                sys.exit
        else:
            try:
                # Extract out versions
                self.ConvertOTAVersionToMajorMinorBuild()

                # Set the build file output to the location passed in to filelocation
                self.BUILD_FILE_FULL_NAME = args.filelocation

                # Break file path down so the version number can be appended to the file name
                filepath = Path(self.BUILD_FILE_FULL_NAME)
                basename = filepath.stem

                # This is the file name that will be uploaded to S3
                self.APP_NAME = basename + "_" + self.constants["APP_VERSION_MAJOR"] + "." + \
                    self.constants["APP_VERSION_MINOR"] + "." + \
                    self.constants["APP_VERSION_BUILD"] + ".bin"

                # Add the full path on to the new app name so we can copy the file
                self.APP_FULL_NAME = Path.joinpath(filepath.parent, self.APP_NAME)
                print("App Name: " + str(self.APP_NAME))
                print("Using App Location: " + str(self.APP_FULL_NAME))
                print("Build File Name: " + str(self.BUILD_FILE_FULL_NAME))

                try:
                    copyfile(self.BUILD_FILE_FULL_NAME, self.APP_FULL_NAME)
                except Exception as e:
                    print("Error copying %s" % self.BUILD_FILE_FULL_NAME)
                    sys.exit

            except Exception as e:
                print("Error building firmware file names" % args.filelocation)
                sys.exit

    # Copy the file to the s3 bucket

    def CopyFirmwareFileToS3(self):
        self.s3 = boto3.resource('s3')
        try:
            self.s3.meta.client.upload_file(
                str(self.APP_FULL_NAME), args.s3bucket, str(self.APP_NAME))
        except Exception as e:
            print("Error uploading file to s3: %s", e)
            sys.exit

    # Get the latest version

    def GetLatestS3FileVersion(self):
        try:
            versions = self.s3.meta.client.list_object_versions(
                Bucket=args.s3bucket, Prefix=self.APP_NAME)['Versions']
            latestversion = [x for x in versions if x['IsLatest'] == True]
            self.latestVersionId = latestversion[0]['VersionId']
            #print("Using version %s" % self.latestVersionId)
        except Exception as e:
            print("Error getting versions: %s" % e)
            sys.exit

    # Create signing profile if it does not exist

    def CreateSigningProfile(self):
        try:
            signer = boto3.client('signer')
            profiles = signer.list_signing_profiles()['profiles']

            foundProfile = False
            afrProfile = None
            print("Searching for profile %s" % args.otasigningprofile)

            if len(profiles) > 0:
                for profile in profiles:
                    if profile['profileName'] == args.otasigningprofile:
                        foundProfile = True
                        afrProfile = profile

            if (afrProfile != None):
                foundProfile = True
                print("Found Profile %s in account" % args.otasigningprofile)

            if (foundProfile == False):
                # Create profile
                newProfile = signer.put_signing_profile(
                    signingParameters={
                        'certname': 'otasigner.crt'
                    },
                    profileName=args.otasigningprofile,
                    signingMaterial={
                        'certificateArn': self.SIGNINGCERTIFICATEARN
                    },
                    platformId='AmazonFreeRTOS-Default'
                )
                print("Created new signing profile: %s" % newProfile)
        except Exception as e:
            print("Error creating signing profile: %s" % e)
            sys.exit

    def CreateOTAJob(self):

        # Create OTA job
        try:
            iot = boto3.client('iot')
            signer = boto3.client('signer')
            randomSeed = random.randint(1, 65535)

            target = "arn:aws:iot:"+args.region+":" + \
                args.account+":"+args.devicetype+"/"+args.name
            updateId = "esp-"+str(randomSeed) + "-"+self.constants["APP_VERSION_MAJOR"] + "-" + \
                self.constants["APP_VERSION_MINOR"] + "-" + \
                self.constants["APP_VERSION_BUILD"]

            # First start a signing job
            signingjob = signer.start_signing_job(
                source={
                    's3': {
                        'bucketName': args.s3bucket,
                        'key': self.APP_NAME,
                        'version': self.latestVersionId
                    }
                },
                destination={
                    's3': {
                        'bucketName': args.s3bucket
                    }
                },
                profileName=args.otasigningprofile,
                clientRequestToken=updateId
            )

            s3StreamKey = signingjob['jobId']
            # print("Signing Job: %s\r\n" % signingjob)
            # print("Signing stream key: %s \r\n" % s3StreamKey)

            print("Waiting for signing job to complete \r\n")

            # Wait until job is done
            signJobTimeout = 30 #seconds
            start = time.time()
            signJobComplete = False
            while time.time()-start <= signJobTimeout:
                signingJobStatus = signer.describe_signing_job(jobId=s3StreamKey)['status']
                # print("Signing Status: %s" % signingJobStatus)
                if signingJobStatus == "Succeeded":
                    signJobComplete = True
                    break
                time.sleep(5)

            if signJobComplete == False:
                print("Signing job did not complete in time. Exiting")
                exit



            versions = self.s3.meta.client.list_object_versions(
                Bucket=args.s3bucket, Prefix=s3StreamKey)['Versions']

            # print("Versions: %s\r\n" % versions)

            latestversion = [x for x in versions if x['IsLatest'] == True][0]['VersionId']
            # print("Latest Version: %s\r\n" % latestversion)

            # Initialize the template to use
            streamFiles = [{
                'fileId': args.fileId,
                's3Location': {
                    'bucket': args.s3bucket,
                    'key': s3StreamKey,
                    'version': latestversion
                }
            }]

            # print("Stream for update: %s\r\n" % streamFiles)

            stream_create = iot.create_stream(
                streamId=updateId,
                files=streamFiles,
                roleArn="arn:aws:iam::"+args.account+":role/"+args.role
            )

            # print("Stream Create Status: %s" % stream_create)

            # Initialize the template to use for the ota update
            files = [{
                'fileName': self.APP_NAME,
                'fileVersion': '1',
                'fileLocation': {
                    'stream': {
                        'streamId': updateId,
                        'fileId': args.fileId
                    }
                },
                'codeSigning': {
                    "awsSignerJobId": signingjob['jobId']
                }
            }]

            # print("Files for update: %s" % files)

            ota_update = iot.create_ota_update(
                otaUpdateId=updateId,
                targetSelection='SNAPSHOT',
                files=files,
                targets=[target],
                roleArn="arn:aws:iam::"+args.account+":role/"+args.role
            )

            print("OTA Update Status: %s" % ota_update)

        except Exception as e:
            print("Error creating OTA Job: %s" % e)
            sys.exit

    def __init__(self):
        boto3.setup_default_session(profile_name=args.profile)
        self.Session = boto3.session.Session()
        if args.region == '':
            args.region = self.Session.region_name

        if args.account == '':
            # Get account Id
            args.account = boto3.client(
                'sts').get_caller_identity().get('Account')

        self.SIGNINGCERTIFICATEARN = "arn:aws:acm:"+args.region + \
            ":"+args.account+":certificate/"+args.signingcertificateid

        print("Certificate ARN: %s" % self.SIGNINGCERTIFICATEARN)

    def DoUpdate(self):
        self.BuildFirmwareFileNames()
        self.CopyFirmwareFileToS3()
        self.GetLatestS3FileVersion()
        self.CreateSigningProfile()
        self.CreateOTAJob()


def main(argv):
    ota = AWS_IoT_OTA()
    ota.DoUpdate()


if __name__ == "__main__":
    main(sys.argv[1:])
