# Namespace Protect
k8s命名空间删除保护operator，使用kopf实现

通过为crd为命名空间配置注解，实现删除保护

## 安装
```shell
git clone https://github.com/suyanhj/namespaceProtect.git --depth=1
cd namespaceProtect
make install
```

## 调试

### 命令运行
#### operator
```shell
python3 -m kopf run --verbose --standalone --log-format=full --liveness http://0.0.0.0:8080 main/np_operator.py 
```

#### 准入控制webhook
```shell
cd tools
sh cert.sh
sh registry-webhook.sh
python3 main/np_webhook.py
```

### k8s运行
```shell
sh tools/dk-build.sh operator webhook
make install
```