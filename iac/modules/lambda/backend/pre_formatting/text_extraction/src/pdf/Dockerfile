FROM public.ecr.aws/lambda/python:3.11

# Copy requirements first for better caching
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Use dnf if available, otherwise fallback to yum
RUN (command -v dnf >/dev/null 2>&1 && dnf clean all && dnf update -y && \
    dnf install -y gcc gcc-c++ make python3-devel \
    freetype-devel libjpeg-turbo-devel zlib-devel \
    libffi-devel libxml2-devel libxslt-devel && \
    dnf clean all) || \
    (yum clean all && yum update -y && \
    yum install -y gcc gcc-c++ make python3-devel \
    freetype-devel libjpeg-turbo-devel zlib-devel \
    libffi-devel libxml2-devel libxslt-devel && \
    yum clean all) && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy function code
COPY . ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD [ "lambda_pdf_extractor.lambda_handler" ]
