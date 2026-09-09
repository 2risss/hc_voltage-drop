# 压降验证测算

家充压降计算工具。手机浏览器打开即可，也可添加到主屏幕。计算和历史记录只留在本机，不会上传。

## 公网地址（推荐分享）

仓库：https://github.com/YOUR_GITHUB_USERNAME/hc_voltage-drop

网页（GitHub Pages，开启后）：

https://YOUR_GITHUB_USERNAME.github.io/hc_voltage-drop/

把上面这个链接发给别人即可，不需要登录。微信里点链接也能打开。

## 内网地址（需登录 github.tesla.cn）

仓库：https://github.tesla.cn/luying/hc_voltage-drop

网页：https://github.tesla.cn/pages/luying/hc_voltage-drop/

## 微信直接打开（单文件）

把仓库里的 `压降验证测算.html` 当文件发到微信，点开即可用，不需要登录、不需要联网。

公式已打进该文件。以后若改了 `config/formula.json`，在项目里运行：

```
python scripts/build_standalone.py
```

会重新生成这一份单文件。

## 本地预览

在项目根目录运行：

```
python -m http.server 8765
```

然后打开 http://127.0.0.1:8765/

不要直接双击仓库里的 `index.html`（它还要加载旁边的 JSON）。单文件 `压降验证测算.html` 可以直接双击或在微信中打开。

## 公式更新

计算公式在 `config/formula.json`。修改后推送到仓库即可，不必改页面代码。页面顶部会显示公式版本号。

原 Excel（`压降计算公式.xlsm`）不上传到本仓库。
