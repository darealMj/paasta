import functools

from bravado.docstring_property import docstring_property
from bravado.exception import HTTPForbidden

from paasta_tools.cli.cmds.auth import get_token_from_file
from paasta_tools.cli.cmds.auth import get_token_from_vault
from paasta_tools.cli.cmds.auth import write_token_to_disk

# from bravado_decorators.decorate_client import decorate_client


class AuthFutureDecorator(object):

    def __init__(self, future, cluster_name):
        self.future = future
        self.attempts = 0
        self.cluster_name = cluster_name

    def result(self, *args, **kwargs):
        """ Wraps a Future's result method with a timer. """
        try:
            result = self.future.result(*args, **kwargs)
        except HTTPForbidden:
            if self.attempts >= 3:
                raise
            self.attempts += 1
            token = get_token_from_file(self.cluster_name)
            if not token or self.future.future.request.headers['X-Paasta-Token'] == token:
                # the token we sent matches on disk but we failed auth anyway
                # so lets try and get a fresh one!
                token = get_token_from_vault(self.cluster_name)
                write_token_to_disk(self.cluster_name, token)
            self.future.future.request.headers['X-Paasta-Token'] = token
            result = self.result(*args, **kwargs)
        return result


class AuthResourceDecorator(object):

    def __init__(self, resource, cluster_name):
        self.resource = resource
        self.cluster_name = cluster_name

    def __getattr__(self, name):
        return decorate_client(self.resource, self._with_auth_check, name)

    def _with_auth_check(self, call_name, *args, **kwargs):
        return AuthFutureDecorator(
            getattr(self.resource, call_name)(*args, **kwargs),
            self.cluster_name,
        )


class AuthClientDecorator(object):
    """
    """

    def __init__(self, client, cluster_name):
        """ Create a auth client decorator.
        :param client: The client that will have all resource operation calls
            tracked.
        :type client: swaggerpy.SwaggerClient
        :return: A wrapped swagger client that should be used in place of a
            plain swagger client.
        """
        self.client = client
        self.cluster_name = cluster_name

    def __getattr__(self, name):
        return AuthResourceDecorator(
            getattr(self.client, name),
            self.cluster_name,
        )

    def __dir__(self):
        return dir(self.client)


# below helpers borrowed from bravado_decorators/decorate_client.py
# maybe move into one of the open bravado packages?

def decorate_client(api_client, func, name):
    """A helper for decorating :class:`bravado.client.SwaggerClient`.
    :class:`bravado.client.SwaggerClient` can be extended by creating a class
    which wraps all calls to it. This helper is used in a :func:`__getattr__`
    to check if the attr exists on the api_client. If the attr does not exist
    raise :class:`AttributeError`, if it exists and is not callable return it,
    and if it is callable return a partial function calling `func` with `name`.

    Example usage:

    .. code-block:: python

        class SomeClientDecorator(object):

            def __init__(self, api_client, ...):
                self.api_client = api_client

            # First arg should be suffiently unique to not conflict with any of
            # the kwargs
            def wrap_call(self, client_call_name, *args, **kwargs):
                ...

            def __getattr__(self, name):
                return decorate_client(self.api_client, self.wrap_call, name)

    :param api_client: the client which is being decorated
    :type  api_client: :class:`bravado.client.SwaggerClient`
    :param func: a callable which accepts `name`, `*args`, `**kwargs`
    :type  func: callable
    :param name: the attribute being accessed
    :type  name: string
    :returns: the attribute from the `api_client` or a partial of `func`
    :raises: :class:`AttributeError`
    """
    client_attr = getattr(api_client, name)
    if not callable(client_attr):
        return client_attr

    return OperationDecorator(client_attr, functools.partial(func, name))


class OperationDecorator(object):
    """A helper to preserve attributes of :class:`swaggerpy.client.Operation`
    and :class:`bravado.client.CallableOperation` while decorating their
    __call__() methods

    :param operation: callable operation, e.g., attributes of
        :class:`swaggerpy.client.Resource` or
        :class:`bravado_core.resource.Resource`
    :type  operation: :class:`swaggerpy.client.Operation` or
        :class:`bravado.client.CallableOperation`
    :param func: a callable which accepts `*args`, `**kwargs`
    :type  func: callable
    """

    @docstring_property(__doc__)
    def __doc__(self):
        return self.operation.__doc__

    def __init__(self, operation, func):
        self.operation = operation
        self.func = func

    def __getattr__(self, name):
        return getattr(self.operation, name)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)
