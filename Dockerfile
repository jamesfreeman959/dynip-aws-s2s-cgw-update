FROM python:3.11
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Download and install AWS Signing Helper for IAM Roles Anywhere
RUN curl -LO https://rolesanywhere.amazonaws.com/releases/1.2.1/X86_64/Linux/aws_signing_helper && \
    chmod +x aws_signing_helper && \
    mv aws_signing_helper /usr/local/bin/

# Copy application
COPY main.py /app/main.py
RUN chmod 0755 /app/main.py

CMD ["/usr/local/bin/python3","-u","/app/main.py"]
