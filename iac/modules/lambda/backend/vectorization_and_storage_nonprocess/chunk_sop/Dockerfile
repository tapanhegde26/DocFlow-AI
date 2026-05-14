FROM public.ecr.aws/lambda/python:3.13

# Set the working directory to the Lambda task root
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy application files
COPY src/app.py .
COPY requirements.txt .

# Install dependencies. Use 'pip' instead of 'pip3' here, as 'pip' is symlinked to 'pip3' in the Lambda Docker images.
# Also, correct the typo 'tct' to 'txt'.
RUN pip install -r requirements.txt

# Command to execute the Lambda handler
CMD ["app.lambda_handler"]