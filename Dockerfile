FROM python:3.10-slim
# tag: registry.cn-hangzhou.aliyuncs.com/suyanhj/namespace-protect:0.1.0
# docker build -t registry.cn-hangzhou.aliyuncs.com/suyanhj/namespace-protect:0.1.0 --progress plain .
# docker push registry.cn-hangzhou.aliyuncs.com/suyanhj/namespace-protect:0.1.0

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    default_pkgs="net-tools curl procps"

RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt update && \
    apt install --no-install-recommends -y $default_pkgs && \
    apt clean all

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app
CMD kopf run --standalone --log-format=full --liveness http://0.0.0.0:8080  main/np_operator.py