from fastapi import FastAPI
import uvicorn

from config import Config, AdmissionRequest, AdmissionResponse, AdmissionReviewResponse
from tools import Tools

conf = Config()
client = Tools.connect_k8s()
api = client.CoreV1Api()
log = conf.logger
app = FastAPI()


@app.get("/livz")
async def livz():
    """
    检查服务是否存活
    """
    return {"status": "ok"}


@app.post("/validate-ns")
async def validate_namespace(admission_review: AdmissionRequest):
    """
    验证命名空间是否被保护
    """
    request_object = admission_review.request.object
    namespace_name = request_object['metadata']['name']
    annotations = request_object.get('metadata', {}).get('annotations', {})

    # 校验是否有保护注解
    if annotations and conf.NS_ANNOTATION in annotations:
        return await admission_error(admission_review,
                                     f"Namespace: {namespace_name} is protected and cannot be deleted.", 403)

    # 如果没有保护注解，允许操作
    return await admission_accept(admission_review)


@app.post("/validate-np-params")
async def validate_np_params(admission_review: AdmissionRequest):
    """
    校验 NamespaceProtect CRD 的参数
    """
    request_object = admission_review.request.object
    spec = request_object.get('spec', {})
    namespaces = spec.get('namespaces', [])
    selectors = spec.get('selectors', {})

    # 校验 namespaces 和 selectors 只能有一个配置
    if namespaces and selectors:
        return await admission_error(admission_review,
                                     'Only one of spec.namespaces and spec.selectors can be configured')

    # 校验 namespaces 或 selectors 必须存在一个
    if not namespaces and not selectors:
        return await admission_error(admission_review, 'One of spec.namespaces or spec.selectors must be configured')

    # 校验 namespaces 是否是列表
    if namespaces and not isinstance(namespaces, list):
        return await admission_error(admission_review, 'spec.namespaces should be a list of namespaces')

    # 校验每个命名空间是否存在
    if namespaces:
        existing_ns = Tools.get_all_ns()
        for ns in namespaces:
            if ns not in existing_ns:
                return await admission_error(admission_review, f"Namespace: {ns} does not exist")

    # 校验 selectors 的标签配置是否是字典
    if selectors:
        labels = selectors.get('labels', {})
        if not isinstance(labels, dict):
            return await admission_error(admission_review, 'spec.selectors.labels should be a dictionary')

    # 如果校验通过
    return await admission_accept(admission_review)


# 构造错误响应
async def admission_error(admission_review, message, code=400):
    """
    构造错误响应
    """
    response = AdmissionResponse(
        apiVersion="admission.k8s.io/v1",
        kind="AdmissionReview",
        response=AdmissionReviewResponse(
            uid=admission_review.request.uid,
            allowed=False,
            status={"code": code, "message": message}
        )
    )
    return response


# 构造接受响应
async def admission_accept(admission_review):
    """
    接受请求
    """
    response = AdmissionResponse(
        apiVersion="admission.k8s.io/v1",
        kind="AdmissionReview",
        response=AdmissionReviewResponse(
            uid=admission_review.request.uid,
            allowed=True
        )
    )
    return response


# 加载 SSL 证书并返回配置
def ssl_load(crt=None, key=None, ca=None):
    """
    加载 SSL 证书
    """
    crt_dir = f'{conf.PROJ_DIR}/tools/files/crt/'
    ca_crt = ca if ca else crt_dir + 'ca.crt'
    cert_file = crt if crt else crt_dir + 'server.pem'
    key_file = key if key else crt_dir + 'server.key'

    return ca_crt, cert_file, key_file


# 启动 HTTPS 服务
def start_https():
    ca_crt, cert_file, key_file = ssl_load()
    log_conf = f'{conf.PROJ_DIR}/examples/log_conf.yml'
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8443,
        ssl_certfile=cert_file,
        ssl_keyfile=key_file,
        ssl_ca_certs=ca_crt,
        log_config=log_conf
    )


# 启动 HTTP 服务
def start_http():
    log_conf = f'{conf.PROJ_DIR}/examples/log_conf.yml'
    uvicorn.run(app, host="0.0.0.0", port=8080,log_config=log_conf)


if __name__ == '__main__':
    # 使用多进程启动 HTTP 和 HTTPS 服务

    # https_process = Process(target=start_https)
    # http_process = Process(target=start_http)
    #
    # https_process.start()
    # http_process.start()
    #
    # https_process.join()
    # http_process.join()
    start_http()
    # start_https()