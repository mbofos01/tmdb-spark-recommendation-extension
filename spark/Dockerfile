FROM apache/spark:3.5.1

USER root

# Install Python dependencies
RUN apt-get update && apt-get install -y python3-pip && \
    pip install --no-cache-dir numpy pandas python-dotenv redis 

USER root
