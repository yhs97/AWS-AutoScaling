import boto3
import os
import subprocess
import time


'''
Steps to set up Apptier
1. Create  EC2
ec2 = boto3.client('ec2','us-east-1')
conn = ec2.run_instances(InstanceType="t2.micro",
                             MaxCount=1,
                             MinCount=1,
                             ImageId="ami-0ee8cf7b8a34448a6",
                            KeyName="cc_nik",
                             SecurityGroupIds=[
                                 'sg-000ab5bea8b4ffc2e',
                             ]
                             )
2. Connect to EC2 via SSH(just update IP) -- ssh -i "cc_nik.pem" ubuntu@ec2-34-229-164-235.compute-1.amazonaws.com 
3. Go to your folder where your config and credential files are and run folowing commands
    scp -i cc_nik.pem config ubuntu@ec2-34-229-164-235.compute-1.amazonaws.com:/home/ubuntu/
    scp -i cc_nik.pem credentials ubuntu@ec2-34-229-164-235.compute-1.amazonaws.com:/home/ubuntu/
4. Update SQS and S3 names in this code as yours.
5. Go to your folder where your AppTier.py file is and run folowing command
    scp -i cc_nik.pem AppTier.py ubuntu@ec2-34-229-164-235.compute-1.amazonaws.com:/home/ubuntu/classifier/
6. Go to your folder where your Startup.sh file is and run folowing command
    scp -i cc_nik.pem Startup.sh ubuntu@ec2-34-229-164-235.compute-1.amazonaws.com:/home/ubuntu/classifier/
7. Go to the EC2 and run following commands:
    chmod +x startup.sh
    mkdir .aws
    cp config .aws/
    cp credentials .aws/
    crontab -e
    select option: 2
    Insert add last line as @reboot /home/ubuntu/startup.sh
8. If you want to shutdown instances after classification is done then uncomment last line in startup.sh

    print(conn)
'''
def classify():
    sqs = boto3.resource('sqs')
    # Get Request queue and its URL
    queue = sqs.get_queue_by_name(QueueName='requestq')
    queue_url = queue.url
    # Get Response queue and its URL
    res_queue = sqs.get_queue_by_name(QueueName='responseq')
    res_queue_url = res_queue.url
    s3_res = boto3.resource('s3')
    s3 = boto3.client('s3')
    # Names of the input and output buckets
    input_bucket = 'ccnikbucket'
    output_bucket = 'ccopbucket'
    print(queue_url, queue_url)
    #It keeps running the loop infinitly
    while True:
        code = 0
        # Read messages from Request queue. Holds for 20 sec until.
        messeges = queue.receive_messages(WaitTimeSeconds=20)
        print(len(messeges))
        fileName = ""
        # If message is present then it will proceede. Else, break the infinite loop and shutdown the apptier.
        if len(messeges):
            try:
                fileName = messeges[0].body #get the image fine name from the request message body e.g Test_0.JPEG
                print('Hello, {0}'.format(fileName))
                messeges[0].delete() #since this apptier will be working on the image it will delete its reference from the requestq
                s3_res.Bucket(input_bucket).download_file(fileName, fileName) #Download the image from i/p S3 bucket on app tier
                query = 'python3 image_classification.py '+fileName # e.g. python3 image_classification.py Test_0.JPEG
                # call the deep learning classification model
                result = str(subprocess.check_output(query, shell=True))
                if len(result) <= 5:
                    raise Exception
                result = result[2:-3] # Formatting the result of model
                print(result)
                image_name = str(fileName[:-5])
                sqs_response = "( "+image_name+" : "+result +" )"  # e.g (Test_0 : Curtain)
                print(sqs_response)
                '''
                Generate output text file and write the above sqs_response in it 
                e.g Test_0.text
                '''
                file_name = str(image_name)+".txt"
                print(file_name)
                f = open(file_name, "w")
                f.write(sqs_response)
                f.close()
                code = 1
                # Upload output file to S3 output bucket
                s3Response = s3.upload_file(file_name, output_bucket, file_name)
                # Send output in the responseq SQS
                response = res_queue.send_message(MessageBody=sqs_response)
                if response['ResponseMetadata']['HTTPStatusCode'] != 200:
                    raise Exception


            except Exception as e:
                '''
                Do to any error if we couldn't do or store the classification results then we are storing 
                the image name back to the request queue. So that other this or apptiers can classify it correctly
                '''
                print(e)
                res = queue.send_message(MessageBody=fileName)


        else:
            break


        time.sleep(5) #hold for 5 sec before going back to peeking request q.

def main():
    classify()


if __name__ == '__main__':
    main()