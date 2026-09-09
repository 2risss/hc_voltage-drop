# 压降验证测算

家充压降计算工具。手机浏览器打开即可，也可添加到主屏幕。计算和历史记录只留在本机，不会上传。

## 内网地址

仓库：https://github.tesla.cn/luying/hc_voltage-drop

开启 Pages 后，常见访问地址为：

- https://github.tesla.cn/pages/luying/hc_voltage-drop/
- 或以仓库 Settings → Pages 页面显示的地址为准

## 本地预览

在项目根目录运行：

```
python -m http.server 8765
```

然后打开 http://127.0.0.1:8765/

不要直接双击 `index.html`。

## 公式更新

计算公式在 `config/formula.json`。修改后推送到仓库即可，不必改页面代码。页面顶部会显示公式版本号。

原 Excel（`压降计算公式.xlsm`）不上传到本仓库。
