#!/usr/bin/env bash

set -ea
svc=${svc:-np-webhook}
ns=${ns:-np-operator}
ca=`cat files/crt/k8s-ca.pem | base64 | tr -d '\n'`

create_csr(){
  kubectl apply -f files/csr.yml
}
approve_csr(){
  kubectl certificate approve np-operator
}
get_crt(){
  kubectl get csr np-operator -o jsonpath='{.status.certificate}' | openssl base64 -d -A -out files/crt/cert.pem
  kubectl get configmap -n kube-system extension-apiserver-authentication -o=jsonpath='{.data.client-ca-file}' > files/crt/k8s-ca.pem
}
conf_webhook(){
  svc_name=${1:-$svc}
  ns_name=${2:-$ns}

  if [ -z $svc_name ] || [ -z $ns_name ]; then
    return 1
  fi
  tmp_file=../examples/admission-webhook.yml
  install_file=../install/operator/admission-webhook.yml
  set +a
  envsubst < $tmp_file > $install_file
  kubectl apply -f $install_file
}
conf_webhook $*