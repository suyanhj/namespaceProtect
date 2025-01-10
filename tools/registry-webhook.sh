#!/usr/bin/env bash

set -ea
svc=${svc:-np-webhook}
ns=${ns:-np-operator}


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
  svc_name=${1:-$svc}
  ns_name=${2:-$ns}
  ca=`base64 files/crt/ca.crt`

  if [ -z $svc_name ] || [ -z $ns_name ]; then
    return 1
  fi
  tmp_file=../examples/admission-webhook.yml
  install_file=../install/operator/admission-webhook.yml
  set +a
  envsubst < $tmp_file > $install_file
  kubectl apply -f $install_file
}
conf_cm(){
  svc_name=${1:-$svc}
  ns_name=${2:-$ns}

  kubectl create cm webhook-crt \
  --from-file=ca.crt=files/crt/ca.crt \
  --from-file=server.key=files/crt/server.key \
  --from-file=server.pem=files/crt/server.pem \
  -n $ns_name

}
main(){
#  create_csr
#  approve_csr
#  get_crt
  conf_webhook $*
  conf_cm $*
}
main $*