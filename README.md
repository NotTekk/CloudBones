# CloudBones — minimal infra “bones” scaffolder

`cloudbones.py` generates a clean, minimal skeleton for cloud test tasks so you can configure everything **live** (e.g., interviews, workshops). It writes files only—no resources are created.

## Features
- **EKS**: Terraform VPC + EKS, tiny K8s app (Deployment/Service/HPA)
- **Serverless**: API Gateway + Lambda (Python handler)
- **ECS**: Fargate placeholder (start points)

## Quick start
```bash
# default: creates ./pp-live-bones with EKS skeleton
python cloudbones.py

# variants
python cloudbones.py --stack serverless
python cloudbones.py --stack ecs

# overwrite existing
python cloudbones.py --force

# choose output directory
python cloudbones.py --dest my-sandbox
```

## Generated layout (EKS)
```
pp-live-bones/
├─ infra/
│  ├─ providers.tf
│  ├─ versions.tf
│  ├─ variables.tf
│  ├─ vpc.tf
│  ├─ eks.tf
│  └─ outputs.tf
├─ apps/k8s/
│  ├─ deploy.yaml
│  ├─ service.yaml
│  └─ hpa.yaml
├─ py/
│  └─ list_buckets.py
├─ cheats/
│  ├─ kubectl.md
│  ├─ terraform.md
│  └─ aws-python.md
└─ README.md
```

## Manual demo flow
```bash
aws configure
aws sts get-caller-identity

cd infra
terraform init
terraform apply

aws eks update-kubeconfig --region eu-central-1 --name pp-eks
kubectl get nodes

kubectl apply -f ../apps/k8s/deploy.yaml
kubectl apply -f ../apps/k8s/service.yaml
kubectl get svc echo -w
curl http://<EXTERNAL-IP>/

# fallback if LoadBalancer pending
kubectl patch svc echo -p '{"spec":{"type":"NodePort"}}'
kubectl port-forward deploy/echo 8080:5678
curl http://localhost:8080/

kubectl scale deploy/echo --replicas=4

python ../py/list_buckets.py

# cleanup
kubectl delete -f ../apps/k8s/ --ignore-not-found
cd ../infra && terraform destroy
```

## Requirements
- Python 3.8+
- (When provisioning) AWS CLI, Terraform ≥ 1.5, kubectl, boto3
