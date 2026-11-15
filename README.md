# STL 转可编辑 SolidWorks 零件

DeepSeek Harness 插件 `dsh-stl-to-editable-part`。它在左侧栏增加一个立方体入口，打开「STL 转可编辑零件」工作台；同时注册 `/stl-to-editable-part` 技能。安装后，工作台可以收集 STL 路径、单位和输出文件名，并在新会话中填入转换任务。

v0.3.1 在本机按实测方案建立 SolidWorks 原生特征。新件先准备测量基线，再重建并验收。同一 STL 可用原任务的验收记录快速重出文件。新建候选检查实体、草图完全定义、驱动尺寸和几何基线。

## 使用

1. 在 DeepSeek Harness 安装插件后，点击左侧栏的立方体图标，打开转换工作台。
2. 填写 STL 文件路径，选择单位；输出文件名可留空。
3. 点击「打开转换会话」。插件会打开当前或最近工作区的新会话，并把完整任务填入输入框；检查后发送。
4. 也可以直接在对话中输入 `/stl-to-editable-part`，给出 STL 文件、单位和目标文件名。

工作台还提供「复制提示词」，便于在已有会话中使用。

## 安装

在 DeepSeek Harness 桌面版打开「插件管理器」，选择「添加插件」，填入 `.tgz` 的下载地址或下载后的绝对路径。启用插件后即可使用侧栏入口。若界面提示需要重启，请重启 Harness。 [查看安装包](https://github.com/msz3546/stl-to-editable-part/releases)

有 CLI 的用户也可以在目标 profile 安装。将命令中的 profile 和文件路径换成自己的值。

```powershell
dsh plugin --profile desktop add 'file:C:/Downloads/dsh-stl-to-editable-part-0.3.1.tgz'
```

## 运行环境

- Windows x64
- 本机可运行的 SolidWorks
- Python 3.12 x64、NumPy、Open CASCADE Python 绑定（OCP）

依赖检查与安装见 [`skills/stl-to-editable-part/references/deepseek-harness.md`](skills/stl-to-editable-part/references/deepseek-harness.md)。安装插件本身不需要启动 CAD。

STL 没有单位。按毫米推定时，应在交付说明中写明。自动管线适合单个闭合、定向流形网格；自动孔恢复覆盖沿输入 Y 轴、两端可匹配的直通孔。复杂曲面、盲孔和圆角可能需要实测后重建。

## 包结构

| 文件 | 作用 |
| --- | --- |
| `index.js` | Host 入口，注册技能 |
| `client.js` | Web Client 入口，注册左侧栏图标和主面板 |
| `cordis.patch.yml` | Bundle 补丁 |
| `locale/` | 插件管理器的标题和描述 |
| `assets/icon.svg` | 插件图标 |
| `skills/stl-to-editable-part/` | 技能说明、脚本和参考文档 |

## English

`dsh-stl-to-editable-part` adds a cube entry to the left sidebar and a conversion workbench. Enter an STL path and units, then open a new session with the conversion prompt drafted. The plugin also registers the `/stl-to-editable-part` skill.

Conversion runs locally on Windows x64 and requires SolidWorks, Python 3.12 x64, NumPy, and the Open CASCADE binding listed in the setup instructions. The mesh pipeline targets one closed, oriented manifold; automatic hole recovery covers through-holes along the input Y axis with matchable ends.
