import os
import subprocess

from deploy.patch import pre_checks

pre_checks()

from deploy.adb import AdbManager
from deploy.alas import AlasManager
from deploy.app import AppManager
from deploy.config import ExecutionError
from deploy.git import GitManager
from deploy.pip import PipManager


class Installer(GitManager, PipManager, AdbManager, AppManager, AlasManager):
    def sync_upstream(self):
        """
        启动时先把自己的补丁叠到最新的官方代码上。

        由 sync-upstream.bat 完成：fetch upstream -> rebase -> 重新生成配置 -> 校验 -> push。
        脚本自带失败回滚，出错不会影响本次启动；脚本不存在时直接跳过。
        """
        script = os.path.abspath('./sync-upstream.bat')
        if not os.path.exists(script):
            return
        try:
            subprocess.call(['cmd', '/c', script, 'auto'])
        except Exception:
            pass

    def install(self):
        self.sync_upstream()

        from deploy.atomic import atomic_failure_cleanup
        atomic_failure_cleanup('./config')
        try:
            self.git_install()
            self.alas_kill()
            self.pip_install()
            self.app_update()
            self.adb_install()
        except ExecutionError:
            exit(1)


if __name__ == '__main__':
    Installer().install()
