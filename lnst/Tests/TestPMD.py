import logging
import subprocess
import signal
from lnst.Common.Parameters import Param, StrParam, IntParam, FloatParam
from lnst.Common.Parameters import IpParam, DeviceOrIpParam
from lnst.Tests.BaseTestModule import BaseTestModule, TestModuleError
from lnst.Common.LnstError import LnstError


class TestPMD(BaseTestModule):
    coremask = StrParam(mandatory=True)
    pmd_coremask = StrParam(mandatory=True)

    # TODO make ListParam
    foward_mode = StrParam(mandatory=True)
    nics = Param(mandatory=True)
    peer_macs = Param(mandatory=False)

    def format_command(self):
        if self.params.forward_mode == "macswap":
            testpmd_args = ["dpdk-testpmd", "--no-pci"]
        else:
            testpmd_args = ["testpmd"]

        testpmd_args.extend(["-c", self.params.coremask,
                             "-n", "4", "--socket-mem", "1024,0"])

        for i, nic in enumerate(self.params.nics):
            if self.params.foward_mode == "mac":
                testpmd_args.extend(["-w", nic])
            elif self.params.foward_mode == "macswap":
                testpmd_args.extend([f"--vdev=net_virtio_user{i+1},path=/var/run/openvswitch/{nic}"])
            else:
                LnstError("Unsupported forward-mode parameter selected for the TestPMD.")

        testpmd_args.extend(["--", "-i", "--forward-mode", self.params.foward_mode,
                             "--coremask", self.params.pmd_coremask])

        if self.params.foward_mode == "mac":
            for i, mac in enumerate(self.params.peer_macs):
                testpmd_args.extend(["--eth-peer", "{},{}".format(i, mac)])
        elif self.params.foward_mode == "macswap":
            testpmd_args.extend(["--port-topology=loop"])

        return " ".join(testpmd_args)


    def run(self):
        cmd = self.format_command()
        logging.debug("Running command \"{}\" as subprocess".format(cmd))
        process = subprocess.Popen(cmd, shell=True,
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   close_fds=True)

        process.stdin.write(str.encode("start tx_first\n"))
        process.stdin.flush()

        self.wait_for_interrupt()

        process.stdin.write(str.encode("stop\n"))
        process.stdin.flush()
        process.stdin.write(str.encode("quit\n"))
        process.stdin.flush()

        out, err = process.communicate()
        self._res_data = {"stdout": out, "stderr": err}
        return True
