# AWS
Spot Instances usage in batch jobs

Architecture comprises of ECS clusters,Spot fleets and Auto-Scaling Groups to
take advantage of spot instances (spare compute capacity and cheap) .

Create an AWS Lambda Function to run periodically on ECS clusters to check the ECS
instances which have a high probability of getting terminated and set them to Draining.
Termination parameters can be customised.

Deploye the Lambda function to orchestrate our workloads seamlessly around any potential
interruptions by maintaining ASG' as backup.

Results in a workaround to the spot instance termination's 2-minute constraint. 
