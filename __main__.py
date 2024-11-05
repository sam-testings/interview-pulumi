import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx

config = pulumi.Config()

ecs_assume = aws.iam.role.Role(
    "ecs_assume",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Principal": {
              "Service": "ecs-tasks.amazonaws.com"
            },
            "Effect": "Allow",
            "Sid": ""
        }]
    }""")

# Add logging authorization
ecs_assume_logging_policy = aws.iam.Policy(
    "ecs_assume-logging-policy",
    path="/",
    description="IAM policy for logging",
    policy="""{
        "Version":"2012-10-17",
        "Statement":[{
            "Action":[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"],
            "Resource":"arn:aws:logs:*:*:*",
            "Effect":"Allow"}]
        }""")
ecs_assume_logging_policy_attachment = aws.iam.RolePolicyAttachment(
    "ecs_assume-logging-policy-attachment",
    role=ecs_assume.name,
    policy_arn=ecs_assume_logging_policy.arn
)

# Add ECR authorization
ecr_policy = aws.iam.Policy(
    "ecr-policy",
    path="/",
    description="IAM policy for ECR",
    policy="""{
        "Version":"2012-10-17",
        "Statement":[{
            "Action":[
                "ecr:GetAuthorizationToken",
                "ecr:BatchGetImage",
                "ecr:GetDownloadUrlForLayer"],
            "Resource":"*",
            "Effect":"Allow"}]
        }""")
ecr_policy_attachment = aws.iam.RolePolicyAttachment(
    "ecr-policy-attachment",
    role=ecs_assume.name,
    policy_arn=ecr_policy.arn
)

# Build repo
ecr_repository = awsx.ecr.Repository(
    "ecr-repository",
)

'''
created ecr image manually as kept getting error when using awsx.ecr.Image
docker build -t 148149772933.dkr.ecr.us-east-1.amazonaws.com/ecr-repository-08fa057 .
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 148149772933.dkr.ecr.us-east-1.amazonaws.com
docker push 148149772933.dkr.ecr.us-east-1.amazonaws.com/ecr-repository-08fa057

Could use local.command to do these commands, however unsure how this resolves with service creation. 
'''

'''
image = awsx.ecr.Image(
    "image",
    awsx.ecr.ImageArgs(
        repository_url=repository.url, 
        context="/app", 
        platform="linux/amd64"
    ),
)
'''

image_uri = "148149772933.dkr.ecr.us-east-1.amazonaws.com/ecr-repository-08fa057:latest"

cluster = aws.ecs.Cluster("cluster")
load_balancer = awsx.lb.ApplicationLoadBalancer("load-balancer")
log_group = aws.cloudwatch.LogGroup("log-group")

service = awsx.ecs.FargateService(
    "service",
    cluster=cluster.arn,
    assign_public_ip=True,
    task_definition_args=awsx.ecs.FargateServiceTaskDefinitionArgs(
        container=awsx.ecs.TaskDefinitionContainerDefinitionArgs(
            name='container',
            image=image_uri,
            cpu=128,
            memory=512,
            essential=True,
            port_mappings=[awsx.ecs.TaskDefinitionPortMappingArgs(
                target_group=load_balancer.default_target_group,
            )],
            environment=[awsx.ecs.TaskDefinitionKeyValuePairArgs(
                name="CUSTOM_VALUE",
                value=config.require("CUSTOM_VALUE"),
            )],
            log_configuration=awsx.ecs.TaskDefinitionLogConfigurationArgs(
                log_driver="awslogs",
                options={
                    "awslogs-region": aws.get_region().name,
                    "awslogs-group": log_group.name,
                    "awslogs-stream-prefix": "container",
                },
            )
        ),
        task_role=awsx.awsx.DefaultRoleWithPolicyArgs(
            role_arn=ecs_assume.arn,
        ),
        log_group=awsx.awsx.DefaultLogGroupArgs(
            existing=ExistingLogGroupArgs(
                arn=log_group.arn
            )
        ),
    )
)

# Export the repository URL and the load balancer URL
pulumi.export("repository_url", ecr_repository.url)
pulumi.export("url", pulumi.Output.concat("http://", load_balancer.load_balancer.dns_name))