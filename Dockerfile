FROM python:3.10-slim
# tag: harbor.baker18.com/mid/python:3.10-slim-node18
# docker build -t harbor.baker18.com/mid/python:3.10-slim-node18 --progress plain .
# docker push harbor.baker18.com/mid/python:3.10-slim-node18

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    default_pkgs="net-tools curl procps xz-utils  python3-dev"

RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt update && \
    apt install --no-install-recommends -y $default_pkgs && \
    apt clean all

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app
CMD kopf run --standalone --verbose --log-format=full --liveness http://0.0.0.0:80  /app/main/np-operator.py