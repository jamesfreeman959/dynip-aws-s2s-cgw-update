FROM python:3.11
WORKDIR /app
RUN pip3 install boto3 requests schedule
COPY main.py /app/main.py
RUN chmod 0755 /app/main.py

CMD ["/usr/local/bin/python3","-u","/app/main.py"]
