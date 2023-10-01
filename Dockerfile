FROM python:3.11
RUN apt-get update && apt-get -y install cron vim && apt-get clean
WORKDIR /app
RUN pip3 install boto3
COPY crontab /etc/cron.d/crontab
COPY main.py /app/main.py
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/bin/crontab /etc/cron.d/crontab

# run crond as main process of container
CMD ["cron", "-f"]