# FROM public.ecr.aws/lambda/python:3.11
FROM public.ecr.aws/lambda/python:3.13


# Copy requirements first for better caching
COPY requirements.txt ${LAMBDA_TASK_ROOT}


RUN dnf update -y && \
   dnf install -y gcc gcc-c++ make python3-devel \
   freetype-devel libjpeg-turbo-devel zlib-devel \
   libffi-devel openssl-devel \
   libxml2-devel libxslt-devel && \
   pip install --upgrade pip && \
   pip install -r requirements.txt && \
   dnf clean all



# Copy function code
COPY . ${LAMBDA_TASK_ROOT}


# Set the CMD to your handler
CMD [ "lambda_office_extractor.lambda_handler" ]