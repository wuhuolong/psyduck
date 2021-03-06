import core.helper
import core.path
from datetime import datetime
from core import db
from core import file_helper
from uploader import upload


class DownloadProcedure:
    act = {}
    over = False
    csdn = ''
    url = ''
    helper: core.helper.Helper
    current_func = None

    def __init__(self, act):
        self.act = act
        self.url = act['message']['url']
        self.csdn = act['message']['csdn']
        self.current_func = self.check_downloaded
        self.helper = core.helper.Helper()
        self.over = False

    def check_downloaded(self):
        _url = self.url
        if _url.find('#') != -1:
            _url = _url[0:_url.index('#')]

        _id = _url[_url.rfind('/') + 1:]
        _d = db.download_get(_id)
        if _d is not None:
            self._done(_id)
            return
        self.current_func = self.process_start

    def process_start(self):
        print('下载初始化...')
        _time = datetime.now().strftime('%Y%m%d%H%M%S%f')
        _des_option = f'_tmp_option_download_{self.csdn}_{_time}'
        if not file_helper.has_option(self.csdn):
            self._fail(f'option not exist')
            return
        res = file_helper.copy_option(self.csdn, _des_option)
        if not res:
            self._fail(f'option error')
            return
        res = self.helper.init(_des_option)
        if not res.success:
            self._fail(f'option error')
            return
        self.current_func = self.goto_validate

    def stop(self):
        self._over()

    def _over(self):
        self.over = True
        self.current_func = None
        self._dispose_helper()

    def _dispose_helper(self):
        if not self.helper.is_disposed:
            self.helper.dispose()

    def set_state(self, state, result):
        db.act_set_state(self.act['id'], state, result)
        self.act['state'] = state
        self.act['result'] = result

    def update(self):
        if self.current_func is not None:
            self.current_func()

    def goto_validate(self):
        print('开始验证登陆状态')
        res = self.helper.check_login()
        if not res.success:
            self._fail('check_login fail')
            return
        if res.result:
            self.goto_download()
        else:
            self._fail('账户过期')

    def goto_download(self):

        def _download_callback(step, now_size=None, total_size=None):
            if step == 'downloading':
                p = {'now_size': now_size, 'total_size': total_size}
                self.set_state('download', {'step': step, 'progress': p})
                print(f'download: {p}')
            else:
                self.set_state('download', {'step': step})

        res = self.helper.download(self.url, _download_callback)

        if not res.success:
            self._fail(res.result)
            return

        info = res.result
        _d = db.download_get(info['id'])

        # 提前关闭 helper
        self._dispose_helper()

        if _d is None:
            db.download_create(info['id'], self.act['uid'], self.csdn, info['url'], info['title'], info['type'],
                               info['size'], info['description'], info['filename'], info['point'], info['star'],
                               info['upload_time'], info['uploader'], '', datetime.now())
            self.goto_upload(info)
        else:
            self._done(info['id'])

    _last_callback = datetime.now()

    def goto_upload(self, info):

        def _upload_callback(now_size, total_size):
            if (datetime.now() - self._last_callback).seconds < 0.5:
                return
            self._last_callback = datetime.now()
            p = {'now_size': now_size, 'total_size': total_size}
            self.set_state('upload', {'step': 'uploading', 'progress': p})
            print(f'upload: {p}')

        self.set_state('upload', {'step': 'start'})
        _id = info['id']
        file_path = core.path.frozen_path(f'caches/zips/{_id}.zip')
        success = upload.upload(file_path, _upload_callback)
        if success:
            self._done(_id)
        else:
            self._fail('上传失败')

    def _fail(self, msg):
        print(f'下载发生错误（{msg}）: {self.csdn}')
        self._over()
        self.set_state('fail', msg)

    def _done(self, _id):
        print(f'下载完成: {self.csdn} -> {_id}')
        self._over()
        self.set_state('done', _id)
