# Namespace Protect
k8s命名空间删除保护operator，使用kopf实现

通过为crd为命名空间配置注解，实现删除保护

## run
```shell
python3 -m kopf run --verbose --standalone --log-format=full --liveness http://0.0.0.0:8080 main/np_operator.py 
```