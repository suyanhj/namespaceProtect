import asyncio
import json
from aiohttp import web
from kubernetes.client import ApiException
from config import Config

conf = Config('dev')
logger = conf.logger_setup()
client = conf.connect_k8s()
app = web.Application()
api = client.CoreV1Api()
client


def get_all_ns(ns='name'):
    """
    获取所有命名空间
    """
    try:
        all_ns = api.list_namespace().items
    except ApiException as e:
        raise Exception(f"Failed to list namespaces: {e}")
    if ns == 'np_name':
        return (ns.metadata.name for ns in all_ns if
                ns.metadata.annotations is not None and conf.NS_ANNOTATION in ns.metadata.annotations)
    elif ns == 'unnp_name':
        return (ns.metadata.name for ns in all_ns if
                ns.metadata.annotations is None or conf.NS_ANNOTATION not in ns.metadata.annotations)

    return (ns.metadata.name for ns in all_ns)

async def validate_namespace(request):
    """
    验证命名空间是否被保护
    """
    admission_review = await request.json()
    request_object = admission_review['request']['object']
    namespace_name = request_object['metadata']['name']
    annotations = request_object.get('metadata', {}).get('annotations', {})

    # 校验是否有保护注解
    if annotations and conf.NS_ANNOTATION in annotations:
        return admission_error(admission_review, f"Namespace: {namespace_name} is protected and cannot be deleted.", 403)

    # 如果没有保护注解，允许操作
    return admission_accept(admission_review)

async def validate_np_params(request):
    """
    校验 NamespaceProtect CRD 的参数
    """
    admission_review = await request.json()
    request_object = admission_review['request']['object']
    spec = request_object.get('spec', {})
    namespaces = spec.get('namespaces', [])
    selectors = spec.get('selectors', {})

    # 校验 namespaces 和 selectors 只能有一个配置
    if namespaces and selectors:
        return admission_error(admission_review, 'Only one of spec.namespaces and spec.selectors can be configured')

    # 校验 namespaces 或 selectors 必须存在一个
    if not namespaces and not selectors:
        return admission_error(admission_review, 'One of spec.namespaces or spec.selectors must be configured')

    # 校验 namespaces 是否是列表
    if namespaces and not isinstance(namespaces, list):
        return admission_error(admission_review, 'spec.namespaces should be a list of namespaces')

    # 校验每个命名空间是否存在
    if namespaces:
        existing_ns = get_all_ns()
        for ns in namespaces:
            if ns not in existing_ns:
                return admission_error(admission_review, f"Namespace: {ns} does not exist")

    # 校验 selectors 的标签配置是否是字典
    if selectors:
        labels = selectors.get('labels', {})
        if not isinstance(labels, dict):
            return admission_error(admission_review, 'spec.selectors.labels should be a dictionary')

    # 如果校验通过
    return admission_accept(admission_review)

async def admission_error(admission_review, message, code=400):
    """
    构造错误响应
    """
    response = {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": {
            "uid": admission_review['request']['uid'],
            "allowed": False,
            "status": {
                "code": code,
                "message": message
            }
        }
    }
    return web.json_response(response)

async def admission_accept(admission_review):
    """
    接受请求
    """
    response = {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": {
            "uid": admission_review['request']['uid'],
            "allowed": True
        }
    }
    return web.json_response(response)

# async def xx(request):
#     return web.json_response({'a': 11111})


def add_routes(route:dict):
    """
    添加路由
    """
    for k,v in route.items():
        app.router.add_get(k, v)

# 设置 Webhook 路由
r = {
    '/validate/namespaces': validate_namespace,
    '/validate/namespaceprotect': validate_np_params,
    # '/xx': xx
}


if __name__ == '__main__':
    # 启动 HTTP server（支持 TLS）
    add_routes(r)
    web.run_app(app, host='0.0.0.0', port=8443, ssl_context=('path/to/cert.pem', 'path/to/key.pem'))
    # web.run_app(app, host='0.0.0.0', port=8443)