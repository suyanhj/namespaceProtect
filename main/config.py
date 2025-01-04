import logging
from os import getenv


class Config:

    def __init__(self):
        if getenv('env') == 'k8s':
            self.listen_host = 'np-operator.np-operator.svc'
            self.api_server = 'https://kubernetes.default.svc'
            self.token = None
        else:
            self.listen_host = '192.168.10.81'
            self.api_server = 'https://192.168.10.110:6443'
            self.token = 'eyJhbGciOiJSUzI1NiIsImtpZCI6IlZjcUFzenUwM3RZck4xdlE1cHoxcUliSllHVzVRVDZubENaZHJyRmJKSU0ifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJhZG1pbi11c2VyIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImFkbWluLXVzZXIiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiI2M2Y5ZjdkNS0yMmIwLTQ4MzAtOTc3YS1iZTQyNDkyODJiMTYiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6a3ViZS1zeXN0ZW06YWRtaW4tdXNlciJ9.Ug9p5GH1aa8rKpd2U3wZiyENfSzYu6aXoADwx7zJjycyNoU4F3D0ly31coEBvPQR1Ci8LHN98zFRjda2f77DG2bpYyg66Gz8khsXjosSfY1qdB6KL1yukFCqGeT6dkhG9uiFyNZsH0iPVtylqUFzJuHV0yOf_4SYcig2cC5aY0N2-cZ1lgIv6qvS5tMzWr9i_SyrPQWB1JHKmyoxmYoJV0dkzaANFoP6jWsmbJv5gnFzR0J0qR6gBsRXP76lqJCEamZQNkaBO4ePaqvdqxqtBRfdfPxSjilfffKuDxvdLN13TOzadSuThMKo694JNSNU3XfN8kmA0rvVKLtAZbPnOg'
        self.kbctx = '~/.kube/config'
        self.token_file = None
        # self.token_file = '/run/secrets/kubernetes.io/serviceaccount/token'
        self.msg = None
        self.logger = self.logger_setup()

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

    def connect_k8s(self):
        from kubernetes import config, client
        try:
            config.load_kube_config(self.kbctx)
        except Exception:
            self.logger.warning('使用kubeconfig连接k8s集群失败，将尝试下一项配置连接')
            try:
                config.load_incluster_config()
            except Exception:
                self.logger.warning('使用pod内token file连接k8s集群失败，将尝试token配置连接')
                k8s_conf = client.Configuration(
                    host=self.api_server,
                    api_key={"authorization": "Bearer " + self.get_token()}
                )
                k8s_conf.verify_ssl = False
                client.Configuration.set_default(k8s_conf)

    def logger_setup(self):
        logging.basicConfig(
            level=logging.INFO,  # 设置日志级别
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 设置日志格式
            handlers=[
                logging.StreamHandler()  # 输出日志到控制台
            ]
        )
        return logging.getLogger(__name__)
