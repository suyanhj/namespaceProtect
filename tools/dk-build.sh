#!/usr/bin/env bash

# docker build -t registry.cn-hangzhou.aliyuncs.com/suyanhj/namespace-protect-operator:0.1.0 --progress plain -e run_app=operator .
# docker build -t registry.cn-hangzhou.aliyuncs.com/suyanhj/namespace-protect-webhook:0.1.0 --progress plain -e run_app=webhook .

set -e

img_hub=registry.cn-hangzhou.aliyuncs.com/suyanhj/namespace-protect
default_tag=0.2.1

arg_check(){
  if [ `echo $*|wc -w` = 0 ]; then
    echo 必须传递镜像名，支持多个，格式: name:tag
    echo "仅支持镜像名: operator | webhook"
    return 1
  fi
}
chk_img(){
  if [[ $1 =~ _ ]] ;then
    echo $1 不符合规范 && return 1
  elif [[ $1 =~ [[:alpha:]-]+$ ]] ;then
    name=${BASH_REMATCH}
    tag=${tag:-$default_tag}
    [ -z $name ] && echo $1 不符合规范 && return 1 || echo $img_hub-$name:$tag
  elif [[ $1 =~ ([[:alpha:]-]+):(.*)$ ]] ;then
    name=${BASH_REMATCH[1]}
    tag=${BASH_REMATCH[2]}
    [ -z $name ] && echo $1 不符合规范 && return 1 || echo $img_hub-$name:$tag
  else
    echo $1 不符合规范 && return 1
  fi
}
build_img(){
  [ -f Dockerfile ] || cd ..
  arg_check $*
  while :; do
    if [ `echo $1|wc -w` -eq 0 ]; then
      return 0
    fi
    img=`chk_img $1`
    name=${1%:*}
    docker build -t $img --build-arg run_app=$name . > /dev/null
#    docker build -t $img --progress plain --build-arg run_app=$name . > /dev/null
    docker push $img > /dev/null
    shift
  done
}
print_img(){
  echo
  echo '##### 镜像名 #####'
  for i in $*; do
    chk_img $i
  done
}
edit_file(){
  os=`uname -s`
  if [ $os = 'Darwin' ] ;then
    sed -i "" "s#image: .*#image: $img#g" $1
  else
    sed -i "s#image: .*#image: $img#g" $1
  fi
}
conf_img(){
  cd install/deploy
  for i in $*; do
    img=`chk_img $i`
    if [[ $i =~ operator ]] ;then
       edit_file *operator.yml
    elif [[ $i =~ webhook ]]; then
       edit_file *webhook.yml
    fi
  done

}
main(){
  build_img $*
  print_img $*
  conf_img $*
}
main $@