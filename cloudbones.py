#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

ROOTS = ["infra","apps/k8s","py","cheats"]

TEMPLATES = {
    ("infra","providers.tf"): "terraform {\n  required_version = \">= 1.5.0\"\n}\nprovider \"aws\" {\n  region = var.region\n}\n",
    ("infra","versions.tf"): "terraform {\n  required_providers {\n    aws = { source = \"hashicorp/aws\", version = \"~> 5.0\" }\n  }\n}\n",
    ("infra","variables.tf"): "variable \"region\" { type = string  default = \"eu-central-1\" }\nvariable \"cluster_name\" { type = string default = \"pp-eks\" }\n",
    ("infra","vpc.tf"): "module \"vpc\" {\n  source  = \"terraform-aws-modules/vpc/aws\"\n  version = \"~> 5.0\"\n  name = \"pp-vpc\"\n  cidr = \"10.0.0.0/16\"\n  azs = [\"eu-central-1a\",\"eu-central-1b\"]\n  public_subnets  = [\"10.0.0.0/24\",\"10.0.1.0/24\"]\n  private_subnets = [\"10.0.10.0/24\",\"10.0.11.0/24\"]\n  enable_nat_gateway = true\n  single_nat_gateway = true\n  tags = { Project=\"CloudBones\", Environment=\"dev\" }\n}\n",
    ("infra","eks.tf"): "module \"eks\" {\n  source  = \"terraform-aws-modules/eks/aws\"\n  version = \"~> 20.0\"\n  cluster_name    = var.cluster_name\n  cluster_version = \"1.29\"\n  vpc_id     = module.vpc.vpc_id\n  subnet_ids = module.vpc.private_subnets\n  eks_managed_node_groups = {\n    default = {\n      min_size = 1\n      max_size = 3\n      desired_size = 1\n      instance_types = [\"t3.large\"]\n      capacity_type  = \"ON_DEMAND\"\n    }\n  }\n  tags = { Project=\"CloudBones\", Environment=\"dev\" }\n}\n",
    ("infra","outputs.tf"): "output \"cluster_name\"     { value = module.eks.cluster_name }\noutput \"cluster_endpoint\" { value = module.eks.cluster_endpoint }\noutput \"cluster_ca\"       { value = module.eks.cluster_certificate_authority_data }\n",
    ("apps/k8s","deploy.yaml"): "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: echo\n  labels: { app: echo }\nspec:\n  replicas: 2\n  selector: { matchLabels: { app: echo } }\n  template:\n    metadata: { labels: { app: echo } }\n    spec:\n      containers:\n      - name: http-echo\n        image: hashicorp/http-echo:0.2.3\n        args: [\"-text=hello\"]\n        ports: [{ containerPort: 5678 }]\n        readinessProbe:\n          httpGet: { path: \"/\", port: 5678 }\n          initialDelaySeconds: 2\n          periodSeconds: 5\n        livenessProbe:\n          httpGet: { path: \"/\", port: 5678 }\n          initialDelaySeconds: 5\n          periodSeconds: 10\n",
    ("apps/k8s","service.yaml"): "apiVersion: v1\nkind: Service\nmetadata:\n  name: echo\n  labels: { app: echo }\nspec:\n  selector: { app: echo }\n  ports:\n    - port: 80\n      targetPort: 5678\n  type: LoadBalancer\n",
    ("apps/k8s","hpa.yaml"): "apiVersion: autoscaling/v2\nkind: HorizontalPodAutoscaler\nmetadata:\n  name: echo-hpa\nspec:\n  scaleTargetRef:\n    apiVersion: apps/v1\n    kind: Deployment\n    name: echo\n  minReplicas: 2\n  maxReplicas: 6\n  metrics:\n  - type: Resource\n    resource:\n      name: cpu\n      target:\n        type: Utilization\n        averageUtilization: 50\n",
    ("py","list_buckets.py"): "import boto3\ns3=boto3.client(\"s3\")\nfor b in s3.list_buckets().get(\"Buckets\",[]):\n    print(b[\"Name\"])\\n",
    ("","README.md"): "# pp-live-bones\\n\\ninfra/ (Terraform), apps/k8s/ (K8s), py/ (boto3).\\n\\nSteps:\\n1) aws configure\\n2) cd infra && terraform init && terraform apply\\n3) aws eks update-kubeconfig --region eu-central-1 --name pp-eks\\n4) kubectl get nodes\\n5) kubectl apply -f apps/k8s/deploy.yaml\\n6) kubectl apply -f apps/k8s/service.yaml\\n7) kubectl get svc echo -w\\n8) kubectl scale deploy/echo --replicas=4\\n9) python py/list_buckets.py\\n\\nCleanup: delete k8s objects; cd infra && terraform destroy\\n",
}

SERVERLESS = {
    ("infra","main.tf"): "terraform {\n  required_version = \">= 1.5.0\"\n  required_providers { aws = { source = \"hashicorp/aws\", version = \"~> 5.0\" } }\n}\nprovider \"aws\" { region = var.region }\nvariable \"region\" { type = string, default = \"eu-central-1\" }\nresource \"aws_iam_role\" \"lambda_exec\" {\n  name = \"cloudbones_lambda_exec\"\n  assume_role_policy = jsonencode({Version=\"2012-10-17\",Statement=[{Action=\"sts:AssumeRole\",Effect=\"Allow\",Principal={Service=\"lambda.amazonaws.com\"}}]})\n}\nresource \"aws_iam_role_policy_attachment\" \"basic\" {\n  role = aws_iam_role.lambda_exec.name\n  policy_arn = \"arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole\"\n}\nresource \"aws_lambda_function\" \"hello\" {\n  function_name = \"cloudbones_hello\"\n  role = aws_iam_role.lambda_exec.arn\n  handler = \"handler.hello\"\n  runtime = \"python3.11\"\n  filename = \"${path.module}/lambda.zip\"\n}\nresource \"aws_apigatewayv2_api\" \"http\" { name = \"cloudbones-http-api\" protocol_type = \"HTTP\" }\nresource \"aws_apigatewayv2_integration\" \"lambda\" {\n  api_id = aws_apigatewayv2_api.http.id\n  integration_type = \"AWS_PROXY\"\n  integration_uri  = aws_lambda_function.hello.invoke_arn\n  payload_format_version = \"2.0\"\n}\nresource \"aws_apigatewayv2_route\" \"root\" { api_id = aws_apigatewayv2_api.http.id route_key = \"GET /\" target = \"integrations/${aws_apigatewayv2_integration.lambda.id}\" }\nresource \"aws_apigatewayv2_stage\" \"default\" { api_id = aws_apigatewayv2_api.http.id name = \"$default\" auto_deploy = true }\noutput \"http_endpoint\" { value = aws_apigatewayv2_api.http.api_endpoint }\n",
    ("py","handler.py"): "def hello(event, context):\n    return {\"statusCode\":200,\"headers\":{\"content-type\":\"text/plain\"},\"body\":\"hello\"}\n",
}

ECS = {
    ("infra","ecs.tf"): "terraform {\n  required_version = \">= 1.5.0\"\n  required_providers { aws = { source = \"hashicorp/aws\", version = \"~> 5.0\" } }\n}\nprovider \"aws\" { region = var.region }\nvariable \"region\" { type = string, default = \"eu-central-1\" }\n",
}

def write_file(p: Path, data: str, force: bool):
    if p.exists() and not force:
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data, encoding='utf-8')

def scaffold(dest: Path, force: bool, stack: str):
    for d in ROOTS:
        (dest/d).mkdir(parents=True, exist_ok=True)
    for (sub, name), data in TEMPLATES.items():
        write_file(dest / sub / name if sub else dest / name, data, force)
    if stack == "serverless":
        for (sub, name), data in SERVERLESS.items():
            write_file(dest / sub / name, data, force)
    if stack == "ecs":
        for (sub, name), data in ECS.items():
            write_file(dest / sub / name, data, force)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="pp-live-bones")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--stack", choices=["eks","serverless","ecs"], default="eks")
    a = ap.parse_args()
    scaffold(Path(a.dest).resolve(), a.force, a.stack)

if __name__ == "__main__":
    main()
