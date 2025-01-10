#!/usr/bin/env bash

# docker build -t registry.cn-hangzhou.aliyuncs.com/suyanhj/namespace-protect-operator:0.1.0 --progress plain -e run_app=operator .
# docker build -t registry.cn-hangzhou.aliyuncs.com/suyanhj/namespace-protect-webhook:0.1.0 --progress plain -e run_app=webhook .

set -e

img_hub=registry.cn-hangzhou.aliyuncs.com/suyanhj/namespace-protect
default_tag=0.1.0

arg_check(){
  if [ `echo $*|wc -w` = 0 ]; then
    echo 必须传递镜像名，支持多个，格式: name:tag
    echo "仅支持镜像名: operator | webhook"
    return 1
  fi
}
main(){
  while :; do
    if [ `echo $1|wc -w` -eq 0 ]; then
      return 0
    fi
    if [[ $1 =~ [[:alpha:]-]+ ]] ;then
      name=${BASH_REMATCH}
      if [[ $1 =~ ([[:alpha:]-]+):(.*)$ ]] ;then
        name=${BASH_REMATCH[1]}
        tag=${BASH_REMATCH[2]}
      fi
      tag=${tag:-$default_tag}
    else
      echo $1 不符合规范
      return 1
    fi
    img=$img_hub-$name:$tag
    docker build -t $img --build-arg run_app=$name . > /dev/null
#    docker build -t $img --progress plain --build-arg run_app=$name . > /dev/null
    docker push $img > /dev/null
    shift
  done
}
prinf_img(){
  [ -f Dockerfile ] || cd ..
  arg_check $*
  main $*
  echo
  echo '##### 镜像名 #####'
  for i in $*; do
    echo $i |egrep :.* && echo $img_hub-$i ||echo $img_hub-$i:$default_tag
  done
}
prinf_img $*
