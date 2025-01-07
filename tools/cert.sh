#!/usr/bin/env bash

set -e
svc=${svc:-np-operator}
ns=${ns:-$svc}
ip=${ip:-127.0.0.1}
work_dir=files



gen_key(){
  openssl genrsa -out crt/private.key 2048
}

conf_csr(){
  svc_name=${1:-$svc}
  ns_name=${2:-$ns}
  ip_addr=${3:-$ip}

  if [ -z $svc_name ] || [ -z $ns_name ]; then
    return 1
  fi
  tee > conf/csr.conf <<eof
[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = $svc_name
DNS.2 = $svc_name.$ns_name
DNS.3 = $svc_name.$ns_name.svc
IP.1 = $ip_addr
eof
}
gen_csr(){
  svc_name=${1:-$svc}
  ns_name=${2:-$ns}
  openssl req -new -key crt/private.key -subj "/CN=$svc_name.$ns_name.svc" -out conf/svc.csr -config conf/csr.conf
}
gen_yml(){
  tee > csr.yml <<EOF
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: np-operator
spec:
  signerName: "kubernetes.io/kube-apiserver-client"
  groups:
  - system:authenticated
  request: $(cat svc.csr | base64 | tr -d '\n')
  usages:
  - digital signature
  - key encipherment
  - client auth
EOF
}
main(){
  [ -z $work_dir ] && mkdir -p $work_dir/{crt,conf} && cd $work_dir
  [ -f crt/private.key ] || gen_key
  conf_csr $@
  gen_csr $@
  gen_yml
}
main $@