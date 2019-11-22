import boto3
import datetime


ec2 = boto3.client('ec2')
ecs = boto3.client('ecs')
asg=boto3.client('autoscaling')

def check_price(type) :
    results = []
    instance = type
    max_price = 0.5
    prices = ec2.describe_spot_price_history(
          AvailabilityZone='us-east-1',
          EndTime=datetime.datetime.now().isoformat(),
          InstanceTypes=[instance],
          ProductDescriptions=['Linux/UNIX', 'Linux/UNIX (Amazon VPC)'],
          StartTime=(datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat(),
          MaxResults=10
    )
    for price in prices["SpotPriceHistory"]:
        results.append((price["AvailabilityZone"], price["SpotPrice"], price["Timestamp"]))

    res = [lis[1] for lis in results]
    res.sort(reverse=True)
    p = float(res[0])
    x = 0.7 * max_price
    y = 0.9 * max_price
    if (p <= x):
        return 1
    else:
        if (p>=y):
            return 2
        else :
            return 3


def spot(request_id,capacity) :
    ec2.modify_spot_fleet_request(
        SpotFleetRequestId=request_id,
        TargetCapacity=capacity,
    )


def on_demand(name,capacity) :
    response=asg.update_auto_scaling_group(
        AutoScalingGroupName=name,
        MinSize=capacity,
        MaxSize=capacity,
        DesiredCapacity=capacity,
    )
    print(response)



def drain_ecs_instance(ecs_cluster, ecs_instance):
    print("Sending a DRAINING request...")
    drain = ecs.update_container_instances_state(cluster=ecs_cluster, containerInstances=[ecs_instance], status='DRAINING')
    if drain['containerInstances'][0]['status'] == 'DRAINING':
       print("Successfully set container instance status to DRAINING.")
    else:
       print("Something went wrong.")




def get_ecs_instance(ecs_cluster):
    list_instances = ecs.list_container_instances(cluster=ecs_cluster, status = 'ACTIVE')['containerInstanceArns']
    if (len(list_instances) != 0):
        describe_instances = ecs.describe_container_instances(cluster=ecs_cluster,containerInstances=list_instances)['containerInstances']

        for e in describe_instances:
            ecs_instance = e['containerInstanceArn']
            instance_id= e['ec2InstanceId']

            ec2_type = ec2.describe_instance_attribute(Attribute='instanceType',InstanceId=instance_id)
            t=ec2_type['InstanceType']['Value']
            flag=check_price(t)
            if (flag == 2):
                sp=ec2.describe_instances(InstanceIds=[instance_id])
                for spo in sp['Reservations']:
                    for i in spo['Instances']:
                        if (i['InstanceLifecycle'] == 'spot'):
                            drain_ecs_instance(ecs_cluster, ecs_instance)


def drain_ec2_cluster(ecs_cluster):
    list_instances = ecs.list_container_instances(cluster=ecs_cluster, status='ACTIVE')['containerInstanceArns']
    if(len(list_instances)!=0):
        describe_instances = ecs.describe_container_instances(cluster=ecs_cluster, containerInstances=list_instances)['containerInstances']
        for e in describe_instances:
            ecs_instance = e['containerInstanceArn']
            instance_id = e['ec2InstanceId']

            sp = ec2.describe_instances(InstanceIds=[instance_id])
            for spo in sp['Reservations']:
                for i in spo['Instances']:
                    if (i['InstanceLifecycle'] != 'spot'):
                        drain_ecs_instance(ecs_cluster, ecs_instance)

def count_ecs_instance(ecs_cluster):

    describe_ecs=ecs.describe_cluster(clusters=[ecs_cluster])['clusters']
    for e in describe_ecs:
        flag=e['registeredContainerInstancesCount']
    if(flag>0):
        return True
    else :
        return False



def lambda_handler() :
    type='t3.micro'
    request_id=event['spotfleetrequestid']      #take spotfleetrequestid as input
    name=event['autoscalinggroupname']          #take autoscalinggroupname as input
    capacity=event['instancecount']             #take capacity required as input
    ecs_cluster = event['cluster_name']         #take ecs cluster name as input
    check=count_ecs_instance(ecs_cluster)
    flag=check_price(type)
    if(flag==1) :
        spot(request_id,capacity)
        drain_ec2_cluster(ecs_cluster)
        on_demand(name,0)
    else :
        if(flag==2):
            if (check == True):
                print("*Check ECS cluster:* " + ecs_cluster)
                get_ecs_instance(ecs_cluster)
                on_demand(name, capacity)
                spot(request_id,0)
            else:
                on_demand(name,capacity)
        else:
            if (check == True):
                print("Working Fine.")
            else:
                on_demand(name,capacity)

    return {}

lambda_handler()



















