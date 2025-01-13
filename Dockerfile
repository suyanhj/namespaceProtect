FROM python:3.10-slim

WORKDIR /app
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt update && \
    apt install --no-install-recommends -y net-tools curl procps libssl-dev nginx inotify-tools && \
    apt clean all

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY . /app

RUN chmod +x tools/run.sh && \
    cp examples/nginx.conf /etc/nginx

#支持：operator、webhook
ARG run_app=operator
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    app=${run_app}
CMD tools/run.sh