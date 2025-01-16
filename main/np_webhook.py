from fastapi import FastAPI
import uvicorn
from config import AdmissionRequest, AdmissionResponse, AdmissionReviewResponse
from tools import Tools

conf = Tools.conf
client = Tools.connect_k8s()
api = client.CoreV1Api()
log = conf.logger
log_conf = f'{conf.PROJ_DIR}/examples/log_conf.yml'
app = FastAPI()


@app.get("/livz")
async def livz():
    """
    检查服务是否存活
    """
    return {"status": "ok"}



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


@app.post("/validate-resources-protect")
async def validate_resources_protect(admission_review: AdmissionRequest):
    """
    验证命名空间是否被保护
    """
    request_object = admission_review.request.oldObject
    name = admission_review.request.name
    resource = admission_review.request.resource.get('resource')
    annotations = request_object.get('metadata', {}).get('annotations', {})

    # 校验是否有保护注解
    if annotations and conf.NS_ANNOTATION in annotations:
        return await admission_error(admission_review,
                                     f"resource {resource}: {name} is protected and cannot be deleted.", 403)

    # 如果没有保护注解，允许操作
    return await admission_accept(admission_review)


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



def ssl_load(crt=None, key=None, ca=None):
    """
    加载 SSL 证书
    """
    crt_dir = f'{conf.PROJ_DIR}/tools/files/crt/'
    ca_crt = ca if ca else crt_dir + 'ca.crt'
    cert_file = crt if crt else crt_dir + 'server.pem'
    key_file = key if key else crt_dir + 'server.key'

    return ca_crt, cert_file, key_file


def start(ssl=False):
    if ssl:
        ca_crt, cert_file, key_file = ssl_load()
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8443,
            ssl_certfile=cert_file,
            ssl_keyfile=key_file,
            ssl_ca_certs=ca_crt,
            log_config=log_conf
        )
    else:
        uvicorn.run(app, host="0.0.0.0", port=8080,log_config=log_conf)


if __name__ == '__main__':
    if conf.env == 'k8s':
        start()
    else:
        start(True)