# Copyright 2015 Intel Corporation.
# All Rights Reserved.
#
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
import yaml

from tacker.agent.linux import utils
from tacker.common import log
from tacker.vm.mgmt_drivers import abstract_driver
from tacker.vm.mgmt_drivers import constants as mgmt_constants


LOG = logging.getLogger(__name__)
OPTS = [
    cfg.StrOpt('user', default='root', help=_('user name to login msactivator')),
    cfg.StrOpt('password', default='', help=_('password to login msactivator')),
]
cfg.CONF.register_opts(OPTS, 'msactivator')


class DeviceMgmtMSActivator(abstract_driver.DeviceMGMTAbstractDriver):
    def get_type(self):
        return 'msactivator'

    def get_name(self):
        return 'msactivator'

    def get_description(self):
        return 'Tacker DeviceMgmt MSActivator Driver'

    def mgmt_url(self, plugin, context, device):
        LOG.debug(_('mgmt_url %s'), device)
        return device.get('mgmt_url', '')

    @log.log
    def _config_service(self, mgmt_ip_address, service, config):
        user = cfg.CONF.msactivator.user
        password = cfg.CONF.msactivator.password
        cmd = ["sshpass", "-p", "%s" % password,
               "ssh", "-o", "StrictHostKeyChecking=no",
               "%s@%s" % (user, mgmt_ip_address),
               "uci import %s; /etc/init.d/%s restart" % (service, service)]
        utils.execute(cmd, process_input=config)

    @log.log
    def mgmt_call(self, plugin, context, device, kwargs):
        if (kwargs[mgmt_constants.KEY_ACTION] !=
                mgmt_constants.ACTION_UPDATE_DEVICE):
            return
        dev_attrs = device.get('attributes', {})

        mgmt_url = jsonutils.loads(device.get('mgmt_url', '{}'))
        if not mgmt_url:
            return

        vdus_config = dev_attrs.get('config', '')
        config_yaml = yaml.load(vdus_config)
        if not config_yaml:
            return
        vdus_config_dict = config_yaml.get('vdus', {})
        for vdu, vdu_dict in vdus_config_dict.items():
            config = vdu_dict.get('config', {})
            for key, conf_value in config.items():
                KNOWN_SERVICES = ('firewall', )
                if key not in KNOWN_SERVICES:
                    continue
                mgmt_ip_address = mgmt_url.get(vdu, '')
                if not mgmt_ip_address:
                    LOG.warning(_('tried to configure unknown mgmt '
                                  'address %s'),
                                vdu)
                    continue
                self._config_service(mgmt_ip_address, key, conf_value)
