#!/usr/bin/env bash

set -ea

type=${1:-svc} #注册方式: svc | url
_svc=${2:-$svc}
_ns=${3:-$ns}
_ip=${4:-$ip}
svc=${_svc:-np-webhook}
ns=${_ns:-np-operator}
ip=${_ip:-192.168.10.81}  #url时注册ip

if [ -z $svc ] || [ -z $ns ]; then
  exit 1
fi
  
create_csr(){
  kubectl apply -f files/csr.yml
}
approve_csr(){
  kubectl certificate approve np-operator
}
get_crt(){
  kubectl get csr np-operator -o jsonpath='{.status.certificate}' | openssl base64 -d -A -out files/crt/cert.pem
  kubectl get cm -n kube-system kube-root-ca.crt -o=jsonpath='{.data.ca\.crt}' > files/crt/k8s-ca.pem
}
conf_webhook(){
  ca=`base64 files/crt/ca.crt`
  os=`uname -s`
  tmp_file=../examples/admission-webhook.yml
  install_file=../install/operator/admission-webhook.yml
  set +a

  if [ $type = url ] ;then
    if [ $os = 'Darwin' ] ;then
      envsubst < $tmp_file |sed -E -e '/service:/,/port:/d' -e 's@^#(.*url.*)@\1@' > $install_file
    else
      envsubst < $tmp_file |sed -r -e '/service:/,/port:/d' -e 's@^#(.*url.*)@\1@' > $install_file
    fi
  fi
  kubectl apply -f $install_file
}
conf_cm(){
  kubectl create cm webhook-crt \
  --from-file=ca.crt=files/crt/ca.crt \
  --from-file=server.key=files/crt/server.key \
  --from-file=server.pem=files/crt/server.pem \
  -n $ns --dry-run=client -o yaml |grep -v creationTimestamp |kubectl apply -f -
}
main(){
#  create_csr
#  approve_csr
#  get_crt
  conf_webhook
  conf_cm
}
main $*