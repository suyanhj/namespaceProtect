import time
import subprocess
from cProfile import label

from kopf.testing import KopfRunner
from main.config import Config
from kubernetes import client

# def test_operator():
#     with KopfRunner(['run', '-A', '--verbose', 'examples/01-minimal/example.py']) as runner:
#         # do something while the operator is running.
#
#         subprocess.run("kubectl apply -f examples/obj.yaml", shell=True, check=True)
#         time.sleep(1)  # give it some time to react and to sleep and to retry
#
#         subprocess.run("kubectl delete -f examples/obj.yaml", shell=True, check=True)
#         time.sleep(1)  # give it some time to react
#
#     assert runner.exit_code == 0
#     assert runner.exception is None
#     assert 'And here we are!' in runner.stdout
#     assert 'Deleted, really deleted' in runner.stdout

def test_config():
    # conf = Config()
    # k8s_conf = client.Configuration(
    #     host=conf.api_server,
    #     api_key={"authorization": "Bearer " + conf.get_token()}
    # )
    # k8s_conf.verify_ssl = False
    # client.Configuration.set_default(k8s_conf)
    # api = client.CoreV1Api()
    # api = client.CoreV1Api(client.api_client.ApiClient(configuration=k8s_conf))
    # if 'namespaceprotect.hj.com/protect' in api.read_namespace('default').metadata.annotations:
    #     print(1)
    # print(type(api.read_namespace('default').metadata.annotations))

    conf = Config()
    conf.connect_k8s()
    api = client.CoreV1Api()
    # print(api.read_namespace('t1').metadata.annotations)
    # print(type(api.list_namespace().items))
    # # print(api.list_namespace().items)
    # a = [ ns.metadata.name for ns in api.list_namespace().items ]
    # print(a)
    NS_ANNOTATION = 'namespaceprotect.hj.com/protect'
    # protected_ns = (ns.metadata.name for ns in api.list_namespace().items if
    #                 ns.metadata.annotations is not None and NS_ANNOTATION in ns.metadata.annotations)
    # unprotected_ns = (ns.metadata.name for ns in api.list_namespace().items if
    #                   ns.metadata.annotations is not None and NS_ANNOTATION not in ns.metadata.annotations or ns.metadata.annotations is None)
    # for ns in protected_ns:
    #     print(ns)
    # for ns in unprotected_ns:
    #     print(ns)

    # namespaces_list = api.list_namespace(label_selector=labels)
    # a=None
    # for i in a:
    #     print(1)

test_config()

class aa:
    @staticmethod
    def xx():
        print(1)

    @classmethod
    def yy(cls):
        cls.xx()

aa.yy()