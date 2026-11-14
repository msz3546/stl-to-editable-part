# DeepSeek Harness 运行方式

使用安装了 SolidWorks 的 Windows 电脑，在 DeepSeek Harness 桌面版打开本机工作文件夹。输入 `/stl-to-editable-part`，再给出 STL 路径和要求。通过 `/` 菜单也可选取同名技能。若刚装好技能，另开一个会话来刷新技能目录。

工作目录要能被当前 Harness 会话写入。工作副本可用 `-ImportedPart` 续接，原生重建计划可用 `-Plan` 续接。 [原生重建和验收](workflow.md) 中的双连字符选项对应底层 Python 命令。也可用 PowerShell 入口的同义参数，如 `-HoleDiameterMm`、`-Template`、`-RecognizedPart`、`-EditDimension`。

```powershell
& '<技能目录>\scripts\run-on-windows.ps1' -Check
```

入口优先使用用户指定的 `-Python`，其次查找 Harness 自带的 Python，再尝试 PATH。若检查显示缺少 OCP，在获准写入的工作区用下列命令安装。把 `$skillDir` 改为 Harness 加载技能时报告的目录。

```powershell
$skillDir = 'C:\path\to\stl-to-editable-part'
$runner = Join-Path $skillDir 'scripts\run-on-windows.ps1'
$dshRoot = $env:DSH_HOME
if (-not $dshRoot) { $dshRoot = Join-Path $env:USERPROFILE '.dsh' }
$python = Join-Path $dshRoot 'dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    $python = (Get-Command python.exe -CommandType Application -ErrorAction Stop).Source
}
$dependencyDir = Join-Path (Get-Location).Path 'stl-to-editable-dependencies'
& $python -m pip install --only-binary=:all: --target $dependencyDir 'cadquery-ocp-novtk==7.9.3.1.1'
if ($LASTEXITCODE -ne 0) { throw 'OCP installation failed.' }
& $runner -Check -Python $python -OcpPath $dependencyDir
```

Harness 自带的 Python 通常已有 NumPy。若 `-Check` 提示缺少 NumPy，使用相同解释器向 `$dependencyDir` 安装 `numpy==2.3.5`，再运行检查。转换时继续传入 `-Python $python -OcpPath $dependencyDir`。如果已有可用的 NumPy 和 OCP，可直接复用。技能和脚本在本机运行，CAD 文件留在本机。

Harness 官方说明提供了 [技能发现目录](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md#local-discovery-priority) 和 [斜杠调用方式](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/ui-skill/README.md#use-this-package)。
