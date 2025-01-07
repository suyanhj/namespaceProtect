import concurrent.futures
import logging
from typing import AsyncIterator

import kopf
from config import Config
import aiohttp
import asyncio
import base64

conf = Config()
log = conf.logger_setup()
api = conf.connect_k8s().CoreV1Api()
svc = {
    'namespace': 'np-operator',
    'name': 'np-operator',
    'port': 443
}
class Tools:
    @staticmethod
    def get_all_ns(ns='name'):
        """
        获取所有命名空间
        """
        all_ns = api.list_namespace().items
        if ns == 'np_name':
            return (ns.metadata.name for ns in all_ns if
                    ns.metadata.annotations is not None and conf.NS_ANNOTATION in ns.metadata.annotations)
        elif ns == 'unnp_name':
            return (ns.metadata.name for ns in all_ns if
                    ns.metadata.annotations is None or conf.NS_ANNOTATION not in ns.metadata.annotations)

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
                'annotations': {conf.NS_ANNOTATION: 'true'}
            }
        }
        api.patch_namespace(ns, patch_body)
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
                'annotations': {conf.NS_ANNOTATION: None},
            }
        }
        api.patch_namespace(ns, patch_body)
        _ = f'old namespace: {ns} is unprotected'
        logger.info(_)
        return {'message': _}

class WebhookServer(kopf.WebhookServer):
    async def __call__(self, fn: kopf.WebhookFn) -> AsyncIterator[kopf.WebhookClientConfig]:

        # Redefine as a coroutine instead of a partial to avoid warnings from aiohttp.
        async def _serve_fn(request: aiohttp.web.Request) -> aiohttp.web.Response:
            return await self._serve(fn, request)
        logger = log
        cadata, context = self._build_ssl()
        path = self.path.rstrip('/') if self.path else ''
        app = aiohttp.web.Application()
        app.add_routes([aiohttp.web.post(f"{path}/{{id:.*}}", _serve_fn)])
        runner = aiohttp.web.AppRunner(app, handle_signals=False)
        await runner.setup()
        try:
            # Note: reuse_port is mostly (but not only) for fast-running tests with SSL sockets;
            # multi-threaded sockets are not really used -- high load is not expected for webhooks.
            addr = self.addr or None  # None is aiohttp's "any interface"
            port = self.port or self._allocate_free_port()
            site = aiohttp.web.TCPSite(runner, addr, port, ssl_context=context, reuse_port=True)
            await site.start()

            # Log with the actual URL: normalised, with hostname/port set.
            # schema = 'http' if context is None else 'https'
            # url = self._build_url(schema, addr or '*', port, self.path or '')
            # logger.debug(f"Listening for webhooks at {url}")
            # host = self.host or self.DEFAULT_HOST or self._get_accessible_addr(self.addr)
            # url = self._build_url(schema, host, port, self.path or '')
            # logger.debug(f"Accessing the webhooks at {url}")

            # client_config = kopf.WebhookClientConfig(url=url)
            # svc.update({'path': ''})
            client_config = kopf.WebhookClientConfig(service=svc)
            if cadata is not None:
                client_config['caBundle'] = base64.b64encode(cadata).decode('ascii')

            yield client_config
            await asyncio.Event().wait()
        finally:
            # On any reason of exit, stop serving the endpoint.
            await runner.cleanup()

tools = Tools




@kopf.on.startup()
def init_fn(settings: kopf.OperatorSettings, **_):
    # 发送给k8s事件的日志级别设置为WARNING
    settings.posting.level = logging.WARNING
    # 同步函数，工作线程池大小设置为10
    settings.execution.max_workers = 10
    settings.execution.executor = concurrent.futures.ThreadPoolExecutor()
    # 设置finalizer名称
    settings.persistence.finalizer = f'{conf.API_NAME}/kopf-finalizer'
    # 重试回退
    settings.networking.error_backoffs = [10, 20, 30]
    # 准入控制
    settings.admission.server = WebhookServer(addr='0.0.0.0', port=8443,host=conf.listen_host)
    settings.admission.managed = conf.API_NAME



if not conf.env:
    @kopf.on.validate('namespaces', operations=['DELETE'])
    def namespace(body, **_):
        """
        验证命名空间是否被保护
        :return:
        """
        ns_annotations = body.metadata.annotations
        if ns_annotations and conf.NS_ANNOTATION in ns_annotations:
            raise kopf.AdmissionError(f'Namespace: {body.metadata.name} is protected and cannot be deleted.')


    @kopf.on.validate(conf.CRD_NAME, operations=['CREATE', 'UPDATE'])
    def namespaceprotect(body, **_):
        """
        校验 NamespaceProtect CRD 的参数
        """
        # 获取 namespaces 和 selectors
        namespaces = body.spec.get('namespaces', [])
        selectors = body.spec.get('selectors', {})

        # 校验 namespaces 和 selectors 只能有一个配置
        if namespaces and selectors:
            raise kopf.PermanentError('Only one of spec.namespaces and spec.selectors can be configured')

        # 如果没有配置 namespaces 和 selectors，则报错
        if not namespaces and not selectors:
            raise kopf.PermanentError('One of spec.namespaces or spec.selectors must be configured')

        # 如果配置了 namespaces，确保它是一个列表
        if namespaces and not isinstance(namespaces, list):
            raise kopf.PermanentError('spec.namespaces should be a list of namespaces')

        # 校验每个命名空间是否有效（如果 namespaces 非空）
        if namespaces:
            all_ns = tools.get_all_ns()
            for ns in namespaces:
                if ns not in all_ns:
                    raise kopf.PermanentError(f"Namespace: {ns} does not exist")

        # 校验 selectors 的标签配置是否是字典类型
        if selectors:
            labels = selectors.get('labels', {})
            if not isinstance(labels, dict):
                raise kopf.PermanentError('spec.selectors.labels should be a dictionary')


@kopf.on.update(conf.CRD_NAME)
@kopf.on.create(conf.CRD_NAME)
@kopf.on.resume(conf.CRD_NAME)
def np_fn(spec, logger, **_):
    """
    为命名空间打上保护注解，防止删除。
    如果是 spec.namespaces，则保护指定的命名空间。
    如果是 spec.selectors，则根据选择器标签保护匹配的命名空间。
    """
    namespaces = spec.get('namespaces', [])
    selectors = spec.get('selectors', {})

    if namespaces:
        # 处理指定的命名空间
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(tools.sub_np_fn, ns, logger): ns for ns in namespaces}
            for future in concurrent.futures.as_completed(futures):
                future.result()

    elif selectors and selectors.get('labels'):
        ns_label = ','.join(f'{key}={value}' for key, value in selectors.get('labels').items())
        # 获取所有命名空间并筛选符合标签选择器的命名空间
        try:
            namespaces_list = api.list_namespace(label_selector=ns_label).items
        except Exception as e:
            raise kopf.PermanentError(f"Failed to list namespaces with labels {selectors['labels']}: {e}")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(tools.sub_np_fn, ns.metadata.name, logger): ns.metadata.name for ns in
                       namespaces_list}
            for future in concurrent.futures.as_completed(futures):
                future.result()

    _ = 'Namespace protection applied successfully'
    logger.info(_)
    return {'message': _}


@kopf.on.update(conf.CRD_NAME, field='spec.namespaces')
def update_field_namespaces(new, old, logger, **_):
    """
    更新 spec.namespaces 字段时，删除已存在的保护注解。
    """
    if old:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(tools.sub_update_fn, ns, new, logger): ns for ns in old}
            for future in concurrent.futures.as_completed(futures):
                future.result()


@kopf.on.update(conf.CRD_NAME, field='spec.selectors')
def update_field_selectors(new, old, logger, **_):
    if old:
        ns_label = ','.join(f'{key}={value}' for key, value in old.get('labels').items())
        namespaces_list = api.list_namespace(label_selector=ns_label).items
        _ns = api.list_namespace(
            label_selector=','.join(f'{key}={value}' for key, value in new.get('labels').items())).items
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(tools.sub_update_fn, ns.metadata.name, _ns, logger): ns.metadata.name for ns in
                       namespaces_list}
            for future in concurrent.futures.as_completed(futures):
                future.result()

# @kopf.on.validate(conf.CRD_NAME,operations=['CREATE','UPDATE'])
# def validate_np_params(body, **_):
#     if body.spec.get('namespaces') and body.spec.get('selectors'):
#         raise kopf.PermanentError('Only one of spec.namespaces and spec.selectors can be configured')
#     if not body.spec.get('namespace'):
#         raise kopf.PermanentError('spec.namespace is required')
#
# @kopf.on.update(conf.CRD_NAME)
# @kopf.on.create(conf.CRD_NAME)
# @kopf.on.resume(conf.CRD_NAME)
# def ns_protect_fn(spec,logger, **_):
#     ns = spec.get('namespace')
#     ns_annotations = api.read_namespace(ns).metadata.annotations
#     if  ns_annotations:
#         if conf.NS_ANNOTATION in ns_annotations:
#             logger.info(f'namespace is protected: {ns}')
#             return {'message': f'namespace: {ns} is protected'}
#
#     patch_body = {
#         'metadata': {
#             'annotations': {conf.NS_ANNOTATION: 'true'},
#         }
#     }
#     api.patch_namespace(ns,patch_body)
#     return {'message': f'namespace: {ns} is protected'}
#
# @kopf.on.update(conf.CRD_NAME,field='spec.namespace')
# def update_ns_fn(new, old, **_):
#     all_ns = (ns.metadata.name for ns in api.list_namespace().items)
#     if old not in all_ns:
#         return {'message': f'namespace: {old} is not exist'}
#
#     patch_body = {
#         'metadata': {
#             'annotations': {conf.NS_ANNOTATION: None},
#         }
#     }
#     api.patch_namespace(old,patch_body)
#     return {'message': f'namespace: {new} is protected, old namespace: {old} is unprotected'}
