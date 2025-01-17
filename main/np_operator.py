import asyncio
import concurrent.futures
import logging

import kopf

from tools import Tools

conf = Tools.conf
log = conf.logger
client = Tools.connect_k8s()
api = client.CoreV1Api()


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
async def np_fn(spec, logger, **_):
    """
    为命名空间打上保护注解，防止删除。
    如果是 spec.namespaces，则保护指定的命名空间。
    如果是 spec.selectors，则根据选择器标签保护匹配的命名空间。
    """
    namespaces = spec.get('namespaces', [])
    selectors = spec.get('selectors', {})
    protect_all = spec.get('protectSubresources', False)
    tasks = []

    if not namespaces:
        if selectors and selectors.get('labels'):
            ns_label = ','.join(f'{key}={value}' for key, value in selectors.get('labels').items())
            try:
                namespaces = [ns.metadata.name for ns in api.list_namespace(label_selector=ns_label).items]
            except Exception as e:
                raise kopf.PermanentError(f"Failed to list namespaces with labels {selectors['labels']}: {e}")
        else:
            log.info('The label selector failed to successfully filter the namespace. Check the label selector configuration.')
            return
    if not namespaces:
        log.info('No namespaces specified, skipping namespace protection')
        return

    tasks.extend(Tools.sub_np_fn(ns, logger, protect_all=protect_all) for ns in namespaces)

    if tasks:
        await asyncio.gather(*tasks)

    _msg = f'Namespace: {namespaces} protection applied successfully'
    logger.info(_msg)
    return {'message': _msg}


@kopf.on.update(conf.CRD_NAME, field='spec.namespaces')
async def update_field_namespaces(new, old, logger, **_):
    """
    更新 spec.namespaces 字段时，删除已存在的保护注解。
    """
    if not new:
        return
    if old:
        tasks = []
        tasks.extend(
            Tools.sub_update_fn(ns, new, logger) for ns in old
        )

        # 异步等待所有任务完成
        if tasks:
            await asyncio.gather(*tasks)


@kopf.on.update(conf.CRD_NAME, field='spec.selectors')
async def update_field_selectors(new, old, logger, **_):
    if not new:
        return
    if old:
        old_label = ','.join(f'{key}={value}' for key, value in old.get('labels').items())
        new_label = ','.join(f'{key}={value}' for key, value in new.get('labels').items())
        # 获取旧命名空间
        old_ns = api.list_namespace(label_selector=old_label).items
        # 获取新命名空间
        new_ns = api.list_namespace(label_selector=new_label).items

        tasks = []
        tasks.extend(
            Tools.sub_update_fn(ns, new_ns, logger) for ns in old_ns
        )

        # 异步等待所有任务完成
        if tasks:
            await asyncio.gather(*tasks)

@kopf.on.update(conf.CRD_NAME, field='spec.protectSubresources')
async def update_field_protect_subresource(spec,new, logger, **_):
    app_api = client.AppsV1Api()
    tasks = []
    namespaces = spec.get('namespaces', [])
    if not namespaces:
        ns_label = ','.join(f'{key}={value}' for key, value in spec.get('selectors').get('labels').items())
        namespaces = [ns.metadata.name for ns in api.list_namespace(label_selector=ns_label).items]

    if not namespaces:
        logger.info('namespace is None')
        return
    # 新的要给子资源添加
    if not new:
        tasks.extend(Tools.task_run_subresource(mode='del', ns=ns, core_api=api, app_api=app_api) for ns in namespaces)
        logger.info(f'{namespaces} Subresources unprotect,all resources(svc,cm,secret,deploy,sts)')

    if tasks:
        await asyncio.gather(*tasks)