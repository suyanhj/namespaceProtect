from config import Config


class Tools:
    conf = Config()


    @classmethod
    def connect_k8s(cls):
        from kubernetes import config, client

        logger = cls.conf.logger
        try:
                config.load_kube_config(cls.conf.kbctx)
                logger.debug(f'kubeconfig连接k8s集群成功')
                return client
        except Exception:
            logger.debug('使用kubeconfig连接k8s集群失败，将尝试下一项配置连接')
            try:
                config.load_incluster_config()
                logger.debug(f'token file连接k8s集群成功')
                return client
            except Exception:
                logger.debug('使用pod内token file连接k8s集群失败，将尝试token配置连接')
                k8s_conf = client.Configuration(
                    host=cls.conf.api_server,
                    api_key={"authorization": "Bearer " + cls.conf.get_token()}
                )
                k8s_conf.verify_ssl = False
                client.Configuration.set_default(k8s_conf)
                logger.debug(f'token连接k8s集群成功')
                return client

    @classmethod
    def get_all_ns(cls, ns='name'):
        """
        获取所有命名空间
        """
        all_ns = cls.connect_k8s().CoreV1Api().list_namespace().items
        if ns == 'np_name':
            return (ns.metadata.name for ns in all_ns if
                    ns.metadata.annotations is not None and cls.conf.NS_ANNOTATION in ns.metadata.annotations)
        elif ns == 'unnp_name':
            return (ns.metadata.name for ns in all_ns if
                    ns.metadata.annotations is None or cls.conf.NS_ANNOTATION not in ns.metadata.annotations)

        return (ns.metadata.name for ns in all_ns)

    @classmethod
    def sub_np_fn(cls, ns, logger):
        """
        给指定命名空间打上保护注解，如果没有被保护的话
        """
        protected_ns = cls.get_all_ns('np_name')
        if ns in protected_ns:
            logger.info(f'Namespace {ns} is already protected.')
            return
        patch_body = {
            'metadata': {
                'annotations': {cls.conf.NS_ANNOTATION: 'true'}
            }
        }
        cls.api.patch_namespace(ns, patch_body)
        _ = f'Protected namespace {ns}.'
        logger.info(_)
        return {'message': _}

    @classmethod
    def sub_update_fn(cls, ns, new, logger):
        all_ns = cls.get_all_ns()
        if ns not in all_ns:
            return {'message': f'namespace: {ns} is not exist'}
        if ns in new:
            return

        patch_body = {
            'metadata': {
                'annotations': {cls.conf.NS_ANNOTATION: None},
            }
        }
        cls.api.patch_namespace(ns, patch_body)
        _ = f'old namespace: {ns} is unprotected'
        logger.info(_)
        return {'message': _}
