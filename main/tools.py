import asyncio

from config import Config


class Tools:
    conf = Config()
    _client = None
    ADD_BODY = {
        'metadata': {
            'annotations': {conf.NS_ANNOTATION: 'true'}
        }
    }
    DEL_BODY = {
        'metadata': {
            'annotations': {conf.NS_ANNOTATION: None}
        }
    }

    @classmethod
    def connect_k8s(cls):
        from kubernetes import config, client

        if cls._client:
            return cls._client

        logger = cls.conf.logger
        try:
            config.load_kube_config(cls.conf.kbctx)
            logger.debug(f'kubeconfig连接k8s集群成功')
            cls._client = client
            return client
        except Exception:
            logger.debug('使用kubeconfig连接k8s集群失败，将尝试下一项配置连接')
            try:
                config.load_incluster_config()
                logger.debug(f'token file连接k8s集群成功')
                cls._client = client
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
                cls._client = client
                return client

    @classmethod
    def get_all_ns(cls, ns='all', **_):
        """
        获取所有命名空间
        """
        all_ns = cls.connect_k8s().CoreV1Api().list_namespace().items
        if ns == 'protect':
            return (ns.metadata.name for ns in all_ns if
                    ns.metadata.annotations is not None and cls.conf.NS_ANNOTATION in ns.metadata.annotations)
        elif ns == 'unprotect':
            return (ns.metadata.name for ns in all_ns if
                    ns.metadata.annotations is None or cls.conf.NS_ANNOTATION not in ns.metadata.annotations)

        return (ns.metadata.name for ns in all_ns)

    @classmethod
    async def get_ns_all_resource(cls, obj, **kwargs):
        resources = obj(kwargs['ns']).items
        if resources:
            protect_name = (
                res.metadata.name for res in resources
                if res.metadata.annotations and cls.conf.NS_ANNOTATION in res.metadata.annotations
            )

            if kwargs['mode'] == 'protect':
                return protect_name
            return (res.metadata.name for res in resources if res.metadata.name not in protect_name)

        return ()

    @classmethod
    async def _patch_resource(cls, patch_method, resource_name, ns, body=None):
        """
        执行资源的 patch 操作
        """
        if not body:
            body = cls.ADD_BODY
        patch_method(resource_name, ns, body)

    @classmethod
    async def task_run_subresource(cls, mode='add', ns=None, core_api=None, app_api=None):
        _body = None
        _mode = None
        tasks = []
        if mode == 'add':
            _body = cls.ADD_BODY
            _mode = 'unprotect'
        elif mode == 'del':
            _body = cls.DEL_BODY
            _mode = 'protect'

        for svc in await cls.get_ns_all_resource(core_api.list_namespaced_service, ns=ns, mode=_mode):
            tasks.append(cls._patch_resource(core_api.patch_namespaced_service,svc, ns, _body))
        for cm in await cls.get_ns_all_resource(core_api.list_namespaced_config_map, ns=ns, mode=_mode):
            tasks.append(cls._patch_resource(core_api.patch_namespaced_config_map,cm, ns, _body))
        for secret in await cls.get_ns_all_resource(core_api.list_namespaced_secret, ns=ns, mode=_mode):
            tasks.append(cls._patch_resource(core_api.patch_namespaced_secret,secret, ns, _body))
        for deploy in await cls.get_ns_all_resource(app_api.list_namespaced_deployment, ns=ns, mode=_mode):
            tasks.append(cls._patch_resource(app_api.patch_namespaced_deployment,deploy, ns, _body))
        for sts in await cls.get_ns_all_resource(app_api.list_namespaced_stateful_set, ns=ns, mode=_mode):
            tasks.append(cls._patch_resource(app_api.patch_namespaced_stateful_set,sts, ns, _body))

        if tasks:
            await asyncio.gather(*tasks)


    @classmethod
    async def sub_np_fn(cls, ns, logger, **kwargs):
        """
        给指定命名空间打上保护注解，如果没有被保护的话
        """
        protected_ns = cls.get_all_ns('protect')
        client = cls.connect_k8s()
        core_api = client.CoreV1Api()
        app_api = client.AppsV1Api()
        if ns in protected_ns:
            logger.info(f'Namespace: {ns} is already protected.')
            if kwargs.get('protect_all'):
                await cls.task_run_subresource(mode='add', ns=ns, core_api=core_api, app_api=app_api)
            return

        core_api.patch_namespace(ns, cls.ADD_BODY)
        _msg = f'Protected: namespace {ns}.'
        logger.info(_msg)

        if kwargs.get('protect_all'):
            logger.info(f'subresource protect complete,all resources(svc/cm/secret/deploy/sts)')
            await cls.task_run_subresource(mode='add', ns=ns, core_api=core_api, app_api=app_api)


    @classmethod
    async def sub_update_fn(cls, ns, new, logger, **_):
        client = cls.connect_k8s()
        core_api = client.CoreV1Api()
        app_api = client.AppsV1Api()
        all_ns = cls.get_all_ns()

        # 判断命名空间是否已经被删除
        if ns not in all_ns:
            return {'message': f'namespace: {ns} is not exist'}
        # 判断命名空间是否已经被保护
        if ns in new:
            return

        core_api.patch_namespace(ns, cls.DEL_BODY)
        _msg = f'old namespace: {ns} is unprotected'
        logger.info(_msg)

        await cls.task_run_subresource(mode='del', ns=ns, core_api=core_api, app_api=app_api)
        logger.info(f'subresource of namespace: {ns} is unprotected, all resources(svc/cm/secret/deploy/sts)')
        return {'message': _msg}
