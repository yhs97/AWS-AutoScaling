import boto3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
# Global variable to keep track of number of images uploaded by user
numInputImages = 0

# Landing Page
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global numInputImages
    uploaded_files = request.files.getlist('file[]')
    # print(uploaded_files)
    
    numInputImages += len(uploaded_files)
    print("Number of input images = ",numInputImages)
    s3 = boto3.client('s3')
    sqs = boto3.resource('sqs', region_name='us-east-1')
    queue = sqs.get_queue_by_name(QueueName='requestq')
    # queue = sqs.create_queue(QueueName='requestq')


    for uploaded_file in uploaded_files:
	    if uploaded_file.filename != '':
	    	uploaded_file.save(uploaded_file.filename)
            # Upload file to S3
	    	s3Response = s3.upload_file(uploaded_file.filename, 'ccnikbucket', uploaded_file.filename)
    		# Add image name to message body and send message to SQS request queue
            sqsResponse = queue.send_message(MessageBody=uploaded_file.filename)
    		print(uploaded_file.filename)

    return redirect(url_for('index'))

@app.route('/show_results')
def show_results():
    return render_template('show_results.html')

@app.route('/show_results', methods=['POST'])
def display_results():
    # global variable which keeps track of number of input images
    global numInputImages
    sqs = boto3.resource('sqs', region_name='us-east-1')
    sqsClient = boto3.client('sqs', region_name='us-east-1')
    # Get response queue
    queue = sqs.get_queue_by_name(QueueName='responseq')
    queueUrlResponse = sqsClient.get_queue_url(
        QueueName='responseq',
    )
    # Get response queue url needed further to query the queue for number of messages
    queue_url = queueUrlResponse['QueueUrl']
    print("queue_url = ",queue_url)
    
    # Get number of messages in the response queue
    attrResponse = sqsClient.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=[
            'ApproximateNumberOfMessages',
        ]
    )
    numOfMsgs = attrResponse['Attributes']['ApproximateNumberOfMessages']

    # Keep querying sqs queue for number of msgs until it is equal to number of input images
    # Exit out of the while loop when number of messages = number of uploaded images
    while(int(numOfMsgs) < numInputImages):
        attrResponse = sqsClient.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=[
                'ApproximateNumberOfMessages',
            ]
        )
        numOfMsgs = attrResponse['Attributes']['ApproximateNumberOfMessages']
       # print("num of messages inside = ",numOfMsgs)

    print("num of messages = ",numOfMsgs)

    # Create response list which will contain the classification results and will be sent to client
    responseList = []
    print(numInputImages)
    # Keep polling the response queue and add messages to response list 
    # Exit out of while loop when all the messages in the response queue have been added to response list 
    while(len(responseList) < int(numOfMsgs)):
        for message in queue.receive_messages(MaxNumberOfMessages=10, WaitTimeSeconds=1):
            # print("Inside receive_messages")
            print(message.body)
            responseList.append(message.body)
            message.delete()

   
    print(responseList)

    # Send response list to client
    return render_template('index.html', to_send=responseList)
