algorithm_name=gpt-sovits-inference

account=$(aws sts get-caller-identity --query Account --output text)

# Get the region defined in the current configuration (default to us-west-2 if none defined)
region=$(aws configure get region)

fullname="${account}.dkr.ecr.${region}.amazonaws.com/${algorithm_name}:latest"

# If the repository doesn't exist in ECR, create it.

aws ecr describe-repositories --repository-names "${algorithm_name}" > /dev/null 2>&1
if [ $? -ne 0 ]
then
echo "create repository:" "${algorithm_name}"
aws ecr create-repository --repository-name "${algorithm_name}" > /dev/null
fi

#load public ECR image
#aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws

# Log into Docker
pwd=$(aws ecr get-login-password --region ${region})
docker login --username AWS -p ${pwd} ${account}.dkr.ecr.${region}.amazonaws.com


git clone -b stream https://github.com/qingyuan18/GPT-SoVITS.git
docker build -t ${algorithm_name}  ./ -f ./Dockerfile-sagemaker
docker tag ${algorithm_name} ${fullname}
docker push ${fullname}
rm -rf ./GPT-SoVITS