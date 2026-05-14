FROM public.ecr.aws/lambda/python:3.13-arm64

WORKDIR /var/task

# Copy requirements.txt and install dependencies
COPY reviewUI/src/requirements.txt .
RUN pip install -r requirements.txt

# Copy repo-wide common code (ui/common → container:/var/task/common)
COPY common/ common/

# Copy source code
COPY reviewUI/src/ .

CMD ["app.lambda_handler"]