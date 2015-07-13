import os
import contextlib
import sys
from behave import when, then
import mock
from time import sleep

sys.path.append('../')
from paasta_tools.utils import _run
from paasta_tools import marathon_tools
from paasta_tools import setup_marathon_job
from marathon import MarathonApp
from marathon import NotFoundError

fake_service_name = 'fake_complete_service'
fake_instance_name = 'fake_instance'
fake_appid = 'fake--complete--service.gitdeadbeef.configdeadbeef2'
fake_service_config = {
        'id': 'bounce.test1.newapp',
        'cmd': '/bin/sleep infinity',
        'instances': 1,
        'backoff_seconds': 0.1,
        'backoff_factor': 1,
        'mem': 480,
    }


@when(u'all zookeepers are unavailable')
def all_zookeepers_unavailable(context):
    pass


@when(u'all mesos masters are unavailable')
def all_mesos_masters_unavailable(context):
    pass

@when(u'an app called "{app_id}" using high memory is launched')
def run_paasta_metastatus_high_mem(context, app_id):
    context.client.create_app(app_id, MarathonApp(cmd='/bin/sleep infinity', mem=490, instances=1))


@when(u'an app called "{app_id}" using high cpu is launched')
def run_paasta_metastatus_high_cpu(context, app_id):
    context.client.create_app(app_id, MarathonApp(cmd='/bin/sleep infinity', cpus=9, instances=1))


@when(u'a task with id "{app_id}" is in the task list')
def task_is_ready(context, app_id):
    """ wait for a task with a matching task name to be ready. time out in 60 seconds """
    count = 60
    tries = 0
    while tries < count:
        try:
            tasks = context.client.list_tasks(app_id=app_id)
            if len(tasks) > 0:
                print 'Found task belonging to app %s, started at %s' % (app_id, tasks[0].started_at)
                return
            else:
                print 'Sleeping for 1 second...'
                tries = tries + 1
                sleep(1)
        except NotFoundError:
            print 'No app found. sleeping for 1 second...'
            tries = tries + 1
            sleep(1)
    raise Exception("Timed out waiting for task with belonging to app with id %s to appear in the task list" % app_id)


@then(u'metastatus returns 2')
def check_metastatus_return(context):
    # We don't want to invoke the "paasta metastatus" wrapper because by
    # default it will check every cluster. This is also the way sensu invokes
    # this check.
    cmd = '../paasta_tools/paasta_metastatus.py'
    env = dict(os.environ)
    env['MESOS_CLI_CONFIG'] = context.mesos_cli_config_filename
    print 'Running cmd %s with MESOS_CLI_CONFIG=%s' % (cmd, env['MESOS_CLI_CONFIG'])
    (returncode, output) = _run(cmd, env=env)
    print 'Got returncode %s with output:' % returncode
    print output

    assert returncode == 2
