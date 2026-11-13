##
# File: MultiUpdateWorkerCountTests.py
#
"""Worker-process count used when releasing or pulling several entries.

Without configuration the pool size is half the CPUs the process may use (at least 1), or one worker per entry when the
compute cluster is enabled.  The resource allocation file can set a count for this step.  The tests replace the process
pool, the site configuration and the CPU counts, so nothing real is started.
"""

# pylint: disable=protected-access,unused-argument

import json
import multiprocessing
import os
import sys
import tempfile
import unittest
from unittest import mock

try:
    import MySQLdb  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    # The database driver is not needed here; a stand-in lets the modules under test import.
    _MYSQL = mock.MagicMock()
    sys.modules["MySQLdb"] = _MYSQL
    sys.modules["MySQLdb.cursors"] = _MYSQL.cursors

try:
    import wwpdb.utils.nmr.NmrDpUtility  # noqa: F401  # pylint: disable=unused-import
except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
    # The NMR tools load reference data at import time and are not needed here.
    for _name in [name for name in sys.modules if name.startswith("wwpdb.utils.nmr")]:
        del sys.modules[_name]
    _NMR = mock.MagicMock()
    sys.modules["wwpdb.utils.nmr"] = _NMR
    sys.modules["wwpdb.utils.nmr.NmrDpUtility"] = _NMR.NmrDpUtility

try:
    import wwpdb.apps.msgmodule.io.MessagingIo  # noqa: F401  # pylint: disable=unused-import
except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
    sys.modules["wwpdb.apps.msgmodule.io.MessagingIo"] = mock.MagicMock()

import wwpdb.apps.releasemodule.update.MultiUpdateProcess as update_module  # noqa: E402
from wwpdb.apps.releasemodule.update.UpdateBase import UpdateBase  # noqa: E402


class _FakePool(object):
    """Stands in for MultiProcUtil and remembers the requested number of processes."""

    requested = []

    def __init__(self, *args, **kwargs):
        pass

    def set(self, **kwargs):
        pass

    def setWorkingDir(self, path):
        pass

    def runMulti(self, dataList=None, numProc=None, numResults=None):
        _FakePool.requested.append(numProc)
        return True, [], [[]], []


class _FakeConfigInfo(object):
    """Site configuration with a resource allocation file and an optional compute-cluster flag."""

    path = None
    cluster = False

    def __init__(self, *args, **kwargs):
        pass

    def get(self, key, default=None):
        if key == "RESOURCE_ALLOCATION_CONFIG_FILE":
            return _FakeConfigInfo.path
        if key == "USE_COMPUTE_CLUSTER":
            return _FakeConfigInfo.cluster
        return default


def _fake_base_init(self, reqObj=None, verbose=False, log=sys.stderr):
    self._reqObj = reqObj
    self._cI = _FakeConfigInfo()
    self._sessionPath = tempfile.gettempdir()


class MultiUpdateWorkerCountTests(unittest.TestCase):
    key = "releasemodule.update"
    entries = 5

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        _FakePool.requested = []
        _FakeConfigInfo.path = None
        _FakeConfigInfo.cluster = False
        mock.patch("wwpdb.io.misc.ResourceAllocation.ConfigInfo", _FakeConfigInfo).start()
        mock.patch.object(UpdateBase, "__init__", _fake_base_init).start()
        self.addCleanup(mock.patch.stopall)

    def _configure(self, jobs=None, defaults=None):
        path = os.path.join(self._tmp, "resources.yaml")
        with open(path, "w") as out:
            json.dump({"jobs": jobs or {}, "defaults": defaults or {}}, out)
        _FakeConfigInfo.path = path

    def _cpus(self, available, node=None):
        mock.patch.object(os, "sched_getaffinity", lambda pid: set(range(available)), create=True).start()
        mock.patch.object(multiprocessing, "cpu_count", lambda: available if node is None else node).start()

    def _pool_size(self):
        request = mock.Mock()
        request.getValue.return_value = "Entries in release"
        step = update_module.MultiUpdateProcess(reqObj=request, updateList=[{"entry": str(i)} for i in range(self.entries)])
        _FakePool.requested = []
        with mock.patch.object(update_module, "MultiProcUtil", _FakePool), mock.patch.object(
            update_module.MultiUpdateProcess, "_MultiUpdateProcess__initialize", lambda self: None
        ), mock.patch.object(update_module.MultiUpdateProcess, "_MultiUpdateProcess__finalize", lambda self: None):
            step.run()
        self.assertEqual(1, len(_FakePool.requested))
        return _FakePool.requested[0]

    def testUnconfiguredUsesHalfTheCpus(self):
        self._cpus(16)
        self.assertEqual(8, self._pool_size())

    def testUnconfiguredUsesCpusAvailableToTheProcessNotTheNode(self):
        self._cpus(4, node=64)
        self.assertEqual(2, self._pool_size())

    def testOneCpuStillStartsOneWorker(self):
        self._cpus(1)
        self.assertEqual(1, self._pool_size())

    def testConfiguredCountIsUsed(self):
        self._cpus(16)
        self._configure(jobs={self.key: {"cpus": 3}})
        self.assertEqual(3, self._pool_size())

    def testConfiguredCountAboveAvailableCpusIsClamped(self):
        self._cpus(4)
        self._configure(jobs={self.key: {"cpus": 12}})
        self.assertEqual(4, self._pool_size())

    def testMalformedConfigurationFallsBackToTheDefault(self):
        self._cpus(16)
        self._configure(jobs={self.key: {"cpus": "lots"}})
        self.assertEqual(8, self._pool_size())

    def testClusterUsesOneWorkerPerEntryEvenAboveTheCpus(self):
        _FakeConfigInfo.cluster = True
        self._cpus(2)
        self.assertEqual(5, self._pool_size())

    def testConfiguredCountIsUsedWithCluster(self):
        _FakeConfigInfo.cluster = True
        self._cpus(16)
        self._configure(jobs={self.key: {"cpus": 3}})
        self.assertEqual(3, self._pool_size())

    def testMalformedConfigurationWithClusterFallsBackToOnePerEntry(self):
        _FakeConfigInfo.cluster = True
        self._cpus(16)
        self._configure(jobs={self.key: {"cpus": "lots"}})
        self.assertEqual(5, self._pool_size())


if __name__ == "__main__":
    unittest.main()
