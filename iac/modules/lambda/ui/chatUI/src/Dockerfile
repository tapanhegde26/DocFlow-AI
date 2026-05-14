FROM public.ecr.aws/lambda/python:3.12-arm64

WORKDIR /var/task

COPY chatUI/src/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip list

# Copy repo-wide common code (ui/common → container:/var/task/common)
COPY common/ common/

COPY chatUI/src/ .

CMD ["app.lambda_handler"]
