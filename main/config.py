import logging
from os import getenv
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel
from typing_extensions import Literal, TypedDict


class Config:
    CRD_NAME: str = 'namespaceprotects'
    API_NAME: str = f'{CRD_NAME}.hj.com'
    NS_ANNOTATION: str = 'namespaceprotect.hj.com/protect'
    PROJ_DIR = Path(__file__).parent.parent

    def __init__(self, env=None):
        self.logger = self.logger_setup()
        self.env = getenv('env') if getenv('env') else env
        if self.env == 'k8s':
            self.listen_host = 'np-operator' + getenv('NAMESPACE', 'np-operator') + '.svc'
            self.api_server = 'https://kubernetes.default.svc'
            self.token = None
            self.kbctx = None
            self.token_file = '/run/secrets/kubernetes.io/serviceaccount/token'
        else:
            self.listen_host = '192.168.10.81'
            self.api_server = 'https://192.168.10.110:6443'
            self.token = 'eyJhbGciOiJSUzI1NiIsImtpZCI6IlZjcUFzenUwM3RZck4xdlE1cHoxcUliSllHVzVRVDZubENaZHJyRmJKSU0ifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJhZG1pbi11c2VyIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImFkbWluLXVzZXIiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiI2M2Y5ZjdkNS0yMmIwLTQ4MzAtOTc3YS1iZTQyNDkyODJiMTYiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6a3ViZS1zeXN0ZW06YWRtaW4tdXNlciJ9.Ug9p5GH1aa8rKpd2U3wZiyENfSzYu6aXoADwx7zJjycyNoU4F3D0ly31coEBvPQR1Ci8LHN98zFRjda2f77DG2bpYyg66Gz8khsXjosSfY1qdB6KL1yukFCqGeT6dkhG9uiFyNZsH0iPVtylqUFzJuHV0yOf_4SYcig2cC5aY0N2-cZ1lgIv6qvS5tMzWr9i_SyrPQWB1JHKmyoxmYoJV0dkzaANFoP6jWsmbJv5gnFzR0J0qR6gBsRXP76lqJCEamZQNkaBO4ePaqvdqxqtBRfdfPxSjilfffKuDxvdLN13TOzadSuThMKo694JNSNU3XfN8kmA0rvVKLtAZbPnOg'
            self.kbctx = '~/.kube/config'
            self.token_file = None

        self.msg = None

        self.vaild_api_srv()
        if not self.vaild_auth_conf(self.kbctx, 'kubeconfig'):
            if not self.vaild_auth_conf(self.token, 'token'):
                if not self.vaild_auth_conf(self.token_file, 'token file'):
                    self.msg = '未找到认证配置文件'
                    self.logger.error(self.msg)
                    # print(self.msg)

    def vaild_api_srv(self):
        if not self.api_server:
            self.msg = 'api server 未定义'
            self.logger.warning(self.msg)
            # print(self.msg)
            return

    def vaild_auth_conf(self, conf, msg):
        if conf is not None:
            if len(conf) != 0:
                return True

        self.msg = f'未配置 {msg}, 将获取下一配置项'
        # print(self.msg)
        self.logger.warning(self.msg)

    def get_token(self):
        if self.token:
            return self.token
        if self.token_file:
            with open(self.token_file, 'r') as f:
                return f.read()

    @staticmethod
    def logger_setup():
        logging.basicConfig(
            level=logging.INFO,  # 设置日志级别
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 设置日志格式
            handlers=[
                logging.StreamHandler()  # 输出日志到控制台
            ]
        )
        return logging.getLogger(__name__)


Operation = Literal['CREATE', 'UPDATE', 'DELETE', 'CONNECT']


class CreateOptions(TypedDict, total=False):
    apiVersion: Literal["meta.k8s.io/v1"]
    kind: Literal["CreateOptions"]


class UpdateOptions(TypedDict, total=False):
    apiVersion: Literal["meta.k8s.io/v1"]
    kind: Literal["UpdateOptions"]


class DeleteOptions(TypedDict, total=False):
    apiVersion: Literal["meta.k8s.io/v1"]
    kind: Literal["DeleteOptions"]


# 请求模型
class AdmissionReviewRequest(BaseModel):
    uid: str
    options: Union[None, CreateOptions, UpdateOptions, DeleteOptions]
    object: Optional[Dict[str, Any]] = None
    oldObject: Optional[Dict[str, Any]] = None
    kind: Optional[Dict[str, str]] = None
    resource: Optional[Dict[str, str]] = None
    subResource: Optional[str] = None
    requestKind: Optional[Dict[str, Any]] = None
    requestResource: Optional[Dict[str, Any]] = None
    requestSubResource: Optional[str] = None
    name: Optional[str] = None
    namespace: Optional[str] = None
    operation: Optional[str] = None
    userInfo: Optional[Dict[str, Any]] = None
    # options: Optional[Dict[str, str]] = None
    dryRun: Optional[bool] = False


class AdmissionRequest(BaseModel):
    apiVersion: str
    kind: str
    request: AdmissionReviewRequest


class AdmissionReviewResponse(BaseModel):
    uid: str
    allowed: bool
    status: Optional[Dict[str, Any]] = None
    patch: Optional[str] = None
    patchType: Optional[str] = None
    warnings: Optional[List[str]] = None


class AdmissionResponse(BaseModel):
    apiVersion: str
    kind: str
    response: AdmissionReviewResponse
