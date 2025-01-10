#!/usr/bin/env bash

set -e
svc=${svc:-np-webhook}
ns=${ns:-np-operator}
ip=${ip:-127.0.0.1}
work_dir=files
conf_dir=conf
crt_dir=crt
days=3650
ca_subj='/O=ca-hj/CN=ca.hj.com'

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
  svc_name=${1:-$svc}
  ns_name=${2:-$ns}
  ip_addr=${3:-$ip}

  if [ -z $svc_name ] || [ -z $ns_name ]; then
    return 1
  fi
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
DNS.1 = $svc_name
DNS.2 = $svc_name.$ns_name
DNS.3 = $svc_name.$ns_name.svc
IP.1 = $ip_addr
eof
}
gen_csr(){
  svc_name=${1:-$svc}
  ns_name=${2:-$ns}

  openssl req -new -key $crt_dir/server.key -subj "/CN=$svc_name.$ns_name.svc" -out $crt_dir/svc.csr -config $conf_dir/san.conf
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