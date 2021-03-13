import boto3
import time
import threading
import sys

ec2_client = boto3.client('ec2', region_name='us-east-1')
ec2_resource = boto3.resource('ec2', region_name='us-east-1')
msgCount = 1
threshold = 0
exit = 0
AMI='ami-042e8287309f5df03'

def getInstancesStates(stoppedInstances, runningInstances):
    for instance in ec2_resource.instances.all():
        if instance.state['Name'] == 'stopped':
            stoppedInstances.append(instance)
        elif instance.state['Name'] == 'running':
            runningInstances.append(instance)


def startInstances(cnt):
    # We work with a maximum of 19 app tier instances
    if cnt > 19:
        cnt = 19
    for instance in ec2_resource.instances.all():
        if instance.state['Name'] == 'pending':
            cnt-=1
        if instance.state['Name'] == 'stopped':
            instance.start()
            cnt -=1
            # if there are no instances to start just break
            if cnt<=0:
                break
    #if cnt>0:
    #    ec2_client.run_instances(InstanceType="t2.micro",MaxCount=cnt, MinCount=1, ImageId=AMI)

    #time.sleep(30)


def stopInstances(cnt):
    for instance in ec2_resource.instances.all():
        if instance.state['Name'] == 'running':
            instance.stop()
            cnt -=1
            if cnt<=0:
                break

# Not used in our implementation
def terminateInstances(cnt):
    for instance in ec2_resource.instances.all():
        if instance.state['Name'] == 'stopped':
            instance.terminate()
            cnt -=1
            if cnt<=0:
                break

def controller():
    sqs = boto3.resource('sqs', region_name='us-east-1')

    while True:
        # Get request queue
        queue = sqs.get_queue_by_name(QueueName='requestq')
        # Get number of messages in the request queue
        msgCount = queue.attributes['ApproximateNumberOfMessages']
        # Sometimes number of messages value may be wrong, so check again 
        time.sleep(5)
        msgCount = queue.attributes['ApproximateNumberOfMessages']
        print("Message count = ",msgCount)
        stoppedInstances=[]
        runningInstances=[]
        # Get the number of stopped instances and number of running instances 
        getInstancesStates(stoppedInstances, runningInstances)
        numRunning = len(runningInstances)
        print("Number of instances running = ",numRunning)
        buf = int(msgCount) - threshold
        # Case when num of msgs < num of available instances
        if buf > 0 and buf < 20:
            if buf > 0 and buf > (numRunning-1):
                print("Starting {} instances".format(buf-numRunning+1))
                startInstances(buf - numRunning + 1)
                time.sleep(25)
                
        # Case when number of images(msgs) > num of available instances 
        else:
            if buf > 0:
                startInstances(buf)

            # if buf <= 0:
            #     terminateInstances(19)

            time.sleep(3) #Sleep 3 secs


def runController():
    id = threading.Thread(target=controller, args=[])
    id.start()
    id.join()

def test():
    print("Yolo")

if __name__ == "__main__":
    runController()
