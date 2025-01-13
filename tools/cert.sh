#!/usr/bin/env bash

set -e
_svc=${1:-$svc}
_ns=${2:-$ns}
_ip=${3:-$ip}
svc=${_svc:-np-webhook}
ns=${_ns:-np-operator}
ip=${_ip:-127.0.0.1}
work_dir=files
conf_dir=conf
crt_dir=crt
days=3650
ca_subj='/O=ca-hj/CN=ca.hj.com'

if [ -z $svc ] || [ -z $ns ]; then
  exit 1
fi

gen_ca(){
  if [ -f $crt_dir/ca.key -a -f $crt_dir/ca.crt ] ;then
    echo -e "已有ca证书"
  else
    openssl genrsa -out $crt_dir/ca.key 2048
    openssl req -new -x509 -key $crt_dir/ca.key -out $crt_dir/ca.crt -nodes -days $days -subj $ca_subj
  fi
}
gen_key(){
  if [ -f $crt_dir/server.key ] ;then
    echo -e "已有私钥"
  else
    openssl genrsa -out $crt_dir/server.key 2048
  fi
}
san_conf(){
  tee > $conf_dir/san.conf <<eof
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
DNS.1 = $svc
DNS.2 = $svc.$ns
DNS.3 = $svc.$ns.svc
IP.1 = $ip
eof
}
gen_csr(){
  openssl req -new -key $crt_dir/server.key -subj "/CN=$svc.$ns.svc" -out $crt_dir/svc.csr -config $conf_dir/san.conf
}
issue_crt(){
  openssl x509 -req -days $days -in $crt_dir/svc.csr -CA $crt_dir/ca.crt -CAkey $crt_dir/ca.key -CAcreateserial -out $crt_dir/server.crt -extensions v3_req -extfile $conf_dir/san.conf
  cat $crt_dir/server.crt $crt_dir/ca.crt > $crt_dir/server.pem
}
gen_yml(){
  tee > csr.yml <<EOF
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: np-operator
spec:
  signerName: "kubernetes.io/kubelet-serving"
  groups:
  - system:authenticated
  request: $(cat $crt_dir/svc.csr | base64 | tr -d '\n')
  usages:
  - digital signature
  - key encipherment
  - server auth
EOF
}

main(){
  [ -d $work_dir/conf ] || mkdir -p $work_dir/{crt,conf}
  cd $work_dir
  gen_ca
  gen_key
  san_conf $@
  gen_csr $@
  issue_crt
  #gen_yml
}
main $@