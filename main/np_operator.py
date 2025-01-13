import concurrent.futures
import logging
import kopf
from config import Config
from tools import Tools

conf = Config()
log = conf.logger
api = Tools.connect_k8s().CoreV1Api()

# conf.env = 'xx'
# if not conf.env:
#     import aiohttp
#     import asyncio
#     import base64
#     from typing import AsyncIterator
#
#     svc = {
#         'namespace': 'np-operator',
#         'name': 'np-operator',
#         'port': 443
#     }
#
#
#     # class WebhookServer(kopf.WebhookServer):
#     #     async def __call__(self, fn: kopf.WebhookFn) -> AsyncIterator[kopf.WebhookClientConfig]:
#     #
#     #         async def _serve_fn(request: aiohttp.web.Request) -> aiohttp.web.Response:
#     #             return await self._serve(fn, request)
#     #         cadata, context = self._build_ssl()
#     #         path = self.path.rstrip('/') if self.path else ''
#     #         app = aiohttp.web.Application()
#     #         app.add_routes([aiohttp.web.post(f"{path}/{{id:.*}}", _serve_fn)])
#     #         runner = aiohttp.web.AppRunner(app, handle_signals=False)
#     #         await runner.setup()
#     #         try:
#     #             addr = self.addr or None  # None is aiohttp's "any interface"
#     #             port = self.port or self._allocate_free_port()
#     #             site = aiohttp.web.TCPSite(runner, addr, port, ssl_context=context, reuse_port=True)
#     #             await site.start()
#     #
#     #             client_config = kopf.WebhookClientConfig(service=svc)
#     #             if cadata is not None:
#     #                 client_config['caBundle'] = base64.b64encode(cadata).decode('ascii')
#     #
#     #             yield client_config
#     #             await asyncio.Event().wait()
#     #         finally:
#     #             await runner.cleanup()
#
    # @kopf.on.validate('namespaces', operations=['DELETE'])
    # def namespace(body, **_):
    #     """
    #     验证命名空间是否被保护
    #     :return:
    #     """
    #     ns_annotations = body.metadata.annotations
    #     if ns_annotations and conf.NS_ANNOTATION in ns_annotations:
    #         raise kopf.AdmissionError(f'Namespace: {body.metadata.name} is protected and cannot be deleted.')
    #
    #
    # @kopf.on.validate(conf.CRD_NAME, operations=['CREATE', 'UPDATE'])
    # def namespaceprotect(body, **_):
    #     """
    #     校验 NamespaceProtect CRD 的参数
    #     """
    #     # 获取 namespaces 和 selectors
    #     namespaces = body.spec.get('namespaces', [])
    #     selectors = body.spec.get('selectors', {})
    #
    #     # 校验 namespaces 和 selectors 只能有一个配置
    #     if namespaces and selectors:
    #         raise kopf.PermanentError('Only one of spec.namespaces and spec.selectors can be configured')
    #
    #     # 如果没有配置 namespaces 和 selectors，则报错
    #     if not namespaces and not selectors:
    #         raise kopf.PermanentError('One of spec.namespaces or spec.selectors must be configured')
    #
    #     # 如果配置了 namespaces，确保它是一个列表
    #     if namespaces and not isinstance(namespaces, list):
    #         raise kopf.PermanentError('spec.namespaces should be a list of namespaces')
    #
    #     # 校验每个命名空间是否有效（如果 namespaces 非空）
    #     if namespaces:
    #         all_ns = Tools.get_all_ns()
    #         for ns in namespaces:
    #             if ns not in all_ns:
    #                 raise kopf.PermanentError(f"Namespace: {ns} does not exist")
    #
    #     # 校验 selectors 的标签配置是否是字典类型
    #     if selectors:
    #         labels = selectors.get('labels', {})
    #         if not isinstance(labels, dict):
    #             raise kopf.PermanentError('spec.selectors.labels should be a dictionary')


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
    # settings.admission.server = WebhookServer(addr='0.0.0.0', port=8443,host=conf.listen_host) if conf.env else kopf.WebhookServer(addr='0.0.0.0', port=8443,host=conf.listen_host)
    # settings.admission.server = kopf.WebhookServer(addr='0.0.0.0', port=8443, host=conf.listen_host)
    # settings.admission.managed = conf.API_NAME


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
            futures = {executor.submit(Tools.sub_np_fn, ns, logger): ns for ns in namespaces}
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
            futures = {executor.submit(Tools.sub_np_fn, ns.metadata.name, logger): ns.metadata.name for ns in
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
            futures = {executor.submit(Tools.sub_update_fn, ns, new, logger): ns for ns in old}
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
            futures = {executor.submit(Tools.sub_update_fn, ns.metadata.name, _ns, logger): ns.metadata.name for ns in
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
