# FROM python:3.12-slim

# WORKDIR /code

# # Copy your dependencies tracker
# COPY ./requirements.txt ./

# # Install everything inside the container
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy the rest of your agent app
# COPY ./gebu_monitoring_agent ./gebu_monitoring_agent
# COPY ./skills ./skills
# COPY ./tools ./tools
# ARG COMMIT_SHA=""
# ENV COMMIT_SHA=${COMMIT_SHA}

# ARG AGENT_VERSION=0.0.0
# ENV AGENT_VERSION=${AGENT_VERSION}

# EXPOSE 8080

# # Run using standard uvicorn since it's installed globally in the container environment
# CMD ["uvicorn", "app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]

# Copyright 2026 Google LLC
# ... (licenses) ...

FROM python:3.12-slim

WORKDIR /code

# Copy your dependencies tracker
COPY ./requirements.txt ./

# Install everything inside the container
RUN pip install --no-cache-dir -r requirements.txt

# Copy the core agent directories based on your exact structure
COPY ./app ./app
COPY ./skills ./skills
COPY ./tools ./tools

ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}

EXPOSE 8080

# Run using standard uvicorn since it's installed globally in the container environment
# Your fast_api_app.py is inside the 'app' directory!
CMD ["uvicorn", "app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]