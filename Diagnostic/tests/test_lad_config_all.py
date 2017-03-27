# TODO (A big one) Make LadConfigAll class unittest-able here.
# To achieve that, we need the following:
# - Mock VM's cert/prv key files (w/ thumbprint) that's used for decrypting the extensions's protected settings
#   and for encrypting storage key/SAS token in mdsd XML file
# - Mock a complete LAD extension's handler setting (that includes protected settings and public settings).
# - Mock RunGetOutput for external command executions.
# - Mock any other things that are necessary!
# It'd be easiest to create a test VM w/ LAD enabled and copy out necessary files to here to be used for this test.
# The test VM should be destroyed immediately. A test storage account should be used and deleted immediately.

import json
import os
import subprocess
import unittest

from Utils.lad_ext_settings import *
from lad_config_all import *

# Mocked waagent/LAD dir/files
test_waagent_dir = os.path.join(os.path.dirname(__file__), 'var_lib_waagent')
test_lad_dir = os.path.join(test_waagent_dir, 'lad_dir')
test_lad_settings_json_file = os.path.join(test_lad_dir, 'config', 'lad_settings.jq')


# Mocked functions
def test_logger(type, msg):
    print type + ':' + msg


def test_run_command(cmd, should_log=True):
    if should_log:
        print "Command to execute: " + cmd
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        print "Command execution error. Exit code=" + str(e.returncode) + \
            ", result=" + e.output[:-1].decode('latin-1')
        return e.returncode, e.output.decode('latin-1')
    return 0, output.decode('latin-1')


# BADBAD Copied code from HandlerUtil.py to decrypt protectedSettings...
# Can't import HandlerUtil.py from unittests, because of the waagent dependency...
# so just copying like this...
def decrypt_protected_settings(handlerSettings):
    if handlerSettings.has_key('protectedSettings') and \
            handlerSettings.has_key("protectedSettingsCertThumbprint") and \
            handlerSettings['protectedSettings'] is not None and \
            handlerSettings["protectedSettingsCertThumbprint"] is not None:
        protectedSettings = handlerSettings['protectedSettings']
        thumb=handlerSettings['protectedSettingsCertThumbprint']
        cert=test_waagent_dir+'/'+thumb+'.crt'
        pkey=test_waagent_dir+'/'+thumb+'.prv'
        unencodedSettings = base64.standard_b64decode(protectedSettings)
        openSSLcmd = "openssl smime -inform DER -decrypt -recip {0} -inkey {1}".format(cert, pkey)
        proc = subprocess.Popen([openSSLcmd], shell=True, stdin=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdout=subprocess.PIPE)
        output = proc.communicate(unencodedSettings)[0].decode('latin-1')
        handlerSettings['protectedSettings'] = json.loads(output)


def print_content_with_header(header_text, content):
    header = '>>>>> ' + header_text + ' >>>>>'
    print header
    print content
    print '<' * len(header)
    print


class LadConfigAllTest(unittest.TestCase):

    def setUp(self):
        """
        Set up a LadConfigAll object with all dependencies properly set up and injected.
        """
        with open(test_lad_settings_json_file) as f:
            handler_settings = json.loads(f.read())['runtimeSettings'][0]['handlerSettings']
            decrypt_protected_settings(handler_settings)
            lad_settings = LadExtSettings(handler_settings)

        self._lad_config_all_helper = LadConfigAll(lad_settings, test_lad_dir, test_waagent_dir,
                                                   'test_lad_deployment_id', test_run_command,
                                                   lambda x: test_logger('LOG', x), lambda x: test_logger('ERROR', x))

    def test_lad_config_all_basic(self):
        """
        Perform basic LadConfigAll object tests, like generating various configs and validating them.
        Initially this will be mostly just exercising the API functions, not asserting much.
        """
        lad_cfg = self._lad_config_all_helper  # handy reference
        result, msg = lad_cfg.generate_mdsd_omsagent_syslog_configs()
        self.assertTrue(result, 'Config generation failed: ' + msg)

        with open(os.path.join(test_lad_dir, 'xmlCfg.xml')) as f:
            mdsd_xml_cfg = f.read()
        print_content_with_header('Generated mdsd XML cfg', mdsd_xml_cfg)
        self.assertTrue(mdsd_xml_cfg, 'Empty mdsd XML config is invalid!')

        rsyslog_cfg = lad_cfg.get_rsyslog_config()
        print_content_with_header('Generated rsyslog cfg', rsyslog_cfg)
        self.assertTrue(rsyslog_cfg, 'Empty rsyslog cfg is invalid')

        syslog_ng_cfg = lad_cfg.get_syslog_ng_config()
        print_content_with_header('Generated syslog-ng cfg', syslog_ng_cfg)
        self.assertTrue(syslog_ng_cfg, 'Empty syslog-ng cfg is invalid')

        fluentd_out_mdsd_cfg = lad_cfg.get_fluentd_out_mdsd_config()
        print_content_with_header('Generated fluentd out_mdsd cfg', fluentd_out_mdsd_cfg)
        self.assertTrue(fluentd_out_mdsd_cfg, 'Empty fluentd out_mdsd cfg is invalid')

        fluentd_syslog_src_cfg = lad_cfg.get_fluentd_syslog_src_config()
        print_content_with_header('Generated fluentd syslog src cfg', fluentd_syslog_src_cfg)
        self.assertTrue(fluentd_syslog_src_cfg, 'Empty fluentd syslog src cfg is invalid')

        fluentd_tail_src_cfg = lad_cfg.get_fluentd_tail_src_config()
        print_content_with_header('Generated fluentd tail src cfg', fluentd_tail_src_cfg)
        self.assertTrue(fluentd_tail_src_cfg, 'Empty fluentd tail src cfg is invalid')
